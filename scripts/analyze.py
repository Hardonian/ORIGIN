#!/usr/bin/env python3
"""Pre-registered analysis of H1 (see research/protocols/powered_replication.md).

Implements exactly the registered analysis and nothing else:

  * effect size = difference in mean held-out reward vs fixed-objective GA,
    with a bootstrap 95% percentile CI (10,000 resamples, RNG seed 20261008);
  * two-sided Mann-Whitney U on per-seed held-out rewards (alpha = 0.05);
  * verdict per the registered decision rule (CI excludes 0 -> supported/falsified,
    otherwise inconclusive).

No additional tests are run and the conclusion is not switched to a more
favourable statistic. Every input comes from the experiment store.

Usage:
    python scripts/analyze.py --store runs --experiment <id> \
        --out research/reports/H1_powered_analysis.md
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from origin.evaluation.stats import bootstrap_diff_ci, mann_whitney
from origin.experiments.store import Store

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261008
ALPHA = 0.05
DIVERSITY = ["novelty_search", "map_elites"]
BASELINE = "fixed_objective_ga"


def _held_out(store: Store, exp_id: str) -> dict[str, list[float]]:
    by_algo: dict[str, list[tuple[int, float]]] = {}
    for t in store.trials(exp_id):
        if t["status"] != "done":
            continue
        m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
        v = m.get("test_mean_reward")
        if v is not None:
            by_algo.setdefault(t["algorithm"], []).append((int(t["seed"]), float(v)))
    # deterministic order by seed so results are reproducible
    return {a: [v for _, v in sorted(pairs)] for a, pairs in by_algo.items()}


def _undertest(a: list[float], b: list[float]) -> tuple[float, float, float]:
    r = bootstrap_diff_ci(a, b, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED)
    return r.point, r.lo, r.hi


def _verdict_for(a: list[float], b: list[float]) -> str:
    return bootstrap_diff_ci(a, b, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED).verdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", default=None)
    ap.add_argument("--out", default="research/reports/H1_powered_analysis.md")
    args = ap.parse_args()

    store = Store(args.store)
    exps = store.list_experiments()
    if not exps:
        raise SystemExit("no experiments in store")
    exp = next((e for e in exps if e["id"] == args.experiment), exps[0])
    exp_id = exp["id"]
    cfg = json.loads(exp["config_json"])

    data = _held_out(store, exp_id)
    if BASELINE not in data:
        raise SystemExit(f"baseline {BASELINE} has no held-out results in {exp_id}")

    base = data[BASELINE]

    lines: list[str] = []
    a = lines.append
    a("# H1 — Pre-registered analysis (powered replication)")
    a("")
    a(f"Experiment `{exp_id}` · protocol `{cfg.get('protocol')}` · "
      f"{len(cfg.get('seeds', []))} seeds · budget {cfg.get('budget'):,} interactions/method/seed.")
    a("")
    a("Analysis fixed in advance at `research/protocols/powered_replication.md`:")
    a(f"bootstrap {BOOTSTRAP_RESAMPLES:,} resamples (seed {BOOTSTRAP_SEED}) and a two-sided")
    a(f"Mann–Whitney U (α = {ALPHA}). No other test is run and the conclusion is not switched.")
    a("")

    a("## Descriptive (held-out mean reward per method)")
    a("")
    a("| method | n | mean | sd | min | max |")
    a("|---|---|---|---|---|---|")
    for algo in ["random", "heuristic", BASELINE, *DIVERSITY, "reinforce"]:
        if algo not in data:
            continue
        v = np.asarray(data[algo])
        a(f"| `{algo}` | {len(v)} | {v.mean():.3f} | {v.std(ddof=1):.3f} | {v.min():.3f} | {v.max():.3f} |")
    a("")

    a("## Registered test: diversity method vs fixed-objective GA")
    a("")
    a("| comparison | mean diff | 95% bootstrap CI | CI excludes 0? | Mann–Whitney U p | verdict |")
    a("|---|---|---|---|---|---|")
    verdicts: dict[str, str] = {}
    for method in DIVERSITY:
        if method not in data:
            continue
        point, lo, hi = _undertest(data[method], base)
        U, p = mann_whitney(data[method], base)
        excludes = not (lo <= 0.0 <= hi)
        verdict = _verdict_for(data[method], base)
        verdicts[method] = verdict
        a(f"| `{method}` − `{BASELINE}` | {point:+.3f} | [{lo:+.3f}, {hi:+.3f}] | "
          f"{'yes' if excludes else 'no'} | {p:.4f} (U={U:.1f}) | **{verdict}** |")
    a("")
    a("Uncorrected p-values are shown. For reference, a Bonferroni threshold for two")
    a(f"comparisons is α/2 = {ALPHA / 2:.3f}. No correction is applied to the verdict.")
    a("")

    a("## Interpretation")
    a("")
    for method, verdict in verdicts.items():
        point, lo, hi = _undertest(data[method], base)
        a(f"* **`{method}`**: {verdict}. Point estimate {point:+.3f} "
          f"(95% CI [{lo:+.3f}, {hi:+.3f}]).")
    a("")
    a("Reminder of scope: this is a single task family with reactive controllers. A")
    a("positive direction is evidence about *this* world, not a general claim, and a")
    a("CI spanning 0 is reported as inconclusive rather than as a near-miss.")
    a("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print("\n".join(lines))
    print(f"\n[analyze] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
