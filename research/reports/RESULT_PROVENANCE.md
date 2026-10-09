# ORIGIN Result Provenance Register

> Updated 2026-10-09. This register is the authority for what may be cited as
> current research evidence. A stored trial or generated report is not, by
> itself, a current result.

| Evidence | Status | Permitted use | Restriction / successor |
| --- | --- | --- | --- |
| H1.MN strict-cap replication v3 (`1e8559d6de45`) | **Confirmatory** | Cite the registered paired endpoint: MAP-Elites minus GA on held-out adapted transfer across the five shocks. | `research/reports/H1_multi_niche_v3_analysis.md` is authoritative. Every learned trial is within the 25,000-step training cap. |
| H1.MN replication v2 (`5058bcacd3de`) | **Invalidated** | Debugging and accounting audit only. | Its optimizers exceeded the registered cap. Never cite its effect estimate or generated research report; use v3. |
| H1.MN multi-niche pilot (`f8f4c952a5c3`) | **Exploratory / archival** | Describe as an early instrument check only. | It predates strict batch reservation and a uniquely fixed ecological-shock aggregation. It cannot decide H1.MN; use v3. |
| Single-niche studies (pilot, powered, paired v2, paired v3) | **Legacy descriptive** | Historical behavioral observations, with their original limitations stated. | Do not cite their interaction/compute totals as strict-cap evidence. Fresh raw stores are not present locally, so a strict-cap rerun is needed for a current compute claim. |
| Embodied transfer v2 | **Retracted** | None as empirical evidence. | The physical instrument failed calibration; see `research/reports/ORIGIN_M4_Embodied_Transfer_Report.md`. A supported-PyBullet acceptance probe and fresh pre-registered campaign are required. |
| Deterministic smoke fixture | **Fixture** | Test/reproducibility checks only. | Never use as research evidence. |

## Generation policy

`scripts/make_report.py` refuses to generate a normal report for any protocol
listed above as invalidated, exploratory/archival, legacy, retracted, or a
fixture. An auditor may pass `--allow-legacy`; that output receives an explicit
archival warning and remains non-citable as current evidence. The strict-cap
v3 protocol remains reportable without an override.

## Citation rule

For H1.MN, cite the registered v3 analysis rather than a generic generated
report. Do not combine shocks as independent observations: a method seed is the
unit of inference. For any historical result not enumerated above, first check
the protocol, cap semantics, raw-store availability, and analysis registration
before treating it as evidence.
