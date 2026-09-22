from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from processor.pipeline.lock import spool_lock

ROOT = Path(__file__).resolve().parents[2]
PREPARE = ROOT / "fixtures" / "cloud_run" / "prepare.py"
EXPECTED = json.loads(
    (ROOT / "fixtures" / "cloud_run" / "expected.json").read_text(encoding="utf-8")
)


def _prepare(root: Path, scenario: str = "normal") -> tuple[Path, Path]:
    completed = subprocess.run(
        [
            sys.executable,
            str(PREPARE),
            "--output-root",
            str(root),
            "--scenario",
            scenario,
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return root / "authority.sqlite3", root / "spool"


def _worker(database: Path, spool: Path) -> tuple[int, dict[str, object], str]:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "processor.cli",
            "run",
            "--database",
            str(database),
            "--spool-root",
            str(spool),
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    payload = json.loads(completed.stdout) if completed.stdout.strip() else {}
    return completed.returncode, payload, completed.stderr


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_outputs(root: Path, database: Path) -> None:
    derived = EXPECTED["derived_output"]
    assert _sha256(root / derived["report_path"]) == derived["report_sha256"]
    assert _sha256(root / derived["manifest_path"]) == derived["manifest_sha256"]
    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT job_id, state, output_artifact_id FROM processing_jobs"
        ).fetchone()
    assert row == (derived["job_id"], "COMPLETE", derived["artifact_id"])


def test_image_and_terraform_use_the_real_worker_contract() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    terraform = (ROOT / "terraform" / "cloud_run_job.tf").read_text(encoding="utf-8")
    assert 'ENTRYPOINT ["edge-evidence-processor"]' in dockerfile
    assert '"run"' in terraform
    assert '"--database"' in terraform
    assert '"--spool-root"' in terraform
    assert "synthetic_processor.py" not in terraform
    assert "environment_variables" not in terraform


def test_committed_fixture_normal_replay_resume_and_busy_lock(tmp_path: Path) -> None:
    normal = tmp_path / "normal"
    database, spool = _prepare(normal)
    code, summary, stderr = _worker(database, spool)
    assert (code, summary, stderr) == (
        EXPECTED["first_run"]["exit_status"],
        EXPECTED["first_run"]["summary"],
        "",
    )
    _assert_outputs(normal, database)

    with sqlite3.connect(database) as connection:
        state_before = connection.execute(
            "SELECT job_id, state, output_artifact_id FROM processing_jobs"
        ).fetchall()
    code, summary, stderr = _worker(database, spool)
    assert (code, summary, stderr) == (
        EXPECTED["replay"]["exit_status"],
        EXPECTED["replay"]["summary"],
        "",
    )
    with sqlite3.connect(database) as connection:
        state_after = connection.execute(
            "SELECT job_id, state, output_artifact_id FROM processing_jobs"
        ).fetchall()
    assert state_after == state_before

    resume = tmp_path / "resume"
    resume_database, resume_spool = _prepare(resume, "resume")
    code, summary, stderr = _worker(resume_database, resume_spool)
    assert (code, summary, stderr) == (
        EXPECTED["resume"]["exit_status"],
        EXPECTED["resume"]["summary"],
        "",
    )
    _assert_outputs(resume, resume_database)

    busy = tmp_path / "busy"
    busy_database, busy_spool = _prepare(busy)
    with spool_lock(busy_spool, mode="exclusive"):
        code, summary, stderr = _worker(busy_database, busy_spool)
    assert (code, summary, stderr) == (
        EXPECTED["busy_lock"]["exit_status"],
        EXPECTED["busy_lock"]["summary"],
        "",
    )
    with sqlite3.connect(busy_database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM processing_jobs").fetchone()[0] == 0
