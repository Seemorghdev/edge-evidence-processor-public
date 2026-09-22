# Examples

## Synthetic processor reliability suite

`synthetic_processor.py` is the primary portfolio demonstration. It builds only synthetic evidence,
creates fresh migrated SQLite authorities, and invokes the real processor CLI. No credentials,
network service, model, or private infrastructure is required.

From the repository root:

```bash
make setup
make demo
make inspect
```

The suite runs three persistent scenarios:

| Scenario | What it proves |
| --- | --- |
| `normal` | verified derived report/manifest, artifact identity, lineage, and exact replay without authority changes |
| `resume` | durable `PREPARED` checkpoint survives a forced exit and the same deterministic job resumes to `COMPLETE` |
| `busy-lock` | canonical spool-lock contention returns `deferred` without creating processor authority; retry then completes |

The top-level result is `.demo-output/summary.json`. Each scenario writes a `receipt.json` containing
its input identity, worker summaries, authoritative state observations, derived artifact/manifest
hashes, lineage/contract verification, and scenario-specific invariants.

Useful direct commands are:

```bash
PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root .demo-output demo

PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root .demo-output inspect

PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root .demo-output fingerprint
```

`inspect` is read-only. `fingerprint` hashes deterministic demonstration evidence files and excludes
generated MP4s, SQLite databases, and lock files. The heavy CI lane compares these fingerprints
across two independently generated demo roots.

## Committed container/Cloud Run fixture

`fixtures/cloud_run/` is a smaller frozen fixture used by acceptance tests and the production image.
Its `expected.json` records the exact first-run/replay summaries, deterministic job/artifact
identity, output paths, and SHA-256 values. CI executes the packaged image entry point against this
fixture; it does not deploy to Google Cloud.

The fixture is evidence for the container command contract. It is not a claim that container-local
writable storage is appropriate persistence for independent Cloud Run executions.

## Optional ADK inspection demo

`adk_inspection_demo.py` exercises the optional Google ADK adapter:

```bash
make setup-adk
PYTHONPATH=. uv run --no-sync python examples/adk_inspection_demo.py
```

The adapter can inspect/classify processor state but cannot mutate evidence, advance processing
jobs, change provider/IAM state, deploy infrastructure, or publish evidence authority.
