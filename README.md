# edge-evidence-processor-public

A deterministic, single-writer processor for evidence already registered in SQLite and a content-addressed filesystem spool: the public, reviewable processing layer of Edge Evidence.

**Status.** Built: a Python processor, CLI and synthetic reliability demo. Evidence: 53 tests passed and 11 optional ADK tests skipped on Python 3.12.13; CI verifies Python 3.12–3.14. The normal demo passes its normal, resume and busy-lock scenarios. Limits: synthetic evidence only; this is not a capture or replication service, and it does not demonstrate a live cloud deployment.

## Quick-start

Requires Python 3.12+, `uv`, FFmpeg/`ffprobe`, and SQLite. From the repository root:

```bash
make setup
make demo
make inspect
```

The demo reports each scenario as `pass` and writes receipts under `.demo-output/`.

## Tests

`make test`: 53 passed, 11 skipped (the optional ADK tests). CI runs the same suite on Python 3.12–3.14 in [`required.yml`](.github/workflows/required.yml). The latest `main` run passed: [![Required checks](https://github.com/Seemorghdev/edge-evidence-processor-public/actions/workflows/required.yml/badge.svg?branch=main)](https://github.com/Seemorghdev/edge-evidence-processor-public/actions/workflows/required.yml).

## How it fits

This is the processing layer of [Edge Evidence](https://mehridian.tech/projects/edge-evidence). Its [record-level case study](https://mehridian.tech/projects/edge-evidence-record) follows a checkpoint, resume and no-write deferral. Technical docs: [Edge Evidence](https://docs.mehridian.tech/edge-evidence/).

## Licence

Apache-2.0. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.

## Further detail

The [previous repository overview](docs/portfolio-overview.md) is preserved unchanged. See also [Architecture](docs/architecture.md), [Contracts](docs/contracts.md), [Local development](docs/local-development.md), and [Deployment handoff](docs/deployment-handoff.md).
