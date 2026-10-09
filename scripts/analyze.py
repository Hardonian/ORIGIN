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
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np

from origin.evaluation.stats import (
    bootstrap_diff_ci,
    mann_whitney,
    min_detectable_effect,
    paired_bootstrap_ci,
    wilcoxon_signed_rank,
)
from origin.experiments.store import Store

BOOTSTRAP_RESAMPLES = 10_000
BOOTSTRAP_SEED = 20261008           # study 1 (independent design)
PAIRED_BOOTSTRAP_SEED = 20261009    # study v2 (paired design) — distinct by design
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


def _held_out_by_seed(store: Store, exp_id: str) -> dict[str, dict[int, float]]:
    out: dict[str, dict[int, float]] = {}
    for t in store.trials(exp_id):
        if t["status"] != "done":
            continue
        m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
        v = m.get("test_mean_reward")
        if v is not None:
            out.setdefault(t["algorithm"], {})[int(t["seed"])] = float(v)
    return out


def _aligned(a: dict[int, float], b: dict[int, float]) -> tuple[list[float], list[float], list[int]]:
    """Align two per-seed maps on their shared seeds (paired design)."""
    seeds = sorted(set(a) & set(b))
    return [a[s] for s in seeds], [b[s] for s in seeds], seeds


def _undertest(a: list[float], b: list[float]) -> tuple[float, float, float]:
    r = bootstrap_diff_ci(a, b, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED)
    return r.point, r.lo, r.hi


def _verdict_for(a: list[float], b: list[float]) -> str:
    return bootstrap_diff_ci(a, b, resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED).verdict


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", default=None)
    ap.add_argument("--design", choices=["independent", "paired"], default="independent",
                    help="registered design: 'independent' (study 1) or 'paired' (study v2/v3)")
    ap.add_argument("--bootstrap-seed", type=int, default=None,
                    help="override the registered bootstrap seed (studies use distinct seeds by design)")
    ap.add_argument("--protocol-doc", default=None, help="path of the protocol document to cite")
    ap.add_argument(
        "--out",
        required=True,
        help="output Markdown path (required to prevent accidentally overwriting a report)",
    )
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
    by_seed = _held_out_by_seed(store, exp_id)

    paired = args.design == "paired"
    protocol_doc = args.protocol_doc or ("research/protocols/paired_v2.md" if paired else "research/protocols/powered_replication.md")
    boot_seed = args.bootstrap_seed if args.bootstrap_seed is not None else (PAIRED_BOOTSTRAP_SEED if paired else BOOTSTRAP_SEED)

    lines: list[str] = []
    a = lines.append
    title = "H1 — Pre-registered analysis (paired design, study v2)" if paired else "H1 — Pre-registered analysis (powered replication)"
    a(f"# {title}")
    a("")
    a(f"Experiment `{exp_id}` · protocol `{cfg.get('protocol')}` · "
      f"{len(cfg.get('seeds', []))} seeds · budget {cfg.get('budget'):,} interactions/method/seed.")
    a("")
    a(f"Analysis fixed in advance at `{protocol_doc}`:")
    if paired:
        a(f"paired bootstrap {BOOTSTRAP_RESAMPLES:,} resamples (seed {boot_seed}) over the mean of the")
        a(f"per-seed differences, and a two-sided Wilcoxon signed-rank test (α = {ALPHA}). Per the")
        a("registration, no other test decides the verdict and it is not switched.")
    else:
        a(f"bootstrap {BOOTSTRAP_RESAMPLES:,} resamples (seed {boot_seed}) and a two-sided")
        a(f"Mann–Whitney U (α = {ALPHA}). No other test is run and the conclusion is not switched.")
    a("")

    a("## Descriptive (held-out mean reward per method)")
    a("")
    a("| method | n | mean | sd | min | max |")
    a("| --- | --- | --- | --- | --- | --- |")
    for algo in ["random", "heuristic", BASELINE, *DIVERSITY, "reinforce"]:
        if algo not in data:
            continue
        v = np.asarray(data[algo])
        a(f"| `{algo}` | {len(v)} | {v.mean():.3f} | {v.std(ddof=1):.3f} | {v.min():.3f} | {v.max():.3f} |")
    a("")

    verdicts: dict[str, str] = {}
    if paired:
        a("## Registered primary: paired test, diversity method vs fixed-objective GA")
        a("")
        a("| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |")
        a("| --- | --- | --- | --- | --- | --- |")
        for method in DIVERSITY:
            if method not in by_seed or BASELINE not in by_seed:
                continue
            ma, mb, seeds = _aligned(by_seed[method], by_seed[BASELINE])
            if not seeds:
                continue
            r = paired_bootstrap_ci(ma, mb, resamples=BOOTSTRAP_RESAMPLES, seed=boot_seed)
            stat, p = wilcoxon_signed_rank(ma, mb)
            verdicts[method] = r.verdict
            a(f"| `{method}` − `{BASELINE}` | {r.point:+.3f} | [{r.lo:+.3f}, {r.hi:+.3f}] | "
              f"{'yes' if r.excludes_zero else 'no'} | {p:.4f} (W={stat:.1f}) | **{r.verdict}** |")
        a("")
        a(f"Paired on {len(set(cfg.get('seeds', [])))} method seeds. Uncorrected p-values are shown;")
        a(f"a Bonferroni threshold for two comparisons is α/2 = {ALPHA / 2:.3f} (reported, not applied).")
        a("")
        a("### Bounded null (minimum detectable effect)")
        a("")
        a("An inconclusive result is only meaningful with the effect size the design could")
        a("have detected. At this n, 80% power, α = 0.05 (two-sided):")
        a("")
        for method in DIVERSITY:
            if method not in by_seed or BASELINE not in by_seed:
                continue
            ma, mb, _seeds = _aligned(by_seed[method], by_seed[BASELINE])
            diffs = [x - y for x, y in zip(ma, mb, strict=False)]
            mde = min_detectable_effect(diffs, n=len(diffs))
            observed = abs(sum(diffs) / len(diffs)) if diffs else 0.0
            a(f"* `{method}`: minimum detectable paired effect = {mde:.3f} "
              f"(observed |mean diff| = {observed:.3f}).")
        a("")
        a("If the CI spans zero, the correct statement is that any true effect is smaller")
        a("than the minimum detectable effect — not that no effect exists.")
        a("")
        a("### Secondary (reported, not decisive)")
        a("")
        a("The unpaired Mann–Whitney U on the same data, for comparability with study 1:")
        a("")
        for method in DIVERSITY:
            if method in data:
                U, p = mann_whitney(data[method], data[BASELINE])
                a(f"* `{method}`: U={U:.1f}, p={p:.4f} (unpaired, secondary).")
        a("")
    else:
        base = data[BASELINE]
        a("## Registered test: diversity method vs fixed-objective GA")
        a("")
        a("| comparison | mean diff | 95% bootstrap CI | CI excludes 0? | Mann–Whitney U p | verdict |")
        a("|---|---|---|---|---|---|")
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
        if paired:
            ma, mb, _seeds = _aligned(by_seed[method], by_seed[BASELINE])
            r = paired_bootstrap_ci(ma, mb, resamples=BOOTSTRAP_RESAMPLES, seed=boot_seed)
        else:
            r = bootstrap_diff_ci(data[method], data[BASELINE], resamples=BOOTSTRAP_RESAMPLES, seed=BOOTSTRAP_SEED)
        a(f"* **`{method}`**: {verdict}. Point estimate {r.point:+.3f} "
          f"(95% CI [{r.lo:+.3f}, {r.hi:+.3f}]).")
    a("")
    a("Reminder of scope: this is a single task family with reactive controllers. A")
    a("positive direction is evidence about *this* world, not a general claim, and a")
    a("CI spanning 0 is reported as inconclusive rather than as a near-miss.")
    a("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"\n[analyze] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
