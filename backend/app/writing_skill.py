"""Activation and quality checks for the Ship 30 for 30 writing workflow."""
from __future__ import annotations

from pathlib import Path
import re

_SKILL_PATH = Path(__file__).resolve().parent / "skills" / "ship_30_for_30.md"
_TRIGGER_PHRASES = (
    "ship 30 for 30", "ship 30", "30 for 30", "1250 word essay",
    "1,250 word essay", "write an essay", "draft an essay",
    "write me an essay", "long-form essay", "long form essay",
)
_SUMMARY_OPENERS = (
    "the search for the passages", "the search was successful",
    "here are the findings", "here are the relevant passages",
    "the following sources", "search results:",
)


def is_ship30_request(message: str) -> bool:
    """Return whether the user explicitly asks for the long-form writing workflow."""
    normalized = " ".join(message.casefold().split())
    return any(phrase in normalized for phrase in _TRIGGER_PHRASES)


def apply_writing_skill(system_prompt: str, user_message: str) -> str:
    """Append the dedicated writing guidance only for essay-writing requests."""
    if not is_ship30_request(user_message):
        return system_prompt
    try:
        instructions = _SKILL_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return system_prompt
    if not instructions:
        return system_prompt
    return (
        system_prompt
        + "\n\n## Active writing workflow: Ship 30 for 30\n"
        + "Follow the dedicated workflow below for this response while preserving all grounding and citation rules above.\n\n"
        + instructions
    )


def essay_quality_issues(answer: str) -> list[str]:
    """Return deterministic checks that can identify obviously incomplete essay drafts."""
    text = answer.strip()
    issues: list[str] = []
    if not text:
        return ["empty"]
    if text.casefold().startswith(_SUMMARY_OPENERS):
        issues.append("search_summary")
    words = re.findall(r"\b[\w’'-]+\b", text)
    has_title = bool(re.match(r"^\s{0,3}#{0,2}\s*[^\n]{8,120}\n", text))
    if len(words) < 1000:
        issues.append("short_draft")
    if not has_title:
        issues.append("missing_title")
    # Citation syntax is a cheap proxy only; it does not prove each claim is supported.
    if not re.search(r"\[\d+\]", text):
        issues.append("missing_citations")
    # Catch escaped heading/separator markers that show up literally in the preview.
    if re.search(r"(?m)^\\#{1,6}\s|^\\---\s*$", text):
        issues.append("malformed_markdown")
    return issues


def essay_needs_revision(answer: str) -> bool:
    """Detect obvious Ship 30 failures before a draft is returned to the user."""
    return bool(essay_quality_issues(answer))


def build_essay_revision_messages(
    messages: list[dict[str, str]], draft: str
) -> list[dict[str, str]]:
    """Ask the same grounded model to repair a clearly incomplete first draft."""
    revision = (
        "QUALITY-CONTROL RETRY: The previous attempt failed one or more deterministic essay checks. "
        "Rewrite it as a complete, polished Ship 30 for 30 essay, not a summary of search results. "
        "Target 1,100–1,400 words. Start with a clear title, use valid Markdown headings (for example, "
        "'## Heading' with no backslash before the hashes), develop one coherent thesis, include "
        "specific actionable takeaways, and end with a memorable conclusion. Every material claim "
        "about a transcript must cite its actual supplied source number like [2]. Only use citation "
        "numbers present in the supplied evidence; never invent sources, quotes, metrics, or guest "
        "attributions. Separate transcript-supported facts from your interpretation. Do not add "
        "citations merely to satisfy the checker: they must support the nearby claim. Avoid generic "
        "openers, repetition, and filler. Return only the revised essay.\n\n"
        "Previous draft to improve:\n"
        + draft
    )
    return [*messages, {"role": "user", "content": revision}]
