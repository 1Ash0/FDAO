"""Parses structured reflection output from the LLM into a StructuredReflection.

Parsing strategy: match each field independently with its own pattern rather than
one fragile multi-field regex. Tolerates extra whitespace, preamble text,
reordered fields, and minor formatting variations from different LLMs.

Parse quality:
  - If fewer than 4/5 fields parse, confidence is downgraded to LOW.
  - If root_cause and strategy_update have low keyword overlap (< 0.15 Jaccard),
    confidence is downgraded to LOW (incoherent diagnosis).
  - parse_failed is True if ANY field is missing.
"""

from __future__ import annotations

import re

from fdao.types import ConfidenceLevel, FailureType, StructuredReflection

_PATTERNS: dict[str, re.Pattern[str]] = {
    "failure_type":    re.compile(r"FAILURE_TYPE\s*:\s*(\S+)", re.IGNORECASE),
    "root_cause":      re.compile(r"ROOT_CAUSE\s*:\s*(.+?)(?=\n[A-Z_]+\s*:|$)", re.IGNORECASE | re.DOTALL),
    "what_worked":     re.compile(r"WHAT_WORKED\s*:\s*(.+?)(?=\n[A-Z_]+\s*:|$)", re.IGNORECASE | re.DOTALL),
    "strategy_update": re.compile(r"STRATEGY_UPDATE\s*:\s*(.+?)(?=\n[A-Z_]+\s*:|$)", re.IGNORECASE | re.DOTALL),
    "confidence":      re.compile(r"CONFIDENCE\s*:\s*(\S+)", re.IGNORECASE),
}

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "were", "be", "been", "have", "has",
    "do", "does", "did", "this", "that", "it", "its", "should", "must",
    "need", "will", "would", "can", "not", "no",
}

_VALID_FAILURE_TYPES = {ft.value for ft in FailureType}
_VALID_CONFIDENCES   = {c.value for c in ConfidenceLevel}


def _keywords(text: str) -> set[str]:
    """Content words, reduced to a 4-letter stem so that inflections match.

    Without stemming, "sorted" vs "sort" or "assumed" vs "assumptions" count as
    different words and a coherent diagnosis scores as incoherent.
    """
    words = re.findall(r"\b[a-z]{3,}\b", text.lower())
    return {w[:4] for w in words if w not in _STOP_WORDS}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def parse_reflection(raw: str) -> StructuredReflection:
    """Extract and validate structured fields from LLM reflection output."""
    fields: dict[str, str] = {}
    for name, pattern in _PATTERNS.items():
        m = pattern.search(raw)
        fields[name] = m.group(1).strip() if m else ""

    parsed_count = sum(1 for v in fields.values() if v)
    parse_failed = parsed_count < len(_PATTERNS)

    # Coherence check: root_cause and strategy_update should share vocabulary
    rc_kw  = _keywords(fields.get("root_cause", ""))
    su_kw  = _keywords(fields.get("strategy_update", ""))
    coherence = _jaccard(rc_kw, su_kw)

    # Parse the stated confidence, then potentially downgrade it
    stated_confidence = _parse_confidence(fields.get("confidence", ""))
    if parse_failed or coherence < 0.15:
        # Incoherent or incomplete reflection — cap confidence at LOW
        effective_confidence = ConfidenceLevel.LOW
    else:
        effective_confidence = stated_confidence

    return StructuredReflection(
        failure_type=_parse_failure_type(fields.get("failure_type", "")),
        root_cause=fields.get("root_cause") or "Could not parse root cause.",
        what_worked=fields.get("what_worked") or "unknown",
        strategy_update=fields.get("strategy_update") or "Try a different approach.",
        confidence=effective_confidence,
        raw=raw,
        parse_failed=parse_failed,
    )


def _parse_failure_type(s: str) -> FailureType:
    cleaned = re.sub(r"[^\w]", "_", s.lower()).strip("_")
    if not cleaned:
        return FailureType.MISUNDERSTANDING
    if cleaned in _VALID_FAILURE_TYPES:
        return FailureType(cleaned)
    for ft in _VALID_FAILURE_TYPES:
        if ft.startswith(cleaned) or cleaned.startswith(ft):
            return FailureType(ft)
    return FailureType.MISUNDERSTANDING


def _parse_confidence(s: str) -> ConfidenceLevel:
    cleaned = s.lower().strip()
    if cleaned in _VALID_CONFIDENCES:
        return ConfidenceLevel(cleaned)
    return ConfidenceLevel.LOW
