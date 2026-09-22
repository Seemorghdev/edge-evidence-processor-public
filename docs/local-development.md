# Local development

## Toolchain

The included devcontainer is the shortest reproducible setup. It includes Python 3.12, `uv`,
FFmpeg/FFprobe, SQLite CLI, `make`, Git, and Terraform 1.16.0.

For a host-native setup, install:

- Python 3.12 or newer;
- `uv`;
- `make`;
- FFmpeg (`ffmpeg` and `ffprobe`).

The SQLite CLI is optional for the processor itself but useful for manual authority inspection.
Terraform is needed only for `make terraform-check`.

## Setup and core checks

```bash
make setup
make test
make compile
```

`make setup` uses the committed `uv.lock` for the default package environment and then installs the
small development requirement set. Google ADK is not installed by default.

## Deterministic processor demo

```bash
make demo
make inspect
```

`make demo` removes the previous `.demo-output` directory, generates synthetic H.264 input, creates
fresh migrated SQLite authorities, and invokes the real processor CLI for three scenarios:

- `normal`: new processing followed by exact replay;
- `resume`: forced process exit immediately after the durable `PREPARED` commit, followed by resume;
- `busy-lock`: exclusive spool-lock contention, zero-write deferral, retry, and replay.

The command is credential-free and requires no network service, model, cloud resource, or private
infrastructure. Persistent evidence is written to:

```text
.demo-output/summary.json
.demo-output/summary.txt
.demo-output/normal/receipt.json
.demo-output/resume/receipt.json
.demo-output/busy-lock/receipt.json
```

Each scenario directory also contains its SQLite authority, spool, generated input, human summary,
and verified derived report/manifest paths. `make inspect` reads those artifacts and prints the
result/tree; it does not process new evidence.

## Reproduce the deterministic evidence comparison

The heavy CI lane runs two independent demo roots and compares the deterministic evidence
fingerprints. The same check can be run locally:

```bash
rm -rf /tmp/processor-demo-a /tmp/processor-demo-b

PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root /tmp/processor-demo-a demo
PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root /tmp/processor-demo-a fingerprint > /tmp/processor-fingerprint-a.json

PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root /tmp/processor-demo-b demo
PYTHONPATH=. uv run --no-sync python examples/synthetic_processor.py \
  --output-root /tmp/processor-demo-b fingerprint > /tmp/processor-fingerprint-b.json

cmp /tmp/processor-fingerprint-a.json /tmp/processor-fingerprint-b.json
```

The fingerprint intentionally excludes generated MP4 files, SQLite database files, and lock files.
It proves stable processor receipts/results and derived evidence hashes, not portability of raw
FFmpeg/SQLite file bytes across every toolchain build.

## Package and container checks

```bash
make build
make docker-build

docker run --rm edge-evidence-processor:local --help
```

The Docker image includes a committed smoke fixture at `/opt/edge-evidence-processor/fixture` and
uses `edge-evidence-processor` as its entry point. The heavy CI lane executes the real worker against
that fixture twice and checks the exact first-run/replay summaries and committed report/manifest
SHA-256 values.

## Terraform checks

```bash
make terraform-check
```

This runs formatting, backend-disabled initialization, validation, and Terraform tests. It is a
credential-free source/configuration check; it does not apply infrastructure. The heavy CI lane also
performs a `-refresh=false` plan with dummy/offline credentials and an immutable example image
digest.

See `deployment-handoff.md` before treating the Terraform as an execution handoff. Real execution
still requires an existing service account plus an existing SQLite authority and writable POSIX
spool made available to the container.

## Optional ADK inspection

Install the optional dependency only when testing the bounded adapter:

```bash
make setup-adk
PYTHONPATH=. uv run --no-sync python examples/adk_inspection_demo.py
```

The adapter is read-only with respect to processor/provider authority. The default test/package path
must continue to work without `google-adk` installed.

## Cleanup

```bash
make clean
```

This removes local virtualenv, pytest/cache output, demo evidence, and package build artifacts. It
does not touch any external evidence or cloud resource.
