"""Local scientific experiment runner (Milestone 5).

Responsibilities:
* validate configuration and derive a deterministic experiment id;
* run each (algorithm, seed) trial under an equal environment-interaction budget;
* evaluate the trained artifact on held-out seeds and on morphology/perturbation
  variants (zero-shot transfer), plus an optional fixed-budget adaptation phase;
* persist everything transactionally (SQLite + JSONL + Parquet/CSV);
* support bounded local concurrency, cancellation, resume and honest failure reporting.

Usage::

    origin-run --config configs/pilot.json --store runs --jobs 4 --resume
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import numpy as np

from origin.environments.embodied import (
    EmbodiedConfig,
    EmbodiedCreature,
    embodied_morphology_variants,
    embodied_perturbation_variants,
)
from origin.environments.gridworld import GridWorldConfig
from origin.evaluation.embodied import (
    EmbodiedEvaluator,
    evaluate_embodied,
)
from origin.evaluation.harness import (
    Evaluator,
    evaluate_policy,
    morphology_variants,
    multi_niche_variants,
    perturbation_variants,
)
from origin.evolution import fine_tune, fixed_objective_ga, map_elites, novelty_search
from origin.learning import reinforce
from origin.organisms.organism import Organism
from origin.organisms.policies import GaitPolicy, HeuristicPolicy, RandomPolicy

ALGORITHMS: dict[str, Any] = {
    "fixed_objective_ga": fixed_objective_ga,
    "novelty_search": novelty_search,
    "map_elites": map_elites,
    "reinforce": reinforce,
}

# Baselines available per simulator kind.
BASELINES: dict[str, tuple[str, ...]] = {
    "gridworld": ("random", "heuristic"),
    "embodied": ("random", "scripted_gait"),
}

DEFAULT_ALGO_KWARGS: dict[str, dict[str, Any]] = {
    "fixed_objective_ga": {"pop_size": 48, "mutation_rate": 0.3, "mutation_scale": 0.5, "morph_strength": 0.3},
    "novelty_search": {"pop_size": 48, "mutation_rate": 0.3, "mutation_scale": 0.5},
    "map_elites": {"batch": 24, "grid_shape": [12, 12], "mutation_rate": 0.3, "mutation_scale": 0.5, "morph_strength": 0.3},
    "reinforce": {"hidden": [24], "episodes_per_update": 4, "lr": 0.03, "gamma": 0.99},
}


# ---------------------------------------------------------------------- #
# Config helpers
# ---------------------------------------------------------------------- #
def sim_kind(cfg: dict[str, Any]) -> str:
    """Which simulator a campaign targets: the grid world or articulated physics."""
    kind = str(cfg.get("env_kind", "gridworld"))
    if kind not in BASELINES:
        raise ValueError(f"unknown env_kind {kind!r}; expected one of {sorted(BASELINES)}")
    return kind


def build_base_env(env_cfg: dict[str, Any], kind: str = "gridworld") -> Any:
    if kind == "embodied":
        return EmbodiedConfig.from_dict(env_cfg)
    return GridWorldConfig.from_dict(env_cfg)


def experiment_id(cfg: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]


def trial_id_for(exp_id: str, algorithm: str, seed: int) -> str:
    return hashlib.sha256(f"{exp_id}|{algorithm}|{seed}".encode()).hexdigest()[:16]


def validate_config(cfg: dict[str, Any]) -> None:
    for key in ("name", "env", "train_seeds", "test_seeds", "budget", "seeds"):
        if key not in cfg:
            raise ValueError(f"config missing required key: {key}")
    if not cfg["train_seeds"] or not cfg["test_seeds"]:
        raise ValueError("train_seeds and test_seeds must be non-empty")
    overlap = set(cfg["train_seeds"]) & set(cfg["test_seeds"])
    if overlap:
        raise ValueError(f"train/test seed leakage: {sorted(overlap)}")
    if cfg["budget"] < 1:
        raise ValueError("budget must be >= 1")
    kind = sim_kind(cfg)
    algos = cfg.get("algorithms", {})
    for name in algos:
        if name not in ALGORITHMS:
            raise ValueError(f"unknown algorithm: {name}")
    for name in cfg.get("include_baselines", []) or []:
        if name not in BASELINES[kind]:
            raise ValueError(f"baseline {name!r} not available for env_kind={kind!r}; expected {BASELINES[kind]}")
    build_base_env(cfg["env"], kind)  # raises on invalid env config


def environment_manifest() -> dict[str, Any]:
    def _git(args: list[str]) -> str:
        try:
            return subprocess.check_output(["git", *args], stderr=subprocess.DEVNULL).decode().strip()
        except Exception:
            return ""

    versions: dict[str, str] = {}
    for mod in ("numpy", "scipy", "pandas", "pyarrow", "gymnasium", "matplotlib"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:
            versions[mod] = "absent"
    return {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": int(_cpu_count()),
        "packages": versions,
        "git_sha": _git(["rev-parse", "HEAD"]),
        "git_dirty": bool(_git(["status", "--porcelain"])),
        "git_branch": _git(["rev-parse", "--abbrev-ref", "HEAD"]),
        "timestamp": time.time(),
    }


def _cpu_count() -> int:
    import os

    try:
        # ``sched_getaffinity`` is Linux-specific and absent from Windows type
        # stubs.  Dynamic lookup preserves the cgroup-aware Linux behaviour
        # while keeping the documented ``os.cpu_count`` fallback portable.
        affinity = getattr(os, "sched_getaffinity", None)
        if affinity is not None:
            return len(affinity(0))
    except Exception:
        pass
    return os.cpu_count() or 1


# ---------------------------------------------------------------------- #
# Trial execution (runs in a worker process)
# ---------------------------------------------------------------------- #
def _serialize_org(org: Organism | None) -> dict[str, Any] | None:
    return org.to_dict() if org is not None else None


def run_trial(algorithm: str, seed: int, cfg: dict[str, Any]) -> dict[str, Any]:
    kind = sim_kind(cfg)
    base = build_base_env(cfg["env"], kind)
    train_seeds = list(cfg["train_seeds"])
    test_seeds = list(cfg["test_seeds"])
    budget = int(cfg["budget"])
    kwargs = {**DEFAULT_ALGO_KWARGS.get(algorithm, {}), **cfg.get("algorithms", {}).get(algorithm, {})}

    if kind == "embodied":
        return _run_trial_embodied(algorithm, seed, base, train_seeds, test_seeds, budget, kwargs, cfg)

    if algorithm in ("random", "heuristic"):
        return _run_baseline(algorithm, seed, base, train_seeds, test_seeds, cfg)

    fn = ALGORITHMS[algorithm]
    evaluator = Evaluator(base_env=base, train_seeds=train_seeds, budget=budget)
    t0 = time.time()
    result = fn(evaluator, base, seed=seed, **kwargs)
    train_fitness = result.best_fitness

    metrics: dict[str, Any] = {
        "algorithm_version": result.version,
        "interactions": result.interactions,
        "budget": budget,
        "train_fitness": train_fitness,
        "n_generations": len(result.history),
        "history": _downsample(result.history, 60),
        "descriptors_mean": (np.mean(result.descriptors, axis=0).tolist() if result.descriptors else None),
        "descriptor_spread": (float(np.mean(np.std(result.descriptors, axis=0))) if result.descriptors else None),
        "wall_seconds": round(time.time() - t0, 3),
        "algorithm_extra": result.extra,
    }

    transfer: dict[str, Any] = {}
    best = result.best_organism
    if best is not None:
        # held-out environmental seeds (same morphology)
        test = evaluate_policy(best.env_config(base), best, test_seeds)
        metrics["test_mean_reward"] = test["mean_reward"]
        metrics["test_std_reward"] = test["std_reward"]
        metrics["test_mean_collected"] = test["mean_collected"]
        # Training and evaluation steps are distinct currencies (see embodied path).
        metrics["evaluation_interactions"] = test["interactions"]
        # morphology + perturbation transfer (zero-shot, then adapted)
        transfer = _transfer_report(best, base, train_seeds, test_seeds, cfg)

    return {
        "algorithm": algorithm,
        "seed": seed,
        "interactions": result.interactions,
        "budget": budget,
        "best_fitness": train_fitness,
        "metrics": metrics,
        "transfer": transfer,
        "best_organism": _serialize_org(best),
        "status": "done",
    }


def _run_baseline(algorithm: str, seed: int, base: GridWorldConfig, train_seeds: list[int], test_seeds: list[int], cfg: dict[str, Any]) -> dict[str, Any]:
    pol = RandomPolicy(base.n_actions, seed=seed) if algorithm == "random" else HeuristicPolicy(base.n_actions, seed=seed)
    train = evaluate_policy(base, pol, train_seeds)
    test = evaluate_policy(base, pol, test_seeds)
    transfer = {}
    for name, vcfg in {**morphology_variants(base), **perturbation_variants(base)}.items():
        try:
            r = evaluate_policy(vcfg, pol, test_seeds)
            transfer[name] = {"zero_shot_mean_reward": r["mean_reward"], "zero_shot_std": r["std_reward"]}
        except Exception as exc:  # pragma: no cover
            transfer[name] = {"error": str(exc)}
    return {
        "algorithm": algorithm,
        "seed": seed,
        # Baselines do not train: zero training interactions, evaluation counted
        # separately (same currency contract as the learner trials).
        "interactions": 0,
        "budget": int(cfg["budget"]),
        "best_fitness": train["mean_reward"],
        "metrics": {
            "train_fitness": train["mean_reward"],
            "train_std": train["std_reward"],
            "test_mean_reward": test["mean_reward"],
            "test_std_reward": test["std_reward"],
            "test_mean_collected": test["mean_collected"],
            "interactions": 0,
            "evaluation_interactions": test["interactions"],
            "baseline": True,
        },
        "transfer": transfer,
        "best_organism": None,
        "status": "done",
    }


def _run_trial_embodied(
    algorithm: str,
    seed: int,
    base: Any,
    train_seeds: list[int],
    test_seeds: list[int],
    budget: int,
    kwargs: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """A campaign trial against the articulated-physics simulator.

    Shares the metric contract with the grid trials so the store, analysis and UI
    treat both kinds identically.
    """
    if algorithm in BASELINES["embodied"]:
        return _run_baseline_embodied(algorithm, seed, base, train_seeds, test_seeds, cfg)

    fn = ALGORITHMS[algorithm]
    evaluator = EmbodiedEvaluator(base_env=base, train_seeds=train_seeds, budget=budget)
    run_kwargs = dict(kwargs)
    if algorithm == "reinforce":
        # The RL loop builds its own envs; hand it a factory for this body.
        run_kwargs["env_factory"] = lambda: EmbodiedCreature(base)
    if algorithm == "map_elites":
        # The embodied descriptor is [travelled, upright_frac, energy, rate, time_frac];
        # archive over (distance travelled, upright fraction) with explicit ranges so
        # the archive never assumes grid descriptor semantics.
        run_kwargs.setdefault("desc_dims", (0, 1))
        run_kwargs.setdefault("bounds", [(0.0, max(1.0, float(base.target_distance))), (0.0, 1.0)])

    t0 = time.time()
    result = fn(evaluator, base, seed=seed, **run_kwargs)
    train_fitness = result.best_fitness

    metrics: dict[str, Any] = {
        "algorithm_version": result.version,
        "interactions": result.interactions,
        "budget": budget,
        "train_fitness": train_fitness,
        "n_generations": len(result.history),
        "history": _downsample(result.history, 60),
        "descriptors_mean": (np.mean(result.descriptors, axis=0).tolist() if result.descriptors else None),
        "descriptor_spread": (float(np.mean(np.std(result.descriptors, axis=0))) if result.descriptors else None),
        "wall_seconds": round(time.time() - t0, 3),
        "algorithm_extra": result.extra,
        "env_kind": "embodied",
    }

    transfer: dict[str, Any] = {}
    best = result.best_organism
    if best is not None:
        test = evaluate_embodied(base, best, test_seeds)
        metrics["test_mean_reward"] = test["mean_reward"]
        metrics["test_std_reward"] = test["std_reward"]
        metrics["test_mean_distance_travelled"] = test["mean_distance_travelled"]
        metrics["test_fall_rate"] = test["fall_rate"]
        metrics["test_target_rate"] = test["target_rate"]
        # Training and evaluation steps are distinct currencies: "interactions"
        # is the budget's unit (training only), evaluation is counted separately
        # so "compute cost per method" never mixes the two.
        metrics["evaluation_interactions"] = test["interactions"]
        transfer = _transfer_report_embodied(best, base, train_seeds, test_seeds, cfg)

    return {
        "algorithm": algorithm,
        "seed": seed,
        "interactions": result.interactions,
        "budget": budget,
        "best_fitness": train_fitness,
        "metrics": metrics,
        "transfer": transfer,
        "best_organism": _serialize_org(best),
        "status": "done",
    }


def _run_baseline_embodied(
    algorithm: str,
    seed: int,
    base: Any,
    train_seeds: list[int],
    test_seeds: list[int],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    pol = RandomPolicy(base.n_actions, seed=seed) if algorithm == "random" else GaitPolicy(base.n_actions, seed=seed)
    train = evaluate_embodied(base, pol, train_seeds)
    test = evaluate_embodied(base, pol, test_seeds)
    transfer: dict[str, Any] = {}
    for name, vcfg in {**embodied_morphology_variants(base), **embodied_perturbation_variants(base)}.items():
        try:
            r = evaluate_embodied(vcfg, pol, test_seeds)
            transfer[name] = {"zero_shot_mean_reward": r["mean_reward"], "zero_shot_std": r["std_reward"]}
        except Exception as exc:  # pragma: no cover
            transfer[name] = {"error": str(exc)}
    return {
        "algorithm": algorithm,
        "seed": seed,
        # Baselines do not train: zero training interactions, evaluation counted
        # separately (same currency contract as the learner trials).
        "interactions": 0,
        "budget": int(cfg["budget"]),
        "best_fitness": train["mean_reward"],
        "metrics": {
            "train_fitness": train["mean_reward"],
            "train_std": train["std_reward"],
            "test_mean_reward": test["mean_reward"],
            "test_std_reward": test["std_reward"],
            "test_mean_distance_travelled": test["mean_distance_travelled"],
            "test_fall_rate": test["fall_rate"],
            "test_target_rate": test["target_rate"],
            "interactions": 0,
            "evaluation_interactions": test["interactions"],
            "baseline": True,
            "env_kind": "embodied",
        },
        "transfer": transfer,
        "best_organism": None,
        "status": "done",
    }


def _transfer_report_embodied(
    org: Organism,
    base: Any,
    train_seeds: list[int],
    test_seeds: list[int],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Zero-shot and adapted transfer across distinct physical bodies.

    Adaptation runs on ``train_seeds`` only; every reported score (zero-shot and
    adapted) is measured on the held-out ``test_seeds``, so an adaptation gain is
    never in-sample.
    """
    tcfg = cfg.get("transfer", {}) or {}
    do_adapt = bool(tcfg.get("adapt", True))
    adapt_budget = int(tcfg.get("budget", max(1, int(cfg["budget"]) // 10)))
    adapt_seeds = train_seeds[: min(2, len(train_seeds))]
    report: dict[str, Any] = {}

    for name, vcfg in embodied_morphology_variants(base).items():
        try:
            zs = evaluate_embodied(vcfg, org, test_seeds)
            entry: dict[str, Any] = {
                "zero_shot_mean_reward": zs["mean_reward"],
                "zero_shot_std": zs["std_reward"],
                "zero_shot_fall_rate": zs["fall_rate"],
                "zero_shot_travelled": zs["mean_distance_travelled"],
                "kind": "morphology",
            }
            if do_adapt and adapt_seeds:
                ev = EmbodiedEvaluator(base_env=vcfg, train_seeds=adapt_seeds, budget=adapt_budget)
                ad = fine_tune(
                    org,
                    vcfg,
                    seed=adapt_seeds[0],
                    budget=adapt_budget,
                    seeds=adapt_seeds,
                    evaluator_factory=lambda ev=ev: ev,
                )
                assert ad.best_organism is not None
                after = evaluate_embodied(vcfg, ad.best_organism, test_seeds)
                entry["adapted_mean_reward"] = after["mean_reward"]
                entry["adaptation_gain"] = after["mean_reward"] - zs["mean_reward"]
                entry["adapted_fall_rate"] = after["fall_rate"]
                entry["adaptation_interactions"] = int(ev.interactions)
            report[name] = entry
        except Exception as exc:
            report[name] = {"error": str(exc), "kind": "morphology"}

    for name, pcfg in embodied_perturbation_variants(base).items():
        try:
            zs = evaluate_embodied(pcfg, org, test_seeds)
            report[name] = {
                "zero_shot_mean_reward": zs["mean_reward"],
                "zero_shot_std": zs["std_reward"],
                "zero_shot_fall_rate": zs["fall_rate"],
                "kind": "perturbation",
            }
        except Exception as exc:
            report[name] = {"error": str(exc), "kind": "perturbation"}

    return report


def _downsample(history: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    if len(history) <= n:
        return history
    idx = np.linspace(0, len(history) - 1, n).astype(int)
    return [history[i] for i in idx]


def _transfer_report(
    org: Organism,
    base: GridWorldConfig,
    train_seeds: list[int],
    test_seeds: list[int],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Zero-shot and adapted transfer on the grid world.

    Adaptation runs on ``train_seeds`` only and the adapted score is measured on
    the held-out ``test_seeds`` — reporting ``fine_tune``'s in-sample best fitness
    here would credit adaptation for memorising its own training seeds.
    """
    tcfg = cfg.get("transfer", {}) or {}
    do_adapt = bool(tcfg.get("adapt", True))
    adapt_budget = int(tcfg.get("budget", max(1, int(cfg["budget"]) // 20)))
    adapt_seeds = train_seeds[: min(2, len(train_seeds))]
    report: dict[str, Any] = {}

    for name, vcfg in morphology_variants(base).items():
        try:
            zs = evaluate_policy(vcfg, org, test_seeds)
            entry: dict[str, Any] = {"zero_shot_mean_reward": zs["mean_reward"], "zero_shot_std": zs["std_reward"], "kind": "morphology"}
            if do_adapt and adapt_seeds:
                ad = fine_tune(org, vcfg, seed=adapt_seeds[0], budget=adapt_budget, seeds=adapt_seeds)
                assert ad.best_organism is not None
                after = evaluate_policy(vcfg, ad.best_organism, test_seeds)
                entry["adapted_mean_reward"] = after["mean_reward"]
                entry["adaptation_gain"] = after["mean_reward"] - zs["mean_reward"]
            report[name] = entry
        except Exception as exc:
            report[name] = {"error": str(exc), "kind": "morphology"}

    for name, pcfg in perturbation_variants(base).items():
        try:
            zs = evaluate_policy(pcfg, org, test_seeds)
            report[name] = {"zero_shot_mean_reward": zs["mean_reward"], "zero_shot_std": zs["std_reward"], "kind": "perturbation"}
        except Exception as exc:
            report[name] = {"error": str(exc), "kind": "perturbation"}

    return report


# ---------------------------------------------------------------------- #
# Orchestration
# ---------------------------------------------------------------------- #
def run_experiment(
    cfg: dict[str, Any],
    store_root: str | Path = "runs",
    jobs: int = 1,
    resume: bool = True,
    cancel_file: str | Path | None = None,
    include_baselines: bool = True,
) -> dict[str, Any]:
    from origin.experiments.store import Store  # local import keeps worker import light

    validate_config(cfg)
    exp_id = experiment_id(cfg)
    store = Store(store_root)
    manifest = environment_manifest()
    store.upsert_experiment(exp_id, cfg["name"], cfg.get("protocol", ""), hashlib.sha256(json.dumps(cfg["env"], sort_keys=True).encode()).hexdigest()[:12], cfg, manifest.get("git_sha"))

    trials: list[tuple[str, int]] = []
    for algo in cfg.get("algorithms", {}):
        for seed in cfg["seeds"]:
            trials.append((algo, int(seed)))
    if include_baselines:
        for algo in cfg.get("include_baselines", ["random", "heuristic"]):
            for seed in cfg["seeds"]:
                trials.append((algo, int(seed)))

    exp_dir = Path(store_root) / exp_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "manifest.json").write_text(json.dumps({"experiment_id": exp_id, "config": cfg, "environment": manifest}, indent=2, sort_keys=True))

    cancel_path = str(cancel_file) if cancel_file else ""

    def cancelled() -> bool:
        return bool(cancel_path) and Path(cancel_path).exists()

    pending = []
    for algo, seed in trials:
        tid = trial_id_for(exp_id, algo, seed)
        if resume and store.trial_status(tid) == "done":
            continue
        pending.append((algo, seed, tid))

    results: list[dict[str, Any]] = []
    started = time.time()
    if jobs <= 1:
        for algo, seed, tid in pending:
            if cancelled():
                break
            _execute_one(store, exp_id, algo, seed, tid, cfg, results)
    else:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {}
            for algo, seed, tid in pending:
                if cancelled():
                    break
                futures[pool.submit(run_trial, algo, seed, cfg)] = (algo, seed, tid)
            for fut in as_completed(futures):
                algo, seed, tid = futures[fut]
                try:
                    res = fut.result()
                    _persist(store, exp_id, res, tid, exp_dir, results)
                except Exception as exc:  # pragma: no cover
                    store.fail_trial(tid, f"{type(exc).__name__}: {exc}")
                    results.append({"trial_id": tid, "algorithm": algo, "seed": seed, "status": "failed", "error": str(exc)})

    exports = store.export_trials(exp_id)
    store.add_artifact(exp_id, None, "trials_csv", exports["csv"])
    summary = store.summary(exp_id)
    report = {
        "experiment_id": exp_id,
        "name": cfg["name"],
        "n_trials_run": len(results),
        "n_pending_before": len(pending),
        "wall_seconds": round(time.time() - started, 2),
        "exports": exports,
        "summary": summary,
    }
    (exp_dir / "summary.json").write_text(json.dumps(report, indent=2, sort_keys=True))
    return report


def _execute_one(store: Any, exp_id: str, algo: str, seed: int, tid: str, cfg: dict[str, Any], results: list[dict[str, Any]]) -> None:
    store.add_trial(tid, exp_id, algo, seed, int(cfg["budget"]))
    try:
        res = run_trial(algo, seed, cfg)
        _persist(store, exp_id, res, tid, Path(store.root) / exp_id, results)
    except Exception as exc:
        store.fail_trial(tid, f"{type(exc).__name__}: {exc}")
        results.append({"trial_id": tid, "algorithm": algo, "seed": seed, "status": "failed", "error": str(exc)})


def _persist(store: Any, exp_id: str, res: dict[str, Any], tid: str, exp_dir: Path, results: list[dict[str, Any]], worker_id: str | None = None) -> None:
    store.add_trial(tid, exp_id, res["algorithm"], res["seed"], int(res["budget"]))
    recorded = store.complete_trial(
        tid,
        res["interactions"],
        float(res["best_fitness"]),
        float(res["metrics"].get("train_fitness", res["best_fitness"])),
        res["metrics"],
        res["transfer"],
        worker_id=worker_id,
    )
    exp_dir.mkdir(parents=True, exist_ok=True)
    hist = res["metrics"].get("history", [])
    with (exp_dir / f"{tid}.jsonl").open("w") as fh:
        for rec in hist:
            fh.write(json.dumps(rec) + "\n")
    if res.get("best_organism"):
        (exp_dir / f"{tid}.organism.json").write_text(json.dumps(res["best_organism"], sort_keys=True))
    store.add_artifact(exp_id, tid, "history_jsonl", str(exp_dir / f"{tid}.jsonl"))
    results.append({
        "trial_id": tid,
        "algorithm": res["algorithm"],
        "seed": res["seed"],
        # Completion is keep-first: if the trial was already done (a duplicate
        # computation finishing late), the recorded result stands and this run
        # is reported as dropped, never silently counted as work done.
        "status": "done" if recorded else "duplicate_dropped",
        "best_fitness": res["best_fitness"],
    })


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="ORIGIN experiment runner")
    ap.add_argument("--config", required=True, help="path to experiment JSON config")
    ap.add_argument("--store", default="runs", help="experiment store directory")
    ap.add_argument("--jobs", type=int, default=1, help="worker processes")
    ap.add_argument("--no-resume", action="store_true", help="re-run completed trials")
    ap.add_argument("--cancel-file", default=None, help="path to a file whose presence cancels the run")
    ap.add_argument("--no-baselines", action="store_true")
    args = ap.parse_args(argv)

    cfg = json.loads(Path(args.config).read_text())
    report = run_experiment(
        cfg,
        store_root=args.store,
        jobs=args.jobs,
        resume=not args.no_resume,
        cancel_file=args.cancel_file,
        include_baselines=not args.no_baselines,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
