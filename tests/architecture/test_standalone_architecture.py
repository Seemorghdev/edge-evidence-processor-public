from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_legacy_monorepo_paths_are_removed() -> None:
    for path in ("apps", "packages", "demo", "deploy", "optional", "scripts"):
        assert not (ROOT / path).exists(), path


def test_processor_is_the_only_installable_application_package() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'include = ["processor*"]' in pyproject
    assert "apps*" not in pyproject
    assert "packages*" not in pyproject
    assert 'edge-evidence-processor = "processor.cli:main"' in pyproject
    assert 'processor-worker = "processor.cli:main"' in pyproject
    assert 'processor-inspect = "processor.inspect:main"' in pyproject


def test_production_source_contains_no_transplant_imports() -> None:
    forbidden = ("apps" + ".", "packages" + ".")
    for source_root in (ROOT / "processor", ROOT / "examples"):
        for path in source_root.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            assert not any(token in content for token in forbidden), path


def test_ordinary_processor_import_does_not_load_google_adk() -> None:
    before = set(sys.modules)
    importlib.import_module("processor")
    importlib.import_module("processor.agent.adk_tools")
    newly_loaded = set(sys.modules) - before
    assert not any(name == "google.adk" or name.startswith("google.adk.") for name in newly_loaded)


def test_terraform_is_a_single_bounded_cloud_run_job() -> None:
    terraform = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((ROOT / "terraform").glob("*.tf"))
    )
    assert 'resource "google_cloud_run_v2_job" "processor"' in terraform
    assert "google_project_service" not in terraform
    assert "_iam_" not in terraform
    assert 'backend "' not in terraform
    assert "allUsers" not in terraform
