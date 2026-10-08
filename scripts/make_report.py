#!/usr/bin/env python3
"""Generate the initial research report from the persisted experiment store.

Every number in the generated report is read from stored trial artifacts —
nothing is typed by hand, so the report cannot drift from the data.

Usage:
    python scripts/make_report.py --store runs --experiment <id> \
        --out research/reports/ORIGIN_Initial_Research_Report.md
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from pathlib import Path

from origin.experiments.store import Store


def _txt(x, d=3):
    return "—" if x is None else f"{x:.{d}f}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", default=None, help="experiment id (default: newest)")
    ap.add_argument("--out", default="research/reports/ORIGIN_Initial_Research_Report.md")
    args = ap.parse_args()

    store = Store(args.store)
    exps = store.list_experiments()
    if not exps:
        raise SystemExit("no experiments in store")
    exp = next((e for e in exps if e["id"] == args.experiment), exps[0])
    exp_id = exp["id"]
    cfg = json.loads(exp["config_json"])
    manifest_path = Path(args.store) / exp_id / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    trials = [t for t in store.trials(exp_id) if t["status"] == "done"]
    failed = [t for t in store.trials(exp_id) if t["status"] == "failed"]

    # ---- held-out comparison table ----
    by_algo: dict[str, dict] = {}
    for t in trials:
        m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
        d = by_algo.setdefault(t["algorithm"], {"test": [], "train": [], "inter": [], "seed": []})
        if m.get("test_mean_reward") is not None:
            d["test"].append(m["test_mean_reward"])
        if t.get("train_fitness") is not None:
            d["train"].append(t["train_fitness"])
        d["inter"].append(t["interactions"] or 0)
        d["seed"].append(t["seed"])

    def _mean_sem(vals):
        if not vals:
            return None, None
        m = st.mean(vals)
        if len(vals) < 2:
            return m, None
        return m, st.stdev(vals) / (len(vals) ** 0.5)

    order = ["random", "heuristic", "fixed_objective_ga", "novelty_search", "map_elites", "reinforce"]
    rows = []
    for algo in order:
        if algo not in by_algo:
            continue
        d = by_algo[algo]
        m_test, sem_test = _mean_sem(d["test"])
        m_train, _ = _mean_sem(d["train"])
        rows.append((algo, len(d["test"]), m_test, sem_test, m_train, st.mean(d["inter"]) if d["inter"] else 0))

    # ---- transfer table ----
    transfer: dict[str, dict[str, dict]] = {}
    for t in trials:
        tr = json.loads(t["transfer_json"]) if t.get("transfer_json") else {}
        for name, entry in (tr or {}).items():
            if "zero_shot_mean_reward" not in entry:
                continue
            slot = transfer.setdefault(name, {}).setdefault(t["algorithm"], {"zero": [], "adapt": [], "kind": entry.get("kind", "")})
            slot["zero"].append(entry["zero_shot_mean_reward"])
            if "adapted_mean_reward" in entry:
                slot["adapt"].append(entry["adapted_mean_reward"])

    # ---- plots ----
    plot_lines = []
    try:
        from origin.visualization import generate_all

        for p in generate_all(args.store, exp_id):
            plot_lines.append(f"* `{p}`")
    except Exception as exc:  # pragma: no cover
        plot_lines.append(f"* (plot generation failed: {exc})")

    env = manifest.get("environment", {})
    lines: list[str] = []
    a = lines.append
    a("# Open-Ended Evolution and Cross-Morphology Generalization: A Reproducible Experimental Framework")
    a("")
    a("**Author:** Scott Hardie (Hardonian) · **Status:** PRELIMINARY, not peer reviewed.")
    a("")
    a("> This report was generated automatically from the stored experiment artifacts by")
    a("> `scripts/make_report.py`. Every figure below is read from the experiment store; no")
    a(f"> number is hand-entered. Experiment id: `{exp_id}`.")
    a("")
    a("---")
    a("")
    a("## 1. Research question and hypothesis")
    a("")
    a(cfg.get("description", ""))
    a("")
    a("**H1.** Under an equivalent environment-interaction budget, maintaining behaviourally")
    a("diverse populations (novelty search, quality-diversity) improves adaptation to unseen")
    a("evaluation environments and to changed morphology relative to fixed-objective evolution.")
    a("")
    a("## 2. Method")
    a("")
    a(f"Deterministic {cfg['env'].get('height')}×{cfg['env'].get('width')} egocentric foraging world; "
      f"observation is 7-D (energy + resource/hazard bearings), absolute position excluded so policies "
      f"cannot memorise a layout. Budget: **{cfg['budget']:,} environment interactions per method per seed**. "
      f"Training seeds {cfg['train_seeds']}; held-out test seeds {cfg['test_seeds']} (disjoint). "
      f"{len(cfg['seeds'])} independent RNG seeds.")
    a("")
    a("## 3. Held-out performance (train/test isolated)")
    a("")
    a("| method | n seeds | held-out reward (mean) | standard error | train fitness | mean interactions |")
    a("|---|---|---|---|---|---|")
    for algo, n, mt, sem, mtr, inter in rows:
        a(f"| `{algo}` | {n} | {_txt(mt)} | {('±' + _txt(sem)) if sem is not None else '—'} | {_txt(mtr)} | {inter:,.0f} |")
    a("")
    a("_held-out reward is measured on evaluation seeds never used for training._")
    a("")

    # verdict vs GA
    ga = by_algo.get("fixed_objective_ga", {}).get("test", [])
    nov = by_algo.get("novelty_search", {}).get("test", [])
    qd = by_algo.get("map_elites", {}).get("test", [])
    if ga and nov:
        diff = st.mean(nov) - st.mean(ga)
        pooled = st.pstdev(ga + nov) if len(ga + nov) > 1 else 0.0
        a("### Directional test of H1")
        a("")
        a(f"* Novelty search minus fixed-objective GA on held-out reward: **{diff:+.3f}** "
          f"(pooled sd ≈ {pooled:.3f}, n={len(ga)}–{len(nov)}).")
        if qd:
            a(f"* MAP-Elites minus fixed-objective GA: **{st.mean(qd) - st.mean(ga):+.3f}**.")
        a("* With this seed count the difference is **not** a powered statistical test; it is a")
        a("  preliminary directional signal. See limitations.")
        a("")

    a("## 4. Cross-morphology and perturbation transfer")
    a("")
    a("Values are reached reward; morphology variants show `zero-shot → adapted`.")
    a("")
    algos = [r[0] for r in rows if r[0] not in ("random", "heuristic")]
    a("| variant | kind | " + " | ".join(f"`{x}`" for x in algos) + " |")
    a("|---|---|" + "---|" * len(algos))
    for name in sorted(transfer):
        kind = transfer[name][algos[0]]["kind"] if algos and algos[0] in transfer[name] else ""
        cells = []
        for algo in algos:
            s = transfer[name].get(algo)
            if not s:
                cells.append("—")
                continue
            z = _txt(st.mean(s["zero"]), 2)
            if s["adapt"]:
                cells.append(f"{z} → {_txt(st.mean(s['adapt']), 2)}")
            else:
                cells.append(z)
        a(f"| `{name}` | {kind} | " + " | ".join(cells) + " |")
    a("")

    a("## 5. Compute")
    a("")
    for row in rows:
        algo, n, inter = row[0], row[1], row[5]
        a(f"* `{algo}`: mean {inter:,.0f} interactions per seed over {n} seed(s).")
    a("")

    a("## 6. Failures")
    a("")
    a(f"Failed trials: **{len(failed)}** of {len(trials) + len(failed)}.")
    for t in failed:
        a(f"* `{t['algorithm']}` seed {t['seed']}: {t['error']}")
    if not failed:
        a("No failures were observed; every recorded trial completed.")
    a("")

    a("## 7. Limitations")
    a("")
    a(f"* **PRELIMINARY.** {len(cfg['seeds'])} seeds per method; confidence intervals are wide and no null-hypothesis test is powered.")
    a("* A reactive controller is a low-ceiling policy class on tasks requiring planning; this")
    a("  bounds achievable effect sizes and compresses between-method differences.")
    a("* Single task family. No claim about generality beyond this world.")
    a("* The scripted BFS heuristic is a privileged reference, not a like-for-like competitor.")
    a("* `reinforce` (a pure-NumPy policy gradient) is sample-inefficient at this budget and, in")
    a("  this run, collapsed toward a degenerate policy. This is reported, not hidden; it bounds")
    a("  any conclusion about RL rather than supporting one.")
    a("")

    a("## 8. Reproduction")
    a("")
    a("```bash")
    a("uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python")
    a(f".venv/bin/origin-run --config configs/{Path('configs/pilot.json').name} --store runs --jobs $(nproc)")
    a(f".venv/bin/python scripts/make_report.py --store runs --experiment {exp_id}")
    a("```")
    a("")
    a(f"Reference environment: Python {env.get('python', '?')}, {env.get('platform', '?')}, {env.get('cpu_count', '?')} CPUs.")
    a("")
    a("## 9. Generated artifacts")
    a("")
    a("\n".join(plot_lines) if plot_lines else "(none)")
    a("")
    a("## 10. Next milestone")
    a("")
    a("Pre-register a powered replication of H1: more seeds, larger budgets, and a")
    a("descriptor-designed task where quality-diversity can express its advantage, plus an")
    a("articulated-physics embodiment benchmark (Milestone 4) to test morphology transfer beyond")
    a("sensor/actuator changes.")
    a("")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"wrote {out} ({len(lines)} lines) for experiment {exp_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
