# Actor-Critic PPO v1 configuration audit

**Status: exploratory implementation result only — not confirmatory and not
citable as a test of H-AC.**

This audit was written before any Actor-Critic v2 trial was started. It preserves
the original v1 registration and configuration files as historical artifacts;
it does not alter them to make the completed run appear compliant.

## Stored run

| Field | Value |
| --- | --- |
| Grid experiment | `98732cc5cdb2` |
| Stored configuration hash | `e2d92757fcec` |
| Completed trials | 32/32, 0 failed |
| Source configuration | `configs/actor_critic_grid_v1.json` |
| Claimed protocol | `research/protocols/actor_critic_v1.md` |

The stored grid data may be used to inspect the PPO implementation, diagnose
runtime, or plan a future registered study. It must not be presented as a
confirmatory PPO-versus-REINFORCE result.

## Registration mismatch

The v1 protocol describes a 500,000-training-step grid study and a
300,000-training-step embodied study using an 8-link, 8-second crawler with
four train and four held-out test seeds. The versioned configuration files do
not implement those specifications:

| Property | v1 protocol | v1 grid config | v1 embodied config |
| --- | --- | --- | --- |
| Training cap | 500,000 grid; 300,000 embodied | 50,000 | 20,000 |
| Embodied body | 8-link worm | — | 6-link worm |
| Embodied horizon | 8.0 s | — | 6.0 s |
| Embodied train/test seeds | four / four | — | three / three |

Because the v1 grid campaign ran with the 50,000-step configuration, changing
the protocol or configuration in place would be a retrospective registration
rewrite. The original files are therefore retained unchanged and the campaign
is classified as exploratory.

## Corrective action

`research/protocols/actor_critic_v2.md`,
`configs/actor_critic_grid_v2.json`, and
`configs/actor_critic_embodied_v2.json` are the replacement registration. They
fix the complete task, body, budgets, random seeds, algorithms, endpoint, and
analysis rule before execution. `scripts/analyze_actor_critic.py` rejects v1
as a confirmatory input and validates a v2 stored configuration against the
registration file supplied on the command line.
