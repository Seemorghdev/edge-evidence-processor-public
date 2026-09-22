from __future__ import annotations

import pytest

from processor import cli


@pytest.mark.acceptance
def test_clean_cli_help_preserves_worker_parser() -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main(["--help"])
    assert raised.value.code == 0
