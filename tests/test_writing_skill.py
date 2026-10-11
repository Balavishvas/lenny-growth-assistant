"""Tests for the dedicated Ship 30 for 30 writing workflow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.writing_skill import apply_writing_skill, is_ship30_request  # noqa: E402


def test_ship30_trigger_phrases_are_case_and_whitespace_insensitive():
    assert is_ship30_request("Please write a Ship 30 for 30 essay")
    assert is_ship30_request("Can you WRITE AN ESSAY about product-market fit?")
    assert is_ship30_request("Draft a 1,250 word essay")
    assert is_ship30_request("  long-form   essay  ")


def test_regular_research_question_does_not_activate_writing_skill():
    assert not is_ship30_request("What is product-market fit?")
    base = "Ground answers in retrieved evidence."
    assert apply_writing_skill(base, "What is product-market fit?") == base


def test_writing_skill_is_injected_and_preserves_grounding_rules():
    base = "Ground answers in retrieved evidence."
    result = apply_writing_skill(base, "Write an essay about finding product-market fit")
    assert result.startswith(base)
    assert "Active writing workflow: Ship 30 for 30" in result
    assert "Never invent a source, quote, metric" in result
    assert "approximately 1,250 words" in result


def test_missing_skill_file_does_not_break_chat(monkeypatch):
    import app.writing_skill as module

    monkeypatch.setattr(module, "_SKILL_PATH", Path("missing-ship30-skill.md"))
    base = "Ground answers in retrieved evidence."
    assert apply_writing_skill(base, "Write an essay") == base
