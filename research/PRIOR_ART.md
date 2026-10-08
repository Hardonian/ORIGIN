# Prior Art

ORIGIN stands on established work. None of the following is claimed as novel here;
ORIGIN's contribution is *integration into a reproducible, falsifiable pipeline*,
not the invention of the techniques.

## Open-ended / novelty

* Lehman, J. & Stanley, K. O. (2011). *Abandoning Objectives: Evolution through
  the Search for Novelty Alone.* Evolutionary Computation.
* Lehman & Stanley (2008). *Exploiting Open-Endedness to Solve Problems Through
  the Search for Novelty.* ALIFE.

## Quality-diversity

* Mouret, J.-B. & Clune, J. (2015). *Illuminating Search Spaces by Mapping
  Elites.* arXiv:1504.04909.
* Cully, A., Clune, J., Tarapore, D. & Mouret, J.-B. (2015). *Robots that can
  adapt like animals.* Nature.
* Cully, A. & Demiris, Y. (2017). *Quality and Diversity Optimization: A
  Unifying Modular Framework.* IEEE TEC.

## Evolutionary robotics & morphology

* Sims, K. (1994). *Evolving Virtual Creatures.* SIGGRAPH.
* Bongard, J. (2011). *Morphological change in machines accelerates the evolution
  of robust behavior.* PNAS.
* Cheney, N., MacCurdy, R., Clune, J. & Lipson, H. (2013). *Unshackling
  evolution: evolving soft robots with multiple materials and a powerful
  generative encoding.* GECCO.

## Reinforcement learning

* Williams, R. J. (1992). *Simple statistical gradient-following algorithms for
  connectionist reinforcement learning.* Machine Learning. (REINFORCE)
* Sutton & Barto (2018). *Reinforcement Learning: An Introduction.*
* Schulman et al. (2017). *Proximal Policy Optimization Algorithms.*
* Raffin et al. (2021). *Stable-Baselines3: Reliable RL Implementations.*

## Frameworks / infrastructure

* Towers et al. (2023). *Gymnasium: A Standard Interface for Reinforcement
  Learning Environments.*
* PyBullet / MuJoCo for articulated physics (candidate for M4 embodiment).
* PettingZoo / EvoJAX / QDax for multi-agent, GPU-accelerated evolution and QD.

## ORIGIN's contribution

1. A **deterministic, replayable, seed-audited** environment/algorithm/evaluation
   stack in which every metric is traceable to stored artifacts.
2. A **fixed-interface / variable-morphology** design that makes cross-morphology
   transfer measurable without shape errors.
3. An **equal-interaction-budget** comparison harness spanning random, scripted,
   evolutionary, quality-diversity and RL baselines.
4. Explicit handling of **failure, cancellation, resume and reporting honesty**.
