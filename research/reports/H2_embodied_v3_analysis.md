experiment 1bdb4b622748: 25 completed trials, 5 methods

== held-out test performance (unseen seeds) ==
method                  n     mean      sd  travelled   fall  success train inter eval inter
map_elites              5   14.265   8.428     4.5163   0.00     0.20       38413        534
novelty_search          5   13.589   3.940     4.1642   0.00     0.00       38451        540
fixed_objective_ga      5   11.717   2.791     4.1111   0.00     0.00       38446        540
random                  5    1.247   0.000     3.1674   0.00     0.00           0        540
scripted_gait           5  -17.438   0.000     2.0158   0.00     0.00           0        540

== transfer across physically distinct bodies ==
body plan           zero-shot   adapted     gain  zs fall  ad fall   n
body_centipede         -3.768     9.442    9.504     0.00     0.00  25
body_heavy_slow        -6.096     5.728    6.971     0.00     0.00  25
body_short_stiff       -6.208     1.799    7.109     0.00     0.07  25
body_slippery          -3.743     6.285    6.663     0.00     0.00  25
MEAN                   -1.748     5.814

== environmental perturbations (zero-shot) ==
  far_target         mean=+7.996 n=15
  heavy_gravity      mean=+6.723 n=15
  low_gravity        mean=-4.306 n=15
  low_grip           mean=-1.727 n=15
  short_episode      mean=+8.130 n=15

== paired comparison on 5 shared seeds ==
  map_elites - fixed_objective_ga: +2.548  95% paired bootstrap CI [-2.480, +9.272]
  Wilcoxon signed-rank p = 0.4375
  minimum detectable effect at this n = 9.294 (observed |diff| = 2.548)
  -> CI spans 0 at this sample size: NOT statistically resolved.

== reproducibility ==
  config_hash=d7911427b4b7 git_sha=9be1994d6c743b7344027186a0e5f86632b6f207
  rerun: .venv/bin/origin-run --config configs/embodied_transfer_v3.json --store runs --jobs 32
