# Security Policy

## Scope

ORIGIN is a local-first research platform. It is designed to run on a trusted
workstation; it does not expose a public attack surface by default.

## Design guarantees

* The read API binds to `127.0.0.1` by default. It must not be exposed to an
  untrusted network without an explicit reverse proxy and authentication.
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

## Known dependency advisories (frontend)

`npm audit` reports 4 advisories against `next@14.2.35` (the latest 14.2.x patch
release). They are documented here rather than suppressed:

| Advisory | Affected feature | Applicable to ORIGIN? |
|---|---|---|
| SSRF in `rewrites` via attacker-controlled destination | `next.config` rewrites | **No** — no rewrites configured |
| Unauthenticated disclosure of internal Server Function endpoints | React Server Actions | **No** — no server actions used |
| Unauthenticated RCE on Windows-hosted servers | Windows deployments | **No** — Linux/WSL host |
| Unauthenticated RCE in Image Optimization API (AVIF) | `next/image` optimizer | **No** — no `next/image`; the UI uses plain `<img>` |

Resolving them requires `next@16`, a breaking change that also removes `next lint`
and pulls React 19. That upgrade is tracked as remaining work (see
`IMPLEMENTATION_STATUS.md`). The lab UI is loopback-only and single-user, which
further bounds exposure. **We do not claim the frontend dependency tree is
advisory-free.**

PostCSS advisories previously present were resolved via an `overrides` pin to
`postcss >= 8.5.29`.

## Reporting a vulnerability

Open a private security advisory on the GitHub repository, or contact the
maintainer directly. Please do not open a public issue for an exploitable
finding. Include a reproduction and the affected commit.

## Non-goals

ORIGIN does not claim to be hardened for multi-tenant or internet-facing
deployment. Do not deploy it that way without additional work.
