from __future__ import annotations

import asyncio
import builtins
import importlib
import importlib.util
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from processor.contracts.canonical import canonical_json
from processor.database import migrations
from processor.pilot import (
    ProcessorAgentContext,
    ProcessorAgentCore,
    ProcessorInspection,
    ProcessorPilotError,
    SQLiteProcessorReadTool,
)
from processor.provenance import CANONICAL_COMMIT

ROOT = Path(__file__).resolve().parents[2]
_POSITIVE_MARK = pytest.mark.pra_p02a_adk_positive


class FixedReadTool:
    def inspect(self) -> ProcessorInspection:
        return ProcessorInspection(
            database_schema_version=10,
            eligible_count=2,
            missing_count=0,
            prepared_count=0,
            complete_count=2,
        )


def _adk_is_installed() -> bool:
    try:
        return importlib.util.find_spec("google.adk") is not None
    except ModuleNotFoundError:
        return False


def _load_adapter_module() -> ModuleType:
    adapter_path = ROOT / "processor" / "agent" / "adk_tools.py"
    spec = importlib.util.spec_from_file_location(
        "processor_pilot_test_adk_adapter",
        adapter_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _core() -> ProcessorAgentCore:
    return ProcessorAgentCore(
        FixedReadTool(),
        context=ProcessorAgentContext(
            canonical_commit=CANONICAL_COMMIT,
            authority_instance="pra-p02a-test",
        ),
    )


def _tool_function(tool: object) -> Any:
    for attribute in ("func", "_func"):
        function = getattr(tool, attribute, None)
        if callable(function):
            return function
    raise AssertionError("FunctionTool does not expose the wrapped callable")


def _tool_run_async(tool: object) -> Any:
    run_async = getattr(tool, "run_async", None)
    if callable(run_async):
        return run_async
    raise AssertionError("FunctionTool does not expose run_async")


def _run_tool(
    tool: object,
    *,
    args: dict[str, Any],
    tool_context: object | None = None,
) -> Any:
    return asyncio.run(
        _tool_run_async(tool)(
            args=args,
            tool_context=tool_context,
        )
    )


def _error_code(error: ProcessorPilotError, expected: str) -> None:
    assert error.finding == expected
    assert error.args == (expected,)
    assert str(error) == expected
    assert repr(error) == f"ProcessorPilotError({expected!r})"


def test_package_and_cli_import_without_adk() -> None:
    assert not _adk_is_installed()
    sys.modules.pop("processor.agent.adk_tools", None)
    package = importlib.import_module("processor.pilot")
    cli = importlib.import_module("processor.inspect")

    assert callable(package.run_processor_pilot)
    assert callable(cli.main)
    assert "processor.agent.adk_tools" not in sys.modules


def test_explicit_adapter_build_reports_exact_missing_extra_without_adk() -> None:
    assert not _adk_is_installed()
    adapter = importlib.import_module("processor.agent.adk_tools")

    with pytest.raises(ProcessorPilotError) as captured:
        adapter.build_processor_adk_tool(_core())

    _error_code(captured.value, "processor_adk_extra_required")
    assert isinstance(captured.value.__cause__, ModuleNotFoundError)
    assert captured.value.__cause__.name in {"google", "google.adk"}


@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_adapter_imports_with_real_extra() -> None:
    from processor.agent.adk_tools import (
        PROCESSOR_ADK_TOOL_NAME,
        build_processor_adk_tool,
    )

    tool = build_processor_adk_tool(_core())

    assert tool.__class__.__mro__[1].__module__.startswith("google.adk")
    assert getattr(tool, "name", None) == PROCESSOR_ADK_TOOL_NAME
    wrapped = _tool_function(tool)
    assert wrapped.__module__ == "processor.agent.adk_tools"
    assert wrapped.__name__ == PROCESSOR_ADK_TOOL_NAME


@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_core_inspection_is_canonical_and_non_mutating() -> None:
    first = _core().inspect()
    second = _core().inspect()

    first_payload = json.loads(canonical_json(first.public()))
    second_payload = json.loads(canonical_json(second.public()))
    assert first_payload == second_payload
    assert first.schema == "processor-readonly-pilot-result.v1"
    assert first.classification.primary_code == "PROCESSOR_CONVERGED"
    assert first.observation.finding_codes == ("PROCESSOR_CONVERGED",)
    assert first.observation.eligible_count == 2
    assert first.observation.complete_count == 2
    assert first.proposal.mutation_class.name == "READ_ONLY"
    assert first.receipt.final_status.name == "READ_ONLY_COMPLETE"

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_returns_exact_canonical_public_payload() -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    expected = json.loads(canonical_json(_core().inspect().public()))
    tool = build_processor_adk_tool(_core())

    assert _run_tool(tool, args={}) == expected

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_is_single_use() -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    tool = build_processor_adk_tool(_core())

    first = _run_tool(tool, args={})
    assert first["schema"] == "processor-readonly-pilot-result.v1"

    with pytest.raises(ProcessorPilotError) as captured:
        _run_tool(tool, args={})
    _error_code(captured.value, "processor_core_already_completed")

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_concurrent_invocation_allows_one_success() -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    tool = build_processor_adk_tool(_core())
    run_async = _tool_run_async(tool)

    async def invoke_twice() -> list[object]:
        return await asyncio.gather(
            run_async(args={}, tool_context=None),
            run_async(args={}, tool_context=None),
            return_exceptions=True,
        )

    results = asyncio.run(invoke_twice())
    successes = [result for result in results if isinstance(result, dict)]
    failures = [
        result
        for result in results
        if isinstance(result, ProcessorPilotError)
    ]

    assert len(successes) == 1
    assert len(failures) == 1
    _error_code(failures[0], "processor_core_already_completed")


@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_rejects_non_mapping_before_execution() -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    tool = build_processor_adk_tool(_core())

    with pytest.raises(ProcessorPilotError) as captured:
        _run_tool(tool, args=None)  # type: ignore[arg-type]
    _error_code(captured.value, "processor_adk_arguments_forbidden")

    result = _run_tool(tool, args={})
    assert result["schema"] == "processor-readonly-pilot-result.v1"

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_rejects_non_empty_mapping_before_execution() -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    tool = build_processor_adk_tool(_core())

    with pytest.raises(ProcessorPilotError) as captured:
        _run_tool(tool, args={"unexpected": "forbidden"})
    _error_code(captured.value, "processor_adk_arguments_forbidden")

    result = _run_tool(tool, args={})
    assert result["schema"] == "processor-readonly-pilot-result.v1"

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_preserves_context_and_provenance() -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    expected = json.loads(canonical_json(_core().inspect().public()))
    tool = build_processor_adk_tool(_core())
    result = _run_tool(tool, args={})

    authority = result["observation"]["authority"]
    assert authority["canonical_commit"] == CANONICAL_COMMIT
    assert authority["authority_instance"] == "pra-p02a-test"
    assert authority == expected["observation"]["authority"]

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_adk_tool_preserves_database_read_only_boundary(
    tmp_path: Path,
) -> None:
    from processor.agent.adk_tools import build_processor_adk_tool

    database = tmp_path / "processor.sqlite3"
    migrations.migrate(database)
    core = ProcessorAgentCore(
        SQLiteProcessorReadTool(database),
        context=ProcessorAgentContext(
            canonical_commit=CANONICAL_COMMIT,
            authority_instance="pra-p02a-sqlite-boundary",
        ),
    )
    tool = build_processor_adk_tool(core)

    before = database.read_bytes()
    result = _run_tool(tool, args={})
    after = database.read_bytes()

    assert result["schema"] == "processor-readonly-pilot-result.v1"
    assert result["observation"]["authority"]["authority_instance"] == (
        "pra-p02a-sqlite-boundary"
    )
    assert before == after

    read_only = sqlite3.connect(
        f"{database.resolve().as_uri()}?mode=ro",
        uri=True,
    )
    with pytest.raises(sqlite3.OperationalError):
        read_only.execute(
            "CREATE TABLE forbidden_mutation (value TEXT NOT NULL)"
        )
    read_only.close()

@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_standard_processor_paths_never_import_adk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def guarded_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> Any:
        if name == "google.adk" or name.startswith("google.adk."):
            raise AssertionError("standard processor path imported google.adk")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    worker = importlib.import_module("processor.worker")
    pilot = importlib.import_module("processor.pilot")

    assert callable(worker.run)
    assert callable(pilot.run_processor_pilot)


@pytest.mark.skipif(
    not _adk_is_installed(),
    reason="install with the optional ADK extra: uv pip install .[adk]",
)
@_POSITIVE_MARK
def test_no_generic_adk_runner_or_root_agent_exists() -> None:
    import processor.agent.adk_tools as adapter

    assert not (ROOT / "processor" / "agent.py").exists()
    assert not hasattr(adapter, "root_agent")
    assert not hasattr(adapter, "Runner")
    assert not hasattr(adapter, "InMemoryRunner")
    assert not hasattr(adapter, "App")


def test_missing_google_namespace_maps_to_extra_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> Any:
        if name == "google.adk.tools":
            raise ModuleNotFoundError(
                "No module named 'google'",
                name="google",
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    adapter = _load_adapter_module()

    with pytest.raises(ProcessorPilotError) as captured:
        adapter.build_processor_adk_tool(_core())

    _error_code(captured.value, "processor_adk_extra_required")
    assert isinstance(captured.value.__cause__, ModuleNotFoundError)
    assert captured.value.__cause__.name == "google"


def test_missing_google_adk_namespace_maps_to_extra_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> Any:
        if name == "google.adk.tools":
            raise ModuleNotFoundError(
                "No module named 'google.adk'",
                name="google.adk",
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    adapter = _load_adapter_module()

    with pytest.raises(ProcessorPilotError) as captured:
        adapter.build_processor_adk_tool(_core())

    _error_code(captured.value, "processor_adk_extra_required")
    assert isinstance(captured.value.__cause__, ModuleNotFoundError)
    assert captured.value.__cause__.name == "google.adk"


def test_missing_unrelated_dependency_is_not_remapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> Any:
        if name == "google.adk.tools":
            raise ModuleNotFoundError(
                "No module named 'unrelated_runtime'",
                name="unrelated_runtime",
            )
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    adapter = _load_adapter_module()

    with pytest.raises(ModuleNotFoundError) as captured:
        adapter.build_processor_adk_tool(_core())

    assert captured.value.name == "unrelated_runtime"
    assert captured.value.__cause__ is None


def test_runtime_failure_during_google_adk_import_is_not_remapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: object = (),
        level: int = 0,
    ) -> Any:
        if name == "google.adk.tools":
            raise RuntimeError("synthetic_google_adk_initialization_failure")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    adapter = _load_adapter_module()

    with pytest.raises(RuntimeError) as captured:
        adapter.build_processor_adk_tool(_core())

    assert str(captured.value) == (
        "synthetic_google_adk_initialization_failure"
    )
    assert captured.value.__cause__ is None


def test_extra_module_does_not_broaden_public_surface() -> None:
    module = _load_adapter_module()

    assert module.__all__ == [
        "PROCESSOR_ADK_TOOL_NAME",
        "build_processor_adk_tool",
        "main",
    ]
    defined_names = {
        name
        for name, value in vars(module).items()
        if callable(value)
        and getattr(value, "__module__", None) == module.__name__
        and not name.startswith("_")
    }
    assert defined_names == {"build_processor_adk_tool", "main"}
