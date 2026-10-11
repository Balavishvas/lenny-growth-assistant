"""Activation and loading for the dedicated Ship 30 for 30 writing workflow."""
from __future__ import annotations

from pathlib import Path

_SKILL_PATH = Path(__file__).resolve().parent / "skills" / "ship_30_for_30.md"
_TRIGGER_PHRASES = (
    "ship 30 for 30",
    "ship 30",
    "30 for 30",
    "1250 word essay",
    "1,250 word essay",
    "write an essay",
    "draft an essay",
    "write me an essay",
    "long-form essay",
    "long form essay",
)


def is_ship30_request(message: str) -> bool:
    """Return whether a user explicitly asks for the long-form writing workflow."""
    normalized = " ".join(message.casefold().split())
    return any(phrase in normalized for phrase in _TRIGGER_PHRASES)


def apply_writing_skill(system_prompt: str, user_message: str) -> str:
    """Append the dedicated writing guidance only for essay-writing requests."""
    if not is_ship30_request(user_message):
        return system_prompt
    try:
        instructions = _SKILL_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        # Fail open for ordinary chat; the application grounding prompt remains intact.
        return system_prompt
    if not instructions:
        return system_prompt
    return (
        system_prompt
        + "\n\n## Active writing workflow: Ship 30 for 30\n"
        + "Follow the dedicated workflow below for this response while preserving all grounding and citation rules above.\n\n"
        + instructions
    )
