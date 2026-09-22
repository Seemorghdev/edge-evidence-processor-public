from __future__ import annotations

import processor
from processor import worker


def test_public_namespace_delegates_to_proven_worker() -> None:
    assert processor.run is worker.run
    assert processor.snapshot is worker.snapshot
    assert processor.RunSummary is worker.RunSummary


def test_adk_module_import_does_not_require_google_adk() -> None:
    from processor.agent import adk_tools

    assert callable(adk_tools.main)
    assert callable(adk_tools.build_processor_adk_tool)
