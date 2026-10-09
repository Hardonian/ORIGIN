# Security Policy

## Scope

ORIGIN is a local-first research platform. It is designed to run on a trusted
workstation; it does not expose a public attack surface by default.

## Design guarantees

* The API binds to `127.0.0.1` by default.
* If bound to an external network interface (e.g. `--host 0.0.0.0`), token authentication
  is automatically enforced: `origin-api` requires `ORIGIN_API_KEY` (or auto-generates a
  cryptographically secure secret token printed to the operator). Requests must provide
  `Authorization: Bearer <token>` or `X-API-Key: <token>`.
* Timing-safe verification (`hmac.compare_digest`) protects against timing side-channels.
* Mutating endpoints (launching experiments, reaping workers) always require valid authentication
  when an API key is configured.
* Organisms are **data-only**. A controller is a plain MLP genome serialized as
  JSON arrays; no externally supplied executable code is ever run.
* Checkpoint/organism restore uses JSON, never `pickle`, so restoring an
  untrusted artifact cannot execute code.
* No secrets are committed. Configuration uses environment variables or local
  files that are git-ignored.
* Simulation can consume CPU heuristically; use `--jobs` to bound concurrency
  and avoid starving other workloads on shared machines.

## Reported guarantees are tested

`tests/test_security.py` asserts these properties against the source tree and is
run in CI. If a guarantee is weakened, CI fails.

## Dependency posture (frontend)

The Next.js runtime advisories previously reported against 14.2.x are **resolved**:
the lab now runs **`next@16.4.0`**, which `npm audit` reports with no Next.js
advisories. The upgrade also required migrating off `next lint` (removed in
Next 16) to the **ESLint 9 flat config** in `apps/lab/eslint.config.mjs`.

Remaining `npm audit` findings:

| Package | Severity | Scope | Status |
|---|---|---|---|
| `braces` (via `eslint-config-next` → `@next/eslint-plugin-next` → `fast-glob` → `micromatch`) | high | **dev-only** (lint toolchain; never shipped in the app bundle) | **unfixable at present** — `braces@3.0.3` is the newest release and the advisory (`GHSA-vfj7-8cjw-p6xm`) covers all versions; `npm audit fix --force` only offers a *downgrade* of `eslint-config-next` |

This is stated rather than suppressed. The finding is a stack-exhaustion DoS in a
parser reached only by linting trusted first-party source, on a loopback, single-user
tool. It is tracked in `IMPLEMENTATION_STATUS.md` and resolves when the Next lint
plugin bumps `micromatch`/`braces`. **We do not claim the frontend dependency tree
is advisory-free.** As checked on 2026-10-09, `npm audit --omit=dev` reports zero
production advisories; the frontend CI job now enforces that same command through
`npm run audit:production`.

Earlier PostCSS advisories were resolved with an `overrides` pin to `postcss >= 8.5.29`.

## Reporting a vulnerability

Open a private security advisory on the GitHub repository, or contact the
maintainer directly. Please do not open a public issue for an exploitable
finding. Include a reproduction and the affected commit.

## Non-goals

ORIGIN does not claim to be hardened for multi-tenant or internet-facing
deployment. Do not deploy it that way without additional work.
