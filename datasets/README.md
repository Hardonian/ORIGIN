# Datasets

ORIGIN generates all data procedurally from seeds; there are no copyrighted or
personal datasets in this repository.

* `fixtures/` — small, deliberate, committable fixtures used by tests.
* Everything else under `datasets/` is **git-ignored**. Large generated
  experiment data lives in `runs/` (also git-ignored).

To regenerate the pilot data:

```bash
.venv/bin/origin-run --config configs/pilot.json --store runs --jobs 6
```
