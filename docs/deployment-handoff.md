# Local executor deployment handoff

This is a non-cloud handoff. Only the local executor may authenticate to Google Cloud, push an
image, apply or destroy Terraform, execute the job, or read cloud logs. Build from the exact
`main` SHA supplied with the handoff record and preserve that SHA with the image digest.

## Production command contract

The image declares this entry point:

```text
edge-evidence-processor
```

Terraform supplies the real worker arguments, so the complete process is:

```text
edge-evidence-processor run --database ABSOLUTE_SQLITE_PATH --spool-root ABSOLUTE_SPOOL_PATH
```

There are no required environment variables. Before the process starts:

- the database path must name an existing canonical schema-v10 SQLite authority file;
- the spool root must be an existing writable directory;
- the database and spool must be on a writable POSIX filesystem available for the whole task;
- the spool must already contain the immutable raw media and manifest paths referenced by SQLite.

The Terraform job is fixed to one task and parallelism one. It creates no IAM, API enablement,
backend, public access, storage, database, or input staging resources.

## Deterministic fixture

The image contains one committed fixture prepared during `docker build`:

```text
/opt/edge-evidence-processor/fixture/authority.sqlite3
/opt/edge-evidence-processor/fixture/spool
/opt/edge-evidence-processor/fixture/expected.json
```

Its exact command arguments are:

```text
run --database /opt/edge-evidence-processor/fixture/authority.sqlite3 --spool-root /opt/edge-evidence-processor/fixture/spool
```

`fixtures/cloud_run/expected.json` records the exact summaries, artifact paths, job id and SHA-256
values. A Cloud Run execution starts from the pristine image fixture and therefore exercises the
first-run expectation. Replay, resume and busy-lock are proven locally and in CI against the same
committed fixture; separate Cloud Run executions do not share the container writable layer.

## Build and local image proof

```bash
SOURCE_SHA="$(git rev-parse HEAD)"
docker build --pull --no-cache \
  -t "edge-evidence-processor:${SOURCE_SHA}" .

docker inspect "edge-evidence-processor:${SOURCE_SHA}" \
  --format '{{json .Config.Entrypoint}} {{json .Config.Cmd}}'

cid="$(docker create "edge-evidence-processor:${SOURCE_SHA}" \
  run \
  --database /opt/edge-evidence-processor/fixture/authority.sqlite3 \
  --spool-root /opt/edge-evidence-processor/fixture/spool)"
trap 'docker rm -f "$cid" >/dev/null 2>&1 || true' EXIT

docker start -a "$cid"          # exact first-run JSON summary
docker start -a "$cid"          # exact replay JSON summary on the same writable layer
docker cp "$cid":/opt/edge-evidence-processor/fixture/expected.json /tmp/processor-expected.json
```

## Terraform inputs

Required variables:

```text
project_id
region
image                    # must end in @sha256:<64 lowercase hex>
service_account_email    # an existing identity; this module creates no IAM
database_path            # absolute in-container path
spool_root               # absolute in-container path
```

Optional bounded settings are `job_name`, `cpu`, `memory`, `timeout_seconds`, and `max_retries`.
For the committed smoke fixture use the two `/opt/edge-evidence-processor/fixture/...` paths above.
For a real execution, the local executor must provide an image or POSIX volume containing the
existing authority database and spool at the paths passed to Terraform.

Credential-free checks:

```bash
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
terraform -chdir=terraform test -verbose
```

The executor's authenticated plan/apply uses an immutable pushed image digest:

```bash
terraform -chdir=terraform plan \
  -var="project_id=${PROJECT_ID}" \
  -var="region=${REGION}" \
  -var="image=${IMAGE_BY_DIGEST}" \
  -var="service_account_email=${SERVICE_ACCOUNT_EMAIL}" \
  -var="database_path=/opt/edge-evidence-processor/fixture/authority.sqlite3" \
  -var="spool_root=/opt/edge-evidence-processor/fixture/spool"

terraform -chdir=terraform apply
```

## Execute and collect evidence

```bash
gcloud run jobs describe "${JOB_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" --format=json

gcloud run jobs execute "${JOB_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" --wait

gcloud run jobs executions list \
  --job "${JOB_NAME}" --project "${PROJECT_ID}" --region "${REGION}"

gcloud run jobs executions describe "${EXECUTION_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" --format=json

gcloud run jobs logs read "${JOB_NAME}" \
  --project "${PROJECT_ID}" --region "${REGION}" \
  --freshness=1h --order=asc --format=json
```

Success evidence is a successful one-task execution and one stdout JSON object exactly matching
`first_run.summary` in `expected.json`. The fixture-derived report and manifest digests are also
listed there and are verified by local/container CI before handoff.

## Cleanup

For a disposable job created from this module, use the same Terraform working directory and state:

```bash
terraform -chdir=terraform destroy
```

Do not delete or mutate any external authority database, spool, service account, API configuration,
registry repository, or image unless those were separately created and explicitly owned by the
local executor.
