#!/usr/bin/env python
"""Analyse an embodied morphology-transfer campaign from the ORIGIN store.

Reports, from the stored trials only (nothing hand-entered):
  * held-out test performance per algorithm, with spread and n
  * zero-shot vs adapted transfer, per body plan and aggregated
  * a paired algorithm comparison on shared seeds, with a bootstrap CI,
    an explicit minimum detectable effect, and an honest power caveat
  * compute cost (interactions) per method

Usage:
  python scripts/analyze_embodied.py --store runs --experiment aa1175d6c5aa
"""

from __future__ import annotations

import argparse
import json
import statistics as st
from typing import Any

import numpy as np

from origin.evaluation.stats import min_detectable_effect, paired_bootstrap_ci, wilcoxon_signed_rank
from origin.experiments.store import Store


def _load(store: Store, exp_id: str) -> list[dict[str, Any]]:
    trials = store.trials(exp_id)
    out = []
    for t in trials:
        if t["status"] != "done":
            continue
        m = json.loads(t["metrics_json"]) if t.get("metrics_json") else {}
        tr = json.loads(t["transfer_json"]) if t.get("transfer_json") else {}
        out.append({
            "algorithm": t["algorithm"],
            "seed": t["seed"],
            "interactions": t["interactions"],
            "test_reward": m.get("test_mean_reward"),
            "travelled": m.get("test_mean_distance_travelled"),
            "fall_rate": m.get("test_fall_rate"),
            "target_rate": m.get("test_target_rate"),
            "wall_seconds": m.get("wall_seconds"),
            "eval_interactions": m.get("evaluation_interactions"),
            "transfer": tr,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", default="runs")
    ap.add_argument("--experiment", required=True)
    ap.add_argument("--bootstrap-seed", type=int, default=20261012)
    args = ap.parse_args()

    store = Store(args.store)
    rows = _load(store, args.experiment)
    if not rows:
        print(f"no completed trials for experiment {args.experiment}")
        return 1

    by_algo: dict[str, list[dict[str, Any]]] = {}
    for r in rows:
        by_algo.setdefault(r["algorithm"], []).append(r)

    print(f"experiment {args.experiment}: {len(rows)} completed trials, "
          f"{len(by_algo)} methods\n")

    print("== held-out test performance (unseen seeds) ==")
    print(f"{'method':22s} {'n':>2s} {'mean':>8s} {'sd':>7s} {'travelled':>10s} "
          f"{'fall':>6s} {'success':>8s} {'train inter':>11s} {'eval inter':>10s}")
    for algo, rs in sorted(by_algo.items(), key=lambda kv: -np.mean([r["test_reward"] or 0 for r in kv[1]])):
        vals = [r["test_reward"] for r in rs if r["test_reward"] is not None]
        trav = [r["travelled"] for r in rs if r["travelled"] is not None]
        fall = [r["fall_rate"] for r in rs if r["fall_rate"] is not None]
        succ = [r["target_rate"] for r in rs if r.get("target_rate") is not None]
        inter = [r["interactions"] for r in rs]
        ev_inter = [r["eval_interactions"] for r in rs if r.get("eval_interactions") is not None]
        sd = st.stdev(vals) if len(vals) > 1 else 0.0
        print(f"{algo:22s} {len(vals):2d} {np.mean(vals):8.3f} {sd:7.3f} "
              f"{(np.mean(trav) if trav else float('nan')):10.4f} "
              f"{(np.mean(fall) if fall else float('nan')):6.2f} "
              f"{(np.mean(succ) if succ else float('nan')):8.2f} "
              f"{int(np.mean(inter)):11d} "
              f"{(int(np.mean(ev_inter)) if ev_inter else float('nan')):10.0f}")

    # ---- transfer: zero-shot vs adapted, per body plan -------------------
    morph_names: list[str] = []
    for r in rows:
        for name, entry in r["transfer"].items():
            if entry.get("kind") == "morphology" and name not in morph_names:
                morph_names.append(name)
    if morph_names:
        print("\n== transfer across physically distinct bodies ==")
        print(f"{'body plan':18s} {'zero-shot':>10s} {'adapted':>9s} {'gain':>8s} "
              f"{'zs fall':>8s} {'ad fall':>8s} {'n':>3s}")
        for name in sorted(morph_names):
            zs, ad, gz, fz, fa = [], [], [], [], []
            for r in rows:
                e = r["transfer"].get(name)
                if not e or "zero_shot_mean_reward" not in e:
                    continue
                zs.append(e["zero_shot_mean_reward"])
                fz.append(e.get("zero_shot_fall_rate", float("nan")))
                if "adapted_mean_reward" in e:
                    ad.append(e["adapted_mean_reward"])
                    fa.append(e.get("adapted_fall_rate", float("nan")))
                    if "adaptation_gain" in e:
                        gz.append(e["adaptation_gain"])
            print(f"{name:18s} {np.mean(zs):10.3f} "
                  f"{(np.mean(ad) if ad else float('nan')):9.3f} "
                  f"{(np.mean(gz) if gz else float('nan')):8.3f} "
                  f"{np.nanmean(fz):8.2f} {(np.nanmean(fa) if fa else float('nan')):8.2f} {len(zs):3d}")
        all_zs = [e["zero_shot_mean_reward"] for r in rows for e in r["transfer"].values()
                  if e.get("kind") == "morphology" and "zero_shot_mean_reward" in e]
        all_ad = [e["adapted_mean_reward"] for r in rows for e in r["transfer"].values()
                  if e.get("kind") == "morphology" and "adapted_mean_reward" in e]
        print(f"{'MEAN':18s} {np.mean(all_zs):10.3f} {(np.mean(all_ad) if all_ad else float('nan')):9.3f}")

    pert_names = [n for r in rows for n, e in r["transfer"].items() if e.get("kind") == "perturbation"]
    if pert_names:
        print("\n== environmental perturbations (zero-shot) ==")
        for name in sorted(set(pert_names)):
            vals = [e["zero_shot_mean_reward"] for r in rows
                    for n, e in r["transfer"].items()
                    if n == name and e.get("kind") == "perturbation" and "zero_shot_mean_reward" in e]
            if vals:
                print(f"  {name:18s} mean={np.mean(vals):+.3f} n={len(vals)}")

    # ---- paired algorithm comparison on shared seeds ---------------------
    # Explicitly the quality-diversity vs fixed-objective comparison (the embodied
    # analogue of H1), not whichever two methods happen to be first.
    preferred = [a for a in ("map_elites", "fixed_objective_ga") if a in by_algo]
    if len(preferred) == 2:
        a1, a2 = preferred[1], preferred[0]  # report (map_elites - fixed_objective_ga)
        s1 = {r["seed"]: r["test_reward"] for r in by_algo[a1] if r["test_reward"] is not None}
        s2 = {r["seed"]: r["test_reward"] for r in by_algo[a2] if r["test_reward"] is not None}
        shared = sorted(set(s1) & set(s2))
        if len(shared) >= 2:
            a_vals = np.array([s1[k] for k in shared], dtype=float)
            b_vals = np.array([s2[k] for k in shared], dtype=float)
            diff = paired_bootstrap_ci(b_vals, a_vals, seed=args.bootstrap_seed)
            diffs = (b_vals - a_vals).tolist()
            mde = min_detectable_effect(diffs)
            _, pval = wilcoxon_signed_rank(b_vals, a_vals)
            print(f"\n== paired comparison on {len(shared)} shared seeds ==")
            print(f"  {a2} - {a1}: {diff.point:+.3f}  95% paired bootstrap CI [{diff.lo:+.3f}, {diff.hi:+.3f}]")
            print(f"  Wilcoxon signed-rank p = {pval:.4f}")
            print(f"  minimum detectable effect at this n = {mde:.3f} "
                  f"(observed |diff| = {abs(diff.point):.3f})")
            if diff.lo > 0 or diff.hi < 0:
                print("  -> CI excludes 0: a difference is supported at this n (still preliminary).")
            else:
                print("  -> CI spans 0 at this sample size: NOT statistically resolved.")

    print("\n== reproducibility ==")
    exp = store.experiment(args.experiment) or {}
    print(f"  config_hash={exp.get('config_hash')} git_sha={exp.get('git_sha')}")
    print("  rerun: .venv/bin/origin-run --config configs/embodied_transfer.json --store runs --jobs 6")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
