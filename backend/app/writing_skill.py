"""Activation and quality checks for the Ship 30 for 30 writing workflow."""
from __future__ import annotations

from pathlib import Path
import re

_SKILL_PATH = Path(__file__).resolve().parent / "skills" / "ship_30_for_30.md"
_TRIGGER_PHRASES = (
    "ship 30 for 30", "ship 30", "30 for 30",
    "1250 word essay", "1,250 word essay",
    "1100 word essay", "1,100 word essay",
    "1400 word essay", "1,400 word essay",
    "write an essay", "draft an essay",
    "write me an essay", "long-form essay", "long form essay",
)
_SUMMARY_OPENERS = (
    "the search for the passages", "the search was successful",
    "here are the findings", "here are the relevant passages",
    "the following sources", "search results:",
)


def is_ship30_request(message: str) -> bool:
    """Return whether the user explicitly asks for the long-form writing workflow."""
    normalized = re.sub(r"[-_]", " ", message.casefold())
    normalized = re.sub(r"ship\s*30", "ship 30", normalized)
    normalized = re.sub(r"30\s*for\s*30", "30 for 30", normalized)
    normalized = " ".join(normalized.split())
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
        + "Follow the dedicated workflow below for this response while preserving all grounding and citation rules above.\n"
        + "Never invent a source, citation, quotation, metric, timestamp, or speaker attribution.\n\n"
        + instructions
    )


def _normalize_quote_text(value: str) -> str:
    """Normalize punctuation and case for conservative quote matching."""
    return " ".join(re.findall(r"\w+", value.casefold()))


def essay_quality_issues(answer: str, sources: list[dict] | None = None) -> list[str]:
    """Check essay completeness plus detectable thesis, citation, and quote failures.

    These are deterministic warning signals, not proof that an essay is factually correct.
    """
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
    citations = [int(number) for number in re.findall(r"\[(\d+)\]", text)]
    if not citations:
        issues.append("missing_citations")
    # Source indexes are one-based and must resolve to the sources shown in the UI.
    if sources and any(number < 1 or number > len(sources) for number in citations):
        issues.append("citation_out_of_range")
    # Catch escaped heading/separator markers that show up literally in the preview.
    if re.search(r"(?m)^\\#{1,6}\s|^\\---\s*$", text):
        issues.append("malformed_markdown")

    # The requested title explicitly rejects activation as the primary engineering goal.
    # Flag a common opposite thesis rather than trying to infer arbitrary argument semantics.
    title = re.match(r"^\s{0,3}#{0,2}\s*([^\n]+)", text)
    if title and re.search(r"product[ -]market fit.*not an activation problem", title.group(1), re.I):
        intro = text[: min(len(text), 2200)].casefold()
        contradiction_patterns = (
            r"primary focus should shift from product.market fit to activation",
            r"shift (?:the )?focus from product.market fit to activation",
            r"activation (?:should|must) be the primary (?:focus|objective|goal)",
        )
        if any(re.search(pattern, intro) for pattern in contradiction_patterns):
            issues.append("thesis_contradiction")

    # Only flag substantial direct quotations; short phrases are too ambiguous to verify.
    # Quote checks are conservative and require supplied source text.
    if sources:
        source_text = " ".join(
            _normalize_quote_text(str(source.get("content", "")))
            for source in sources if isinstance(source, dict)
        )
        quote_candidates = re.findall(r'["“](.{50,500}?)[”"]', text)
        for quote in quote_candidates:
            normalized_quote = _normalize_quote_text(quote)
            quote_words = normalized_quote.split()
            if len(quote_words) >= 10 and normalized_quote not in source_text:
                issues.append("unverified_direct_quote")
                break
    return issues



def select_better_essay(original: str, revised: str, sources: list[dict] | None = None) -> tuple[str, list[str]]:
    """Prefer fewer quality issues; break ties by closeness to 1,250 words.

    Deterministic checks are warning signals, not proof of factual correctness.
    """
    original_issues = essay_quality_issues(original, sources)
    if not revised.strip():
        return original, original_issues
    revised_issues = essay_quality_issues(revised, sources)
    if len(revised_issues) < len(original_issues):
        return revised, revised_issues
    if len(revised_issues) > len(original_issues):
        return original, original_issues
    target_words = 1250
    original_words = len(re.findall(r"\b[\w’'-]+\b", original))
    revised_words = len(re.findall(r"\b[\w’'-]+\b", revised))
    if abs(revised_words - target_words) < abs(original_words - target_words):
        return revised, revised_issues
    return original, original_issues

def essay_needs_revision(answer: str) -> bool:
    """Detect obvious Ship 30 failures before a draft is returned to the user."""
    return bool(essay_quality_issues(answer))


def build_essay_revision_messages(
    messages: list[dict[str, str]],
    draft: str,
    issues: list[str] | None = None,
    sources: list[dict] | None = None,
) -> list[dict[str, str]]:
    """Ask the model to repair a draft using explicit quality failures and retrieved evidence."""
    issue_list = list(issues or essay_quality_issues(draft, sources))
    issue_guidance = {
        "short_draft": "Expand the essay substantially to 1,300–1,400 words. Add new analysis, trade-offs, concrete implications, and actionable takeaways; do not pad by repeating the thesis.",
        "missing_citations": "Add inline bracket citations to every material transcript-derived factual claim. Use only the source numbers already present in the original conversation's retrieved evidence.",
        "citation_out_of_range": "Remove invalid citation numbers and cite only source indexes that exist in the original retrieved evidence.",
        "unverified_direct_quote": "Remove or paraphrase any direct quotation that cannot be verified word-for-word in the supplied transcript passages.",
        "missing_title": "Start with the requested, descriptive Markdown H1 title.",
        "search_summary": "Write a finished argumentative essay, not a report of search activity or a summary of retrieved passages.",
        "thesis_contradiction": "Make the body consistent with the requested thesis; do not argue the opposite of the title.",
        "malformed_markdown": "Use valid Markdown headings and remove literal backslashes before heading markers.",
    }
    targeted_fixes = "\n".join(
        f"- {issue}: {issue_guidance.get(issue, 'Fix this detected quality issue without inventing facts or sources.')}"
        for issue in issue_list
    ) or "- Improve clarity, evidence use, completeness, and structure while preserving factual grounding."
    evidence_blocks: list[str] = []
    for index, source in enumerate(sources or [], start=1):
        if not isinstance(source, dict):
            continue
        content = str(source.get("content") or "").strip()
        if not content:
            continue
        title = str(source.get("title") or "Untitled source")
        guest = str(source.get("guest") or "").strip()
        url = str(source.get("url") or "").strip()
        header = f"[{index}] {title}"
        if guest:
            header += f" — guest: {guest}"
        if url:
            header += f"\nSource URL: {url}"
        evidence_blocks.append(f"{header}\nPassage: {content[:5000]}")
    evidence_section = (
        "\n\nRetrieved evidence available for revision (keep these original citation indexes):\n"
        + "\n\n".join(evidence_blocks)
        if evidence_blocks else
        "\n\nUse only the retrieved evidence already present in the conversation. If it does not support a claim, narrow or omit that claim."
    )
    revision = (
        "QUALITY-CONTROL RETRY: The previous draft failed these checks:\n"
        + targeted_fixes
        + "\n\nRewrite the draft as a complete, polished Ship 30 for 30 essay. Target 1,300–1,400 words, "
        "with a specific thesis, 4–6 meaningful sections, concrete reasoning, trade-offs, and 3–5 useful takeaways. "
        "Do not add filler or repeat the same point to hit length. Every material factual claim about a transcript "
        "must cite the existing source number (for example [1]); never invent citations, sources, quotations, metrics, "
        "or speaker attributions. Prefer paraphrase over an uncertain direct quote. Return only the finished essay.\n\n"
        "Previous draft to improve:\n"
        + draft
        + evidence_section
    )
    return [*messages, {"role": "user", "content": revision}]

def enforce_essay_output_contract(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Place a concise, high-priority output contract directly in the final user turn."""
    if not messages or messages[-1].get("role") != "user":
        return messages
    content = messages[-1].get("content", "")
    if not is_ship30_request(content):
        return messages
    directive = (
        "\n\nMANDATORY FINAL OUTPUT FORMAT — this instruction is part of the user's request:\n"
        "Write the complete Ship 30 essay now. Do NOT summarize retrieved passages, report search "
        "results, ask whether the user wants more detail, or describe what the sources contain. "
        "Begin with the exact essay title, then write the full 1,100–1,400-word article in polished "
        "Markdown with meaningful headings, an actionable takeaway section, and a conclusion. "
        "Use only the supplied transcript evidence and its existing [number] citations. Attribute "
        "claims to the correct speaker; distinguish evidence from analysis; never invent facts or "
        "citations. If evidence supports only a narrow claim, write a careful essay around that "
        "supported claim rather than reverting to a search summary. Return only the essay."
    )
    # Idempotent in case a caller applies the contract more than once.
    if "MANDATORY FINAL OUTPUT FORMAT" in content:
        return messages
    return [*messages[:-1], {**messages[-1], "content": content + directive}]
