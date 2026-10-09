# Protocol — Actor-Critic (PPO) Baseline: Cross-Domain Reinforcement Learning Benchmark v1

**Registered before execution.** This protocol pre-registers the evaluation of
the pure-NumPy Proximal Policy Optimization (PPO) Actor-Critic baseline
across both the discrete gridworld and continuous articulated rigid-body
(PyBullet) locomotion domains in ORIGIN.

---

## 1. Hypotheses and Scope

### H-AC.1 (Sample Efficiency & Value Estimation on Gridworld)
Under a strict, fixed training-interaction budget (500,000 steps) on the
registered single-niche grid task, the PPO Actor-Critic baseline with
Generalized Advantage Estimation (GAE) achieves higher held-out base-task reward
than the non-critic REINFORCE control:

$$\Delta_{\text{grid}} = \bar{R}_{\text{PPO}} - \bar{R}_{\text{REINFORCE}} > 0$$

### H-AC.2 (Embodied Locomotion Competence)
Under a strict training-interaction budget (300,000 steps) on the PyBullet
embodied ground crawler task (`worm`, 8 revolute links), PPO discovers a
locomotion gait achieving forward displacement and reward strictly exceeding
the random control baseline while remaining upright:

$$\Delta_{\text{embodied}} = \bar{R}_{\text{PPO}} - \bar{R}_{\text{random}} > 0$$

---

## 2. Fixed Environments and Algorithm Specifications

### 2.1 Gridworld Task
- **Arena:** 10×10 egocentric random-terrain environment.
- **Seeds:** Training seeds `[11, 22, 33, 44]`, held-out test seeds `[101, 202, 303, 404]`.
- **Budget:** 500,000 training interactions per seed.

### 2.2 Embodied Physics Task
- **Simulator:** PyBullet DIRECT mode (Milestone 4).
- **Body Plan:** `worm` preset (8 revolute links, $L = 0.16\text{ m}$, $r = 0.035\text{ m}$, mass $0.25\text{ kg}$, yaw joints, anisotropic friction $\mu_{\text{lat}} = 1.25, \mu_{\text{long}} = 0.20$).
- **Control Horizon:** 8.0 s (240 control steps at $\Delta t = 1/30\text{ s}$).
- **Seeds:** Training seeds `[11, 22, 33, 44]`, held-out test seeds `[101, 202, 303, 404]`.
- **Budget:** 300,000 training interactions per seed.

### 2.3 Network Architecture & Hyperparameters
- **Actor Network:** MLP with dimensions $[D_{\text{obs}}, 24, N_{\text{actions}}]$, $\tanh$ hidden activations, softmax categorical action head, Adam optimizer ($\text{lr} = 0.008$).
- **Critic Network:** MLP with dimensions $[D_{\text{obs}}, 24, 1]$, $\tanh$ hidden activations, linear scalar head, Adam optimizer ($\text{lr} = 0.012$).
- **RL Hyperparameters:**
  - Discount $\gamma = 0.99$
  - GAE parameter $\lambda = 0.95$
  - Clipping threshold $\epsilon = 0.20$
  - Optimization epochs per rollout batch $K = 4$
  - Episodes per update batch $M = 4$
  - Entropy regularization coefficient $c_e = 0.015$

---

## 3. Interaction Currency & Accounting

1. Every policy rollout interaction is billed to the trial's interaction budget (`evaluator.interactions`).
2. Rollouts that cannot fit within the remaining interaction budget truncate the final batch gracefully rather than exceeding the budget cap.
3. Held-out test evaluation steps are recorded separately under `evaluation_interactions` to ensure training compute comparability.

---

## 4. Registered Statistical Decision Rules

For each paired method seed $s$:

$$d_s = R_{\text{PPO}}(s) - R_{\text{baseline}}(s)$$

1. **Bootstrap Decision Rule:** Compute a 10,000-resample percentile bootstrap 95% confidence interval using seed `20261018`.
2. **Concordance Check:** Two-sided Wilcoxon signed-rank test.
3. **Inference Criteria:**
   - **Supported:** Point estimate $\hat{d} > 0$ and 95% bootstrap CI strictly excludes zero.
   - **Falsified:** Point estimate $\hat{d} < 0$ and 95% bootstrap CI strictly excludes zero.
   - **Inconclusive:** 95% bootstrap CI contains zero.
