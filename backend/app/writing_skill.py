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


def essay_needs_revision(answer: str) -> bool:
    """Detect obvious Ship 30 failures before a draft is returned to the user."""
    text = answer.strip()
    if not text:
        return True
    if text.casefold().startswith(_SUMMARY_OPENERS):
        return True
    words = re.findall(r"\b[\w’'-]+\b", text)
    has_title = bool(re.match(r"^\s{0,3}#?\s*[^\n]{8,100}\n", text))
    # A requested ~1,250-word essay below 850 words is almost always incomplete.
    return len(words) < 850 or not has_title


def build_essay_revision_messages(
    messages: list[dict[str, str]], draft: str
) -> list[dict[str, str]]:
    """Ask the same grounded model to repair a clearly incomplete first draft."""
    revision = (
        "QUALITY-CONTROL RETRY: The previous attempt did not satisfy the active Ship 30 for 30 "
        "essay contract. Rewrite it as a complete, polished essay—not a summary of search results. "
        "Target 1,100–1,400 words, start with the title, develop one coherent thesis, use useful "
        "headings, include specific actionable takeaways, and end with a memorable conclusion. "
        "Remove repetition and generic filler. Preserve only citations that map to the supplied "
        "evidence, do not invent facts or guest attributions, and qualify unsupported claims. "
        "Return only the revised essay.\n\nPrevious draft to improve:\n"
        + draft
    )
    return [*messages, {"role": "user", "content": revision}]
