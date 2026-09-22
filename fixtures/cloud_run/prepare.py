"""Prepare the committed Cloud Run processor fixture without cloud access."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sqlite3
import zlib
from pathlib import Path

from processor.database.migrations import migrate
from processor.pipeline import finalize
from processor.processing import fingerprint

MEDIA_SHA256 = "0a898208211b062c4c89e2cf34ddaee9ec7f324d5848391ca2f4183ca6116013"
MEDIA_BYTE_SIZE = 11061
RAW_MANIFEST_SHA256 = "038dd05129808ed594fc7dda65dc7de68190d117e57b2adfc6a49b2f38d1b884"
JOB_ID = "c9eb642c-10dd-558f-8897-90ac750fc126"
REPORT_SHA256 = "16ec8a76c1383a4a883bd07c4caea8ba22c79eff74ae87e03349c509fffca8f1"
REPORT_MANIFEST_SHA256 = "3f369344fdfec34a857c1ebf5465d5e982ea0f37eb922d7f4c13b0f8ace560c2"
SOURCE_ID = "cloud-run-fixture"
OCCURRENCE_ID = "occ-cloud-run-fixture"
SESSION_ID = "sess-cloud-run-fixture"
STARTED_AT = "2026-08-11T10:00:00Z"
FINALIZED_AT = "2026-08-11T10:00:10Z"


def _fixture_media_bytes() -> bytes:
    encoded_path = Path(__file__).with_name("input.mp4.zlib.b64")
    try:
        compressed = base64.b64decode(
            encoded_path.read_text(encoding="ascii").strip(),
            validate=True,
        )
        media_bytes = zlib.decompress(compressed)
    except (OSError, ValueError, zlib.error) as exc:
        raise RuntimeError("fixture media payload is invalid") from exc
    if (
        len(media_bytes) != MEDIA_BYTE_SIZE
        or hashlib.sha256(media_bytes).hexdigest() != MEDIA_SHA256
    ):
        raise RuntimeError("committed fixture media does not match the frozen digest")
    return media_bytes


def prepare_fixture(output_root: Path, scenario: str = "normal") -> None:
    if scenario not in {"normal", "resume"}:
        raise ValueError("scenario must be 'normal' or 'resume'")
    media_bytes = _fixture_media_bytes()

    output_root = output_root.resolve()
    if output_root == Path(output_root.anchor):
        raise RuntimeError("refusing to replace the filesystem root")
    shutil.rmtree(output_root, ignore_errors=True)
    spool = output_root / "spool"
    database = output_root / "authority.sqlite3"
    spool.mkdir(parents=True)

    migration = migrate(database)
    if migration.current_version != 10:
        raise RuntimeError("fixture authority did not reach schema version 10")

    artifact_id = f"sha256:{MEDIA_SHA256}"
    media_path = spool / finalize.media_relative_path(MEDIA_SHA256)
    manifest_path = spool / finalize.manifest_relative_path(MEDIA_SHA256)
    media_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    media_path.write_bytes(media_bytes)

    manifest = {
        "schema_version": 1,
        "artifact_id": artifact_id,
        "source_id": SOURCE_ID,
        "artifact_kind": "raw_media",
        "media_type": "video/mp4",
        "byte_size": MEDIA_BYTE_SIZE,
        "digest": {"algorithm": "sha256", "value": MEDIA_SHA256},
        "storage_uri": finalize.storage_uri(MEDIA_SHA256),
        "finalized_at": FINALIZED_AT,
    }
    manifest_bytes = finalize.serialize_manifest(manifest)
    if hashlib.sha256(manifest_bytes).hexdigest() != RAW_MANIFEST_SHA256:
        raise RuntimeError("fixture raw manifest digest changed")
    manifest_path.write_bytes(manifest_bytes)
    manifest_uri = f"file:{finalize.manifest_relative_path(MEDIA_SHA256)}"

    with sqlite3.connect(database) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            "INSERT INTO artifacts (artifact_id, source_id, artifact_kind, media_type, "
            "byte_size, digest_algorithm, digest_value, storage_uri, manifest_uri, "
            "manifest_sha256, finalized_at) VALUES (?, ?, 'raw_media', 'video/mp4', ?, "
            "'sha256', ?, ?, ?, ?, ?)",
            (
                artifact_id,
                SOURCE_ID,
                MEDIA_BYTE_SIZE,
                MEDIA_SHA256,
                finalize.storage_uri(MEDIA_SHA256),
                manifest_uri,
                RAW_MANIFEST_SHA256,
                FINALIZED_AT,
            ),
        )
        connection.execute(
            "INSERT INTO expected_occurrences (occurrence_id, source_id, session_id, "
            "sequence_number, expected_started_at, expected_ended_at, state, artifact_id, "
            "terminal_at) VALUES (?, ?, ?, 1, ?, ?, 'COMPLETE', ?, ?)",
            (
                OCCURRENCE_ID,
                SOURCE_ID,
                SESSION_ID,
                STARTED_AT,
                FINALIZED_AT,
                artifact_id,
                FINALIZED_AT,
            ),
        )
        connection.execute(
            "INSERT INTO capture_occurrences (occurrence_id, source_id, session_id, "
            "sequence_number, capture_started_at, capture_ended_at, artifact_id) "
            "VALUES (?, ?, ?, 1, ?, ?, ?)",
            (
                OCCURRENCE_ID,
                SOURCE_ID,
                SESSION_ID,
                STARTED_AT,
                FINALIZED_AT,
                artifact_id,
            ),
        )
        connection.execute(
            "INSERT INTO capture_occurrence_assertions (occurrence_id, source_id, "
            "artifact_id, manifest_layout, manifest_uri, manifest_sha256, finalized_at) "
            "VALUES (?, ?, ?, 'legacy_digest_v1', ?, ?, ?)",
            (
                OCCURRENCE_ID,
                SOURCE_ID,
                artifact_id,
                manifest_uri,
                RAW_MANIFEST_SHA256,
                FINALIZED_AT,
            ),
        )
        if scenario == "resume":
            if fingerprint.job_id_for(MEDIA_SHA256, "integrity") != JOB_ID:
                raise RuntimeError("fixture deterministic job id changed")
            connection.execute(
                "INSERT INTO processing_jobs (job_id, input_artifact_id, processor_name, "
                "processor_version, output_contract, parameters_json, parameters_sha256, "
                "state) VALUES (?, ?, ?, ?, ?, ?, ?, 'PREPARED')",
                (
                    JOB_ID,
                    artifact_id,
                    fingerprint.PROCESSOR_NAME,
                    fingerprint.PROCESSOR_VERSION,
                    fingerprint.OUTPUT_CONTRACT,
                    fingerprint.canonical_parameters("integrity").decode("utf-8"),
                    fingerprint.parameters_sha256("integrity"),
                ),
            )
        connection.commit()

    expected = json.loads(Path(__file__).with_name("expected.json").read_text(encoding="utf-8"))
    (output_root / "expected.json").write_text(
        json.dumps(expected, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--scenario", choices=("normal", "resume"), default="normal")
    args = parser.parse_args()
    prepare_fixture(args.output_root, args.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
