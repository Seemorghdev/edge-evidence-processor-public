# Architecture

## Product boundary

`edge-evidence-processor` is one standalone application package: `processor`.

```text
packaged CLI / Cloud Run Job args
            |
            v
     processor.worker
            |
            v
     processor.pipeline  --------> content-addressed POSIX spool
            |                       raw + derived bytes/manifests
            v
        SQLite authority
   jobs + artifacts + lineage

processor.inspect / processor.pilot / optional ADK
            |
            +---- read-only observation/classification
```

The important boundary is authority, not deployment topology. SQLite records authoritative state;
the spool records authoritative evidence bytes/manifests. The optional inspection/ADK surface does
not receive write, deployment, IAM, provider, or publication authority.

## Component responsibilities

- `processor.worker` selects eligible evidence deterministically and owns the bounded batch/run
  summary used by the production CLI.
- `processor.pipeline` contains the SQLite/filesystem processing transaction, evidence validation,
  locking, staging, publication, recovery, and lineage/finalization primitives.
- `processor.processing` contains the pure fingerprint derivation and deterministic job/parameter
  identity logic.
- `processor.database` owns schema and migration behavior.
- `processor.contracts` contains framework-neutral observations, classifications, proposals,
  receipts, policy records, canonical encoding, and compatibility contracts.
- `processor.inspect`, `processor.pilot`, and `processor.agent` expose bounded inspection surfaces;
  the ADK integration is optional and lazily imported.

## Authority model

The current standalone worker expects a canonical migrated SQLite authority and a writable POSIX
spool containing the immutable raw media/manifests referenced by that authority.

SQLite is authoritative for:

- artifact metadata and digest bindings;
- processing job identity/state;
- derived artifact registration;
- one-parent lineage;
- migration history and compatibility records.

The spool is authoritative for:

- content-addressed raw media and manifests;
- staged and published derived reports/manifests;
- the canonical advisory lock used to serialize spool publication.

Raw evidence is never replaced. The spool root must nevertheless be writable because processing
adds derived content and uses staging/locking metadata.

## Processing transaction

At snapshot time, an eligible raw artifact with no matching processing job is projected as
`MISSING`; `MISSING` is not a persisted job row. Job identity is derived deterministically from the
input and the processor/version/output-contract/parameter identity.

The effectful processing path is intentionally split around a durable checkpoint:

1. Verify that SQLite, the raw artifact id/digest, the raw file, manifest, and media evidence agree.
2. Derive the canonical parameters and deterministic processing job id.
3. If an exact prior `COMPLETE` job exists, verify its authority and adopt it without rewriting.
4. Otherwise create or recover the exact `PREPARED` job and commit that checkpoint.
5. Produce the deterministic metadata report, stage it, and publish report/manifest with
   no-replace filesystem semantics.
6. In the final database transaction, register the derived metadata artifact, record
   `derived_from` lineage, and transition the same job to `COMPLETE`.
7. On exact retry, verify/adopt the `COMPLETE` result. On restart from `PREPARED`, resume the same
   deterministic job rather than creating a replacement.

Existing final paths are not blindly overwritten. Exact compatible work can be verified and
adopted; contradictory identity or incompatible no-replace collisions fail closed.

## Concurrency and recovery

The processor uses the shared POSIX advisory spool lock with a bounded acquisition timeout. The
worker treats exact lock contention as deferrable work rather than a partial processing attempt.
The synthetic busy-lock demonstration asserts that this path creates no processing job and leaves
authoritative database state unchanged.

The pipeline exposes test crash barriers around the durable phases (including after `PREPARED`,
during/after staged writes, after publication, before the final commit, and after `COMPLETE`). Those
barriers exist to prove recovery semantics; they are no-ops in normal production execution.

The portfolio demo forces interruption immediately after the `PREPARED` commit. It then verifies
that no derived artifact/lineage has been committed, resumes the same job id to `COMPLETE`, and
proves an additional replay is idempotent.

## Worker selection boundary

The worker processes completed raw-media authority that meets its snapshot constraints. Current
selection intentionally excludes ambiguous multi-assertion artifacts instead of inventing authority
for them. Snapshot order is deterministic, and a persisted job whose identity contradicts the
expected deterministic job id fails closed.

These behaviors are tested in `tests/unit/test_processor_worker.py` and exercised end to end by the
synthetic/committed fixtures.

## Cloud/runtime boundary

The Docker image exposes the packaged CLI as its entry point. Terraform declares one
`google_cloud_run_v2_job` and supplies the real worker arguments:

```text
run --database ABSOLUTE_SQLITE_PATH --spool-root ABSOLUTE_SPOOL_PATH
```

The job is fixed to one task and parallelism one, matching the single-writer SQLite/POSIX model.
Terraform requires an immutable image digest and an existing service-account identity. It does not
create IAM, enable APIs, create storage/database resources, stage evidence, configure a backend,
grant public access, or perform an apply.

The repository therefore demonstrates a deployable job contract, not a complete cloud platform.
For real execution, an operator must make the existing authority database and writable spool
available at the configured in-container paths. The committed image fixture is a smoke/contract
fixture, not a persistence design for independent Cloud Run executions.

See `deployment-handoff.md` for the separate executor boundary.

## Optional AI boundary

Google ADK is an explicit optional package extra. Ordinary processor imports do not load it. The
adapter wraps read-only processor inspection/classification and is deliberately denied evidence,
provider, IAM, deployment, and publication mutations. AI output is never a substitute for SQLite or
spool evidence and cannot silently advance `PREPARED`/`COMPLETE` state.

## Compatibility and replication boundary

The schema and contract package retain provider-neutral replication compatibility records because
they are part of the authority lineage inherited by this processor. That does not make this
repository a replication service: no replication executor or provider-control runtime is present.
The processor can participate in a larger reference platform through compatible authority data
without depending on that platform to run locally.

Historical behavior-preserving port records live under `docs/history/` and are explicitly not the
current architecture.

## Provenance identity

Git commits identify repository source provenance; immutable container image digests identify a
built deployment artifact. Public-safe compatibility records may intentionally use redacted source
identity sentinels. Neither provenance label changes evidence authority or processor state.
