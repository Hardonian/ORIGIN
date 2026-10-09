# Protocol — Actor-Critic (PPO) Baselines v2

**Registered before execution.** This document supersedes the nonconformant
v1 registration for confirmatory purposes. The completed v1 grid run is
archived as exploratory in `research/reports/ACTOR_CRITIC_V1_CONFIGURATION_AUDIT.md`.
No v2 trial may begin until this document and both referenced JSON
configurations are committed unchanged.

## Scope

This is a fixed-configuration evaluation of ORIGIN's pure-NumPy clipped PPO
Actor-Critic implementation. It asks whether adding a learned value baseline
improves the existing policy-gradient control on gridworld and whether PPO can
produce upright embodied locomotion beyond a random control. It is not a test
of MAP-Elites or of general intelligence.

## H-AC.1 — Gridworld value-estimation comparison

Under the exact configuration in `configs/actor_critic_grid_v2.json`, PPO has
higher mean held-out base-task reward than REINFORCE after at most 500,000
training interactions per learned-method seed.

* **Task:** 10x10 random-terrain gridworld, 100-step episodes, 2% obstacles,
  five resources, no hazards or regeneration; the JSON configuration is the
  complete environment specification.
* **Train/test isolation:** train seeds `[11, 22, 33, 44]`; held-out seeds
  `[101, 202, 303, 404]`.
* **Methods:** confirmatory `ppo` versus `reinforce`. `random` and `heuristic`
  are descriptive controls only.
* **Paired method seeds:** `[400 ... 439]` (n=40), fresh and disjoint from the
  earlier REINFORCE and PPO v1 campaigns.
* **Learners:** both use a 7-24-5 MLP and four episodes per update. PPO uses
  actor learning rate 0.008, critic learning rate 0.012, gamma 0.99, GAE lambda
  0.95, clipping 0.20, four optimization epochs, and entropy coefficient
  0.015. REINFORCE uses learning rate 0.01, gamma 0.99, and entropy coefficient
  0.02.

## H-AC.2 — Embodied locomotion comparison

Under the exact configuration in `configs/actor_critic_embodied_v2.json`, PPO
has higher mean held-out reward than random after at most 300,000 training
interactions per PPO seed, while recorded evaluation episodes remain upright.

* **Task/body:** an eight-link yaw-jointed `worm`; 8.0-second episodes;
  0.16 m links, 0.035 m radius, 0.25 kg/link, 2.5 N m motor cap, lateral and
  longitudinal friction 1.25 and 0.20, respectively. The JSON configuration
  fixes all remaining simulator values.
* **Train/test isolation:** train seeds `[11, 22, 33, 44]`; held-out seeds
  `[101, 202, 303, 404]`.
* **Methods:** confirmatory `ppo` versus `random`; `scripted_gait` is
  descriptive only.
* **Paired method seeds:** `[500 ... 519]` (n=20), fresh and disjoint from
  every prior embodied campaign.
* **Calibration:** the exact body configuration must pass
  `scripts/probe_embodied_morphology.py` before this campaign. Its evidence
  file, configuration hash, and a representative persisted trajectory are
  required reporting artifacts.

## Shared accounting and analysis

1. A learned trial may not exceed its registered cap. Complete updates that do
   not fit in the remaining budget are not started. Held-out evaluation steps
   are stored separately as `evaluation_interactions`.
2. For each registered seed, calculate PPO minus the named baseline on held-out
   mean reward. `scripts/analyze_actor_critic.py` must verify the exact stored
   JSON configuration, complete paired seed coverage, finite values, and the
   training cap before analysis.
3. Use a 10,000-resample percentile paired-bootstrap 95% interval with fixed
   RNG seed `20261019`; report a two-sided Wilcoxon signed-rank result as a
   concordance check.
4. A positive point estimate with an interval excluding zero is **supported**;
   a negative point estimate with an interval excluding zero is **falsified for
   this method and task**; otherwise the result is **inconclusive**. Report the
   observed minimum detectable effect for any inconclusive result.
5. The grid and embodied endpoints are separate registered tests. Neither may
   be substituted for the other, combined after the fact, or tuned against.
