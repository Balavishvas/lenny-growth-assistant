"""Tests for the dedicated Ship 30 for 30 writing workflow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.writing_skill import (  # noqa: E402
    apply_writing_skill,
    build_essay_revision_messages,
    essay_needs_revision,
    essay_quality_issues,
    enforce_essay_output_contract,
    is_ship30_request,
)


def test_ship30_trigger_phrases_are_case_and_whitespace_insensitive():
    assert is_ship30_request("Please write a Ship 30 for 30 essay")
    assert is_ship30_request("Can you WRITE AN ESSAY about product-market fit?")
    assert is_ship30_request("Draft a 1,250 word essay")
    assert is_ship30_request("  long-form   essay  ")
    assert is_ship30_request("Ship30 essay on PMF")
    assert is_ship30_request("Write a Ship-30 essay")
    assert is_ship30_request("Draft a 1250-word essay")
    assert is_ship30_request("Draft a 1,250-word essay")
    assert is_ship30_request("Write a 1,100 word essay")
    assert is_ship30_request("Draft a 1,400-word essay")
    assert is_ship30_request("30for30 essay")


def test_regular_research_question_does_not_activate_writing_skill():
    assert not is_ship30_request("What is product-market fit?")
    base = "Ground answers in retrieved evidence."
    assert apply_writing_skill(base, "What is product-market fit?") == base


def test_writing_skill_is_injected_and_preserves_grounding_rules():
    base = "Ground answers in retrieved evidence."
    result = apply_writing_skill(base, "Write an essay about finding product-market fit")
    assert result.startswith(base)
    assert "Active writing workflow: Ship 30 for 30" in result
    assert "Never invent a source" in result
    assert "approximately 1,250 words" in result or "1,100–1,400 words" in result
    assert "finished essay itself" in result
    assert "not a search report" in result


def test_short_search_summary_is_flagged_for_revision():
    summary = (
        "The search for the passages related to your query has been successful. "
        "Here are the findings. Rahul Vohra says to focus on product market fit."
    )
    assert essay_needs_revision(summary)
    assert "search_summary" in essay_quality_issues(summary)


def test_short_essay_is_flagged_for_revision():
    short = "# Product-Market Fit Is Not an Activation Problem\n\n" + ("Some text. " * 80)
    assert essay_needs_revision(short)


def test_long_title_led_essay_without_citations_is_flagged():
    long = "# Product-Market Fit Is Not an Activation Problem\n\n" + ("Useful paragraph text. " * 500)
    assert "missing_citations" in essay_quality_issues(long)
    assert essay_needs_revision(long)


def test_complete_cited_essay_passes_deterministic_checks():
    long = "# Product-Market Fit Is Not an Activation Problem\n\n" + ("Useful paragraph with evidence [6]. " * 350)
    assert essay_quality_issues(long) == []
    assert not essay_needs_revision(long)


def test_escaped_markdown_heading_is_flagged():
    long = "# Product-Market Fit Is Not an Activation Problem\n\n" + ("Useful paragraph with evidence [6]. " * 350)
    malformed = long + "\n\\#### Broken heading\n"
    assert "malformed_markdown" in essay_quality_issues(malformed)


def test_revision_prompt_preserves_context_and_demands_complete_essay():
    messages = [{"role": "system", "content": "Use grounded citations."}, {"role": "user", "content": "Write an essay."}]
    revised = build_essay_revision_messages(messages, "A short first draft.")
    assert revised[:2] == messages
    assert revised[-1]["role"] == "user"
    assert "not a summary of search results" in revised[-1]["content"]
    assert "1,100–1,400 words" in revised[-1]["content"]
    assert "citation" in revised[-1]["content"]
    assert "A short first draft." in revised[-1]["content"]


def test_missing_skill_file_does_not_break_chat(monkeypatch):
    import app.writing_skill as module

    monkeypatch.setattr(module, "_SKILL_PATH", Path("missing-ship30-skill.md"))
    base = "Ground answers in retrieved evidence."
    assert apply_writing_skill(base, "Write an essay") == base



def test_output_contract_is_appended_to_ship30_user_turn():
    messages = [
        {"role": "system", "content": "Ground claims in sources."},
        {"role": "user", "content": "Write a Ship 30 for 30 essay about product-market fit."},
    ]
    result = enforce_essay_output_contract(messages)
    assert result[0] == messages[0]
    assert result[-1]["role"] == "user"
    assert "MANDATORY FINAL OUTPUT FORMAT" in result[-1]["content"]
    assert "Do NOT summarize retrieved passages" in result[-1]["content"]
    assert "1,100–1,400-word article" in result[-1]["content"]


def test_output_contract_does_not_change_regular_chat():
    messages = [{"role": "user", "content": "What did Rahul Vohra say about activation?"}]
    assert enforce_essay_output_contract(messages) == messages


def test_output_contract_is_idempotent():
    messages = [{"role": "user", "content": "Write an essay of 1,250 words."}]
    once = enforce_essay_output_contract(messages)
    twice = enforce_essay_output_contract(once)
    assert twice == once
