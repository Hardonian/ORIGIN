"""Result visualization (Milestone 5). Matplotlib only; no interactive deps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from origin.experiments.store import Store  # noqa: E402


def _trial_histories(store: Store, exp_id: str) -> dict[str, list[list[dict[str, Any]]]]:
    out: dict[str, list[list[dict]]] = {}
    for t in store.trials(exp_id):
        if t["status"] != "done":
            continue
        m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
        hist = m.get("history")
        if not hist:
            continue
        out.setdefault(t["algorithm"], []).append(hist)
    return out


def plot_training_curves(store: Store, exp_id: str, out_path: Path) -> Path:
    hist = _trial_histories(store, exp_id)
    fig, ax = plt.subplots(figsize=(8, 5))
    for algo, runs in sorted(hist.items()):
        metric_key = next((k for k in ("best", "best_task", "eval_fitness", "mean_episode_reward", "qd_score", "coverage") if k in runs[0][0]), "best")
        maxlen = max(len(r) for r in runs)
        grid = np.full((len(runs), maxlen), np.nan)
        for i, r in enumerate(runs):
            grid[i, : len(r)] = [h.get(metric_key, np.nan) for h in r]
        with np.errstate(invalid="ignore"):
            mean = np.nanmean(grid, axis=0)
        ax.plot(range(len(mean)), mean, label=f"{algo} (n={len(runs)})")
    ax.set_xlabel("generation / iteration")
    ax.set_ylabel("best fitness (train)")
    ax.set_title(f"Training progress — {exp_id}")
    ax.legend()
    ax.grid(alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_transfer(store: Store, exp_id: str, out_path: Path) -> Path:
    trials = [t for t in store.trials(exp_id) if t["status"] == "done"]
    agg: dict[str, dict[str, list[float]]] = {}
    for t in trials:
        tr = json.loads(t["transfer_json"]) if t.get("transfer_json") else {}
        for name, entry in (tr or {}).items():
            if "zero_shot_mean_reward" in entry:
                agg.setdefault(t["algorithm"], {}).setdefault(name, []).append(entry["zero_shot_mean_reward"])
    fig, ax = plt.subplots(figsize=(9, 5))
    algos = sorted(agg)
    if algos:
        names = sorted({n for a in agg.values() for n in a})
        x = np.arange(len(names))
        width = 0.8 / max(1, len(algos))
        for i, algo in enumerate(algos):
            vals = [np.mean(agg[algo][n]) if n in agg[algo] else np.nan for n in names]
            ax.bar(x + i * width, vals, width, label=algo)
        ax.set_xticks(x + width * (len(algos) - 1) / 2)
        ax.set_xticklabels(names, rotation=30, ha="right")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_ylabel("zero-shot mean reward")
        ax.set_title(f"Cross-morphology / perturbation transfer — {exp_id}")
        ax.legend()
        ax.grid(alpha=0.3, axis="y")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def plot_descriptor_scatter(store: Store, exp_id: str, out_path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(7, 5))
    plotted = False
    for t in store.trials(exp_id):
        if t["status"] != "done":
            continue
        org_path = Path(store.root) / exp_id / f"{t['id']}.organism.json"
        if not org_path.exists():
            continue
        m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
        dm = m.get("descriptors_mean")
        if dm:
            ax.scatter(dm[0], dm[2], label=t["algorithm"], s=40)
            plotted = True
    if plotted:
        ax.set_xlabel("mean resources collected (descriptor 0)")
        ax.set_ylabel("episode-length fraction (descriptor 2)")
        ax.set_title(f"Behavioural descriptors — {exp_id}")
        ax.legend()
        ax.grid(alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path, dpi=120)
    plt.close(fig)
    return out_path


def generate_all(store_root: str, exp_id: str, out_dir: str | Path | None = None) -> list[str]:
    store = Store(store_root)
    out = Path(out_dir) if out_dir else Path(store_root) / exp_id / "plots"
    out.mkdir(parents=True, exist_ok=True)
    paths = [
        plot_training_curves(store, exp_id, out / "training_curves.png"),
        plot_transfer(store, exp_id, out / "transfer.png"),
        plot_descriptor_scatter(store, exp_id, out / "descriptors.png"),
    ]
    for p in paths:
        store.add_artifact(exp_id, None, "plot", str(p))
    return [str(p) for p in paths]


def main(argv: list[str] | None = None) -> int:  # pragma: no cover
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    for p in generate_all(args.store, args.experiment, args.out):
        print(p)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
