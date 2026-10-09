#!/usr/bin/env python3
"""Fail-closed registered analysis for the REINFORCE promotion study."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from origin.evaluation.stats import min_detectable_effect, paired_bootstrap_ci, wilcoxon_signed_rank
from origin.experiments.store import Store

METHOD = "reinforce"
BASELINE = "random"
RESAMPLES = 10_000


def require_complete_paired_data(
    by_seed: dict[str, dict[int, float]], cfg: dict, methods: tuple[str, str] = (METHOD, BASELINE)
) -> None:
    """Require the exact registered seed matrix and finite held-out scores."""
    expected = [int(seed) for seed in cfg.get("seeds", [])]
    if len(expected) != len(set(expected)):
        raise ValueError("configured method seeds must be unique")
    problems: list[str] = []
    for method in methods:
        observed = by_seed.get(method, {})
        missing = sorted(set(expected) - set(observed))
        nonfinite = sorted(seed for seed, value in observed.items() if not math.isfinite(value))
        if missing:
            problems.append(f"{method}: missing seeds {missing}")
        if nonfinite:
            problems.append(f"{method}: non-finite held-out values for seeds {nonfinite}")
    if problems:
        raise ValueError("incomplete REINFORCE paired analysis: " + "; ".join(problems))


def _held_out_by_seed(store: Store, exp_id: str) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for trial in store.trials(exp_id):
        if trial["status"] != "done":
            continue
        metrics = json.loads(trial["metrics_json"]) if trial.get("metrics_json") else {}
        value = metrics.get("test_mean_reward")
        if value is not None:
            out.setdefault(trial["algorithm"], {})[int(trial["seed"])] = float(value)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--bootstrap-seed", type=int, default=20261017)
    ap.add_argument("--protocol-doc", default="research/protocols/reinforce_promotion_v1.md")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    store = Store(args.store)
    exp = next((row for row in store.list_experiments() if row["id"] == args.experiment), None)
    if exp is None:
        raise SystemExit(f"unknown experiment {args.experiment}")
    cfg = json.loads(exp["config_json"])
    if cfg.get("protocol") != "reinforce_promotion_v1_strict_cap":
        raise SystemExit(f"unexpected protocol {cfg.get('protocol')!r} for REINFORCE promotion analysis")
    by_seed = _held_out_by_seed(store, args.experiment)
    try:
        require_complete_paired_data(by_seed, cfg)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    seeds = sorted(int(seed) for seed in cfg["seeds"])
    method = [by_seed[METHOD][seed] for seed in seeds]
    baseline = [by_seed[BASELINE][seed] for seed in seeds]
    result = paired_bootstrap_ci(method, baseline, resamples=RESAMPLES, seed=args.bootstrap_seed)
    statistic, p_value = wilcoxon_signed_rank(method, baseline)
    diffs = [m - b for m, b in zip(method, baseline, strict=True)]
    mde = min_detectable_effect(diffs, n=len(diffs))

    if result.verdict.startswith("supported"):
        scope_note = (
            "The supported result promotes REINFORCE only as a reproducible control on this grid "
            "task; it makes no claim about general RL performance or a comparison to evolutionary methods."
        )
    elif result.verdict.startswith("falsified"):
        scope_note = (
            "REINFORCE is not promoted by this study. A future RL comparison would require a new "
            "pre-registered algorithmic intervention and fresh method seeds; this fixed configuration "
            "must not be tuned against the observed endpoint."
        )
    else:
        scope_note = (
            "The result is inconclusive for promotion. Any future RL comparison requires a new "
            "pre-registered intervention and fresh method seeds; this fixed configuration must not be "
            "tuned against the observed endpoint."
        )

    lines = [
        "# REINFORCE promotion v1 — Pre-registered strict-cap analysis",
        "",
        f"Experiment `{args.experiment}` · protocol `{cfg['protocol']}` · {len(seeds)} paired method seeds · "
        f"budget {cfg['budget']:,} interactions/REINFORCE seed.",
        "",
        f"Analysis fixed in advance at `{args.protocol_doc}`. The endpoint is each seed's held-out "
        "base-task reward; all test seeds are disjoint from REINFORCE updates.",
        "",
        "## Endpoint completeness",
        "",
        f"All {len(seeds)} registered seeds are present and finite for `{METHOD}` and `{BASELINE}`.",
        "",
        "## Registered primary comparison",
        "",
        "| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |",
        "| --- | --- | --- | --- | --- | --- |",
        f"| `{METHOD}` − `{BASELINE}` | {result.point:+.3f} | [{result.lo:+.3f}, {result.hi:+.3f}] | "
        f"{'yes' if result.excludes_zero else 'no'} | {p_value:.4f} (W={statistic:.1f}) | **{result.verdict}** |",
        "",
        f"Paired bootstrap: {RESAMPLES:,} resamples, fixed RNG seed `{args.bootstrap_seed}`. "
        "The confidence interval is the registered decision rule; Wilcoxon is a concordance check.",
        "",
        "## Precision and scope",
        "",
        f"The observed paired minimum detectable effect at n={len(seeds)} is {mde:.3f}. {scope_note}",
        "",
        "## Reproduction",
        "",
        "```bash",
        "uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python",
        ".venv/bin/origin-run --config configs/reinforce_promotion_v1.json --store runs --jobs $(nproc)",
        f".venv/bin/python scripts/analyze_reinforce.py --store runs --experiment {args.experiment} "
        f"--bootstrap-seed {args.bootstrap_seed} --protocol-doc {args.protocol_doc} --out {args.out}",
        "```",
        "",
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"[analyze_reinforce] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
