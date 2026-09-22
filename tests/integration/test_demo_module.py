from __future__ import annotations

import importlib.util
from pathlib import Path


def test_demo_is_present_and_importable() -> None:
    path = Path("examples/synthetic_processor.py")
    spec = importlib.util.spec_from_file_location("processor_demo", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.SCENARIOS == ("normal", "resume", "busy-lock")
