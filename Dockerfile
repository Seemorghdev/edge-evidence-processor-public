FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg sqlite3 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE THIRD_PARTY_NOTICES.md ./
COPY processor ./processor
COPY fixtures/cloud_run ./fixtures/cloud_run

RUN python -m pip install --no-cache-dir . \
    && python fixtures/cloud_run/prepare.py \
        --output-root /opt/edge-evidence-processor/fixture \
    && rm -rf fixtures

ENTRYPOINT ["edge-evidence-processor"]
