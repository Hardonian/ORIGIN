# REINFORCE promotion v1 — Pre-registered strict-cap analysis

Experiment `b4c379fcddb7` · protocol `reinforce_promotion_v1_strict_cap` · 40 paired method seeds · budget 500,000 interactions/REINFORCE seed.

Analysis fixed in advance at `research\protocols\reinforce_promotion_v1.md`. The endpoint is each seed's held-out base-task reward; all test seeds are disjoint from REINFORCE updates.

## Endpoint completeness

All 40 registered seeds are present and finite for `reinforce` and `random`.

## Registered primary comparison

| comparison | mean paired diff | 95% paired bootstrap CI | CI excludes 0? | Wilcoxon p | verdict |
| --- | --- | --- | --- | --- | --- |
| `reinforce` − `random` | -1.740 | [-2.126, -1.301] | yes | 0.0000 (W=45.0) | **falsified for this method** |

Paired bootstrap: 10,000 resamples, fixed RNG seed `20261017`. The confidence interval is the registered decision rule; Wilcoxon is a concordance check.

## Precision and scope

The observed paired minimum detectable effect at n=40 is 0.596. REINFORCE is not promoted by this study. A future RL comparison would require a new pre-registered algorithmic intervention and fresh method seeds; this fixed configuration must not be tuned against the observed endpoint.

## Reproduction

```bash
uv venv --python 3.12 .venv && uv pip install -e '.[dev]' --python .venv/bin/python
.venv/bin/origin-run --config configs/reinforce_promotion_v1.json --store runs --jobs $(nproc)
.venv/bin/python scripts/analyze_reinforce.py --store runs --experiment b4c379fcddb7 --bootstrap-seed 20261017 --protocol-doc research\protocols\reinforce_promotion_v1.md --out research\reports\REINFORCE_promotion_v1_analysis.md
```
