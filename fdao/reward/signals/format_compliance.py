"""FormatComplianceSignal: checks that the response has the required structure.

Task-category aware — different categories have different structural requirements.
Returns 1.0 (compliant) or 0.0 (non-compliant). Binary because format is a
hard constraint, not a gradient.

Reward hacking surface
----------------------
Risk: agent writes structurally-correct but semantically garbage content
(e.g. a valid Python function that does nothing, or a correctly-formatted number
that is wrong).
Mitigation: FormatComplianceSignal is intentionally low-weight (0.05–0.1).
It provides a gradient toward the correct *shape* of answer but can never
overcome a low CorrectnessSignal at normal weight configurations.
The rule: format weight should never exceed correctness weight.
"""

from __future__ import annotations

import re

from fdao.reward.composer import RewardSignal
from fdao.tasks.base import Task
from fdao.types import TaskCategory

_NUM_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")
_CODE_DEF_PATTERN = re.compile(r"^\s*def\s+\w+\s*\(", re.MULTILINE)
_FENCED_CODE_PATTERN = re.compile(r"```(?:python)?\s*\n.+?```", re.DOTALL)


class FormatComplianceSignal(RewardSignal):
    """Scores whether the attempt has the structurally correct form for its task type."""

    name = "format_compliance"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    def score(self, task: Task, attempt: str) -> float:
        if task.category == TaskCategory.CODE_GENERATION:
            return self._score_code(attempt)
        if task.category == TaskCategory.QA:
            return self._score_qa(attempt)
        if task.category == TaskCategory.TOOL_USE:
            return self._score_tool_use(attempt)
        return 1.0

    def _score_code(self, attempt: str) -> float:
        """Code response must contain at least one function definition."""
        if _FENCED_CODE_PATTERN.search(attempt):
            return 1.0
        if _CODE_DEF_PATTERN.search(attempt):
            return 1.0
        return 0.0

    def _score_qa(self, attempt: str) -> float:
        """QA/math response must be non-empty and not excessively long.

        We don't require a number specifically — LOGIC tasks expect words.
        Just check the response is a short, direct answer (< 500 chars) and
        not blank.
        """
        cleaned = attempt.strip()
        if not cleaned:
            return 0.0
        # Penalise very long QA answers (suggests the agent explained instead of answered)
        if len(cleaned) > 500:
            return 0.5
        return 1.0

    def _score_tool_use(self, attempt: str) -> float:
        # Stub — Phase 5 implements tool-use tasks.
        return 1.0
