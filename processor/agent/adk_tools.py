"""Lazy, bounded Google ADK adapter for read-only processor inspection."""

from __future__ import annotations

import json
import threading
from typing import Any, Sequence

from processor.contracts.canonical import canonical_json
from processor.pilot import ProcessorAgentCore, ProcessorPilotError

PROCESSOR_ADK_TOOL_NAME = "inspect_processor_authority"


def _function_tool_type() -> type[Any]:
    try:
        from google.adk.tools import FunctionTool
    except ModuleNotFoundError as exc:
        if exc.name in {"google", "google.adk"}:
            raise ProcessorPilotError("processor_adk_extra_required") from exc
        raise
    return FunctionTool


def build_processor_adk_tool(core: ProcessorAgentCore) -> Any:
    """Build the sole read-only ADK tool over one configured core."""

    if not isinstance(core, ProcessorAgentCore):
        raise TypeError("processor ADK adapter requires ProcessorAgentCore")

    FunctionTool = _function_tool_type()

    class _StrictZeroArgumentFunctionTool(FunctionTool):
        """FunctionTool that accepts one valid empty-argument attempt."""

        def __init__(self, *, func: Any) -> None:
            super().__init__(func, require_confirmation=False)
            self._processor_claim_lock = threading.Lock()
            self._processor_consumed = False

        def _claim_once(self) -> None:
            with self._processor_claim_lock:
                if self._processor_consumed:
                    raise ProcessorPilotError("processor_core_already_completed")
                self._processor_consumed = True

        async def run_async(
            self,
            *,
            args: dict[str, Any],
            tool_context: Any,
        ) -> Any:
            if not isinstance(args, dict) or args:
                raise ProcessorPilotError("processor_adk_arguments_forbidden")
            self._claim_once()
            return await super().run_async(args=args, tool_context=tool_context)

    def inspect_processor_authority() -> dict[str, object]:
        """Inspect the configured processor authority exactly once."""

        return json.loads(canonical_json(core.inspect().public()))

    if inspect_processor_authority.__name__ != PROCESSOR_ADK_TOOL_NAME:
        raise RuntimeError("processor ADK tool name mismatch")

    return _StrictZeroArgumentFunctionTool(func=inspect_processor_authority)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the bounded read-only inspection CLI without importing ADK."""

    from processor.inspect import main as inspect_main

    return inspect_main(argv)


__all__ = ["PROCESSOR_ADK_TOOL_NAME", "build_processor_adk_tool", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
