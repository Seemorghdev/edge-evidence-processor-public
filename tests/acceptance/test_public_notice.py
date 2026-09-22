from pathlib import Path


def test_adk_notice_uses_the_pinned_public_source() -> None:
    notice = Path("THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    assert "a3ff2cb5586a3d823f63082a99e2977d397f7cf1" in notice
    assert "core/python/ambient-expense-agent" in notice
    assert "python/agents/ambient-expense-agent" not in notice
