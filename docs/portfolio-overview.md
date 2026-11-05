# Edge Evidence Processor

A deterministic, single-writer processor for evidence that is already registered in a SQLite authority and a content-addressed filesystem spool. It verifies completed raw video, derives an `artifact-fingerprint-report.v1` metadata artifact, records one-parent lineage, and makes retry/resume behavior explicit without mutating raw evidence.

> Public projection: Generated from a reviewed private canonical source. This repository is a recruiter-facing product projection, not a mirror of private development history and not an authority cutover.

## What problem it solves

Evidence processing is easy to make operationally ambiguous: retries can duplicate work, crashes can leave unclear state, competing workers can race publication, and inspection layers can accidentally become sources of authority. This processor keeps those concerns local, deterministic, and inspectable:

- SQLite records processing jobs, artifact metadata, lineage, and migration history.
- The spool stores content-addressed raw and derived bytes plus manifests.
- Job identity and derived-output identity are deterministic.
- A committed `PREPARED` job is a resumable checkpoint; `COMPLETE` is terminal processing state.
- Exact retries verify and adopt complete work rather than rewriting it.
- A busy canonical spool lock defers work without creating processor authority.
- Identity contradictions and no-replace publication collisions fail closed.
- Optional AI/ADK code can inspect and classify; it cannot execute processor state transitions.

## Authority and state model

SQLite and the filesystem spool are the evidence authority for this product. Raw evidence paths are immutable/no-replace; the spool root must be writable so derived artifacts can be appended. Terraform and the optional ADK adapter are not evidence authority.

```text
no processing job (MISSING projection)
        |
        | deterministic job identity
        v
     PREPARED  ---- exact resume ----+
        |                             |
        | verified no-replace output |
        | + manifest publication      |
        | + metadata/lineage commit   |
        v                             |
     COMPLETE <-----------------------+
        |
        +---- exact retry: verify/adopt; no rewrite
```

`MISSING` is a worker projection when no job row exists, not a persisted job state. The synthetic resume scenario stops immediately after the durable `PREPARED` commit, then proves that the same deterministic job is completed on the next run. The busy-lock scenario proves that a blocked attempt leaves the authoritative database unchanged.

See [Architecture](docs/architecture.md) for transaction, locking, and concurrency boundaries.

## 60-second review

Prerequisites: Python 3.12+, `uv`, FFmpeg/`ffprobe`, and SQLite.

```bash
make setup
make demo
make inspect
make test
```

The deterministic demo writes evidence under `.demo-output/`:

```text
.demo-output/summary.json
.demo-output/normal/receipt.json
.demo-output/resume/receipt.json
.demo-output/busy-lock/receipt.json
```

Each receipt records worker summaries, authoritative state observations, derived report/manifest hashes, lineage checks, and scenario-specific invariants.

## Deterministic scenarios

| Scenario | Demonstrated behavior |
| --- | --- |
| `normal` | one new derived artifact, verified content identity and lineage, then an idempotent replay |
| `resume` | forced interruption after durable `PREPARED`, same-job resume, then replay |
| `busy-lock` | canonical spool lock contention returns `deferred` with zero authoritative database writes, then retry succeeds |

The demo also exposes a deterministic `fingerprint` command. CI runs independent demo roots and requires their fingerprints to match.

## Evidence map

| Guarantee | Primary evidence |
| --- | --- |
| deterministic job/retry behavior | `tests/unit/test_processor_worker.py`, synthetic `normal` receipt |
| durable `PREPARED` recovery | `tests/unit/test_processor_worker.py`, synthetic `resume` receipt |
| busy-lock deferral performs no authority write | worker tests, deployment-contract test, synthetic `busy-lock` receipt |
| output bytes, manifest hash, artifact identity, and one-parent lineage are verified | deterministic demo and committed Cloud Run fixture |
| identity conflicts fail closed and CLI errors are sanitized | `tests/unit/test_processor_worker.py` |
| only the `processor*` application package is installed | architecture tests and package build checks |
| ordinary imports do not load Google ADK | architecture test |
| container entry point executes the packaged CLI | `Dockerfile` and deployment-contract tests |
| Terraform defines one bounded Cloud Run Job without IAM/API/backend/public-access resources | `terraform/` and architecture tests |

## CLI surface

```bash
edge-evidence-processor --help
processor-worker --help
processor-inspect --help
```

Production worker contract:

```text
edge-evidence-processor run --database ABSOLUTE_SQLITE_PATH --spool-root ABSOLUTE_SPOOL_PATH
```

The database and spool are explicit inputs; no cloud API or AI layer silently supplies authority.

## Runtime and cloud boundary

This repository contains three concrete runtime/deployment surfaces:

1. the packaged Python CLI;
2. a Docker image whose entry point is `edge-evidence-processor`;
3. Terraform for one `google_cloud_run_v2_job`, fixed to one task and parallelism one.

Terraform requires caller-supplied project/region values, an immutable image reference by digest, an existing service account, and absolute in-container database/spool paths. It does **not** create IAM, enable APIs, configure a backend, create storage/database resources, grant public access, authenticate, apply itself, or deploy anything.

The committed fixture proves the image/worker command contract locally and in CI. This projection does not claim that a live Google Cloud deployment has been performed or that ephemeral Cloud Run storage is a persistence design for real evidence. See [Deployment handoff](docs/deployment-handoff.md).

## Optional ADK boundary

Google ADK is an explicit optional dependency, not part of the default environment. The adapter is lazily imported and bounded to observation/classification. It cannot mutate raw evidence, advance processor jobs, change IAM/provider state, deploy infrastructure, or publish results as evidence authority.

```bash
make setup-adk
PYTHONPATH=. uv run --no-sync python examples/adk_inspection_demo.py
```

## Documentation

- [Architecture](docs/architecture.md)
- [Contracts](docs/contracts.md)
- [Local development](docs/local-development.md)
- [Deployment handoff](docs/deployment-handoff.md)
- [Deterministic examples](examples/README.md)
- [Projection provenance](docs/PROJECTION-PROVENANCE.md)
- [Security policy](SECURITY.md)

## Repository map

```text
processor/                 application code, contracts, pipeline, inspection and optional adapter
tests/                     unit, integration, contract, architecture and acceptance evidence
examples/                  deterministic synthetic reliability suite and optional ADK demo
fixtures/cloud_run/        frozen credential-free image/worker fixture and exact expectations
docs/                      current architecture, contracts, local development and deployment handoff
terraform/                 one bounded Cloud Run Job definition and credential-free tests
.devcontainer/             reproducible development toolchain
Dockerfile                 production CLI image plus committed smoke fixture
Makefile                   local validation/demo commands
pyproject.toml / uv.lock   package metadata and dependency lock
LICENSE / THIRD_PARTY_*    licensing and public third-party notices
```

## Limitations and non-goals

- The authority model is deliberately SQLite + POSIX filesystem and single-writer oriented; this is not a distributed database or queue.
- The worker expects existing, correctly migrated authority data and referenced raw evidence; it is not a capture/ingest service.
- Real cloud persistence, storage mounting, IAM, image publication, deployment, and operations remain operator/platform responsibilities.
- The included portfolio demo is synthetic and credential-free. It demonstrates processor semantics, not production camera data or a live-cloud benchmark.
- Replication execution is out of scope even though compatibility contracts/schema history remain.
- Optional ADK is an inspection convenience, never evidence authority.
- This public projection does not carry private source history, private review metadata, internal validation branches, or authority cutover semantics.
