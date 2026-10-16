"""Anti-pattern detection for the reflection loop.

Three failure modes detected inline during a run:

  CIRCULAR    — same strategy advice repeated across iterations (agent is stuck
                in a loop, not actually updating its approach)

  OVERCORRECT — score dropped after a HIGH-confidence reflection (the agent
                made a big confident change that made things worse)

  DRIFT       — strategy no longer addresses the original failure (the agent
                has wandered away from the root cause over iterations)

These are logged per RunStep and used in two ways:
  1. Trigger the exploration mechanism in StrategyStore (already wired)
  2. Populate the failure taxonomy table in the paper (Section 9.1)

In RL terms:
  CIRCULAR    = policy not updating despite gradient signal (stuck local optimum)
  OVERCORRECT = too-large policy update step (like high learning rate in gradient descent)
  DRIFT       = policy update decoupled from the true gradient direction
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from fdao.types import RunStep, StructuredReflection


class AntiPattern(str, Enum):
    NONE        = "none"
    CIRCULAR    = "circular"
    OVERCORRECT = "overcorrect"
    DRIFT       = "drift"


@dataclass
class AntiPatternResult:
    pattern: AntiPattern
    description: str = ""


CIRCULAR_SIMILARITY_THRESHOLD = 0.60    # Jaccard similarity above this → circular
DRIFT_WINDOW = 3                        # look back this many steps for drift detection


class AntiPatternDetector:
    """Detects anti-patterns in the reflection history at the end of each iteration."""

    def detect(
        self,
        current_reflection: StructuredReflection,
        history: list[RunStep],
        current_score: float,
    ) -> AntiPatternResult:
        """Check for the most severe anti-pattern present. Returns the first match."""
        if self._is_overcorrection(current_reflection, history, current_score):
            return AntiPatternResult(
                pattern=AntiPattern.OVERCORRECT,
                description=(
                    f"Score dropped to {current_score:.2f} after a "
                    f"{current_reflection.confidence.value}-confidence reflection."
                ),
            )
        if self._is_circular(current_reflection, history):
            return AntiPatternResult(
                pattern=AntiPattern.CIRCULAR,
                description="Strategy update is too similar to a previous iteration.",
            )
        if self._is_drift(current_reflection, history):
            return AntiPatternResult(
                pattern=AntiPattern.DRIFT,
                description="Current strategy no longer addresses the original failure type.",
            )
        return AntiPatternResult(pattern=AntiPattern.NONE)

    # ── Circular reasoning ────────────────────────────────────────────────

    def _is_circular(
        self,
        current: StructuredReflection,
        history: list[RunStep],
    ) -> bool:
        """Jaccard similarity between current strategy_update and any previous one."""
        current_tokens = _tokenise(current.strategy_update)
        for step in history:
            if step.reflection is None:
                continue
            prev_tokens = _tokenise(step.reflection.strategy_update)
            if _jaccard(current_tokens, prev_tokens) >= CIRCULAR_SIMILARITY_THRESHOLD:
                return True
        return False

    # ── Overcorrection ────────────────────────────────────────────────────

    def _is_overcorrection(
        self,
        current: StructuredReflection,
        history: list[RunStep],
        current_score: float,
    ) -> bool:
        """Score dropped after the previous reflection had HIGH confidence."""
        if not history:
            return False
        last = history[-1]
        if last.reflection is None:
            return False
        from fdao.types import ConfidenceLevel
        was_high_confidence = last.reflection.confidence == ConfidenceLevel.HIGH
        score_dropped = current_score < last.reward.composite
        return was_high_confidence and score_dropped

    # ── Strategy drift ────────────────────────────────────────────────────

    def _is_drift(
        self,
        current: StructuredReflection,
        history: list[RunStep],
    ) -> bool:
        """Detect when the agent's strategy has wandered away from the root cause.

        Drift is declared when ALL three conditions hold:
          1. Failure type changed from the original (agent is now solving a
             different problem than what it started with)
          2. Score has NOT improved across the last DRIFT_WINDOW steps
             (if scores were trending up, the strategy change is working — not drift)
          3. The current strategy doesn't mention the original root cause keywords

        Using score trend (condition 2) instead of pure Jaccard similarity fixes
        the v1 false-positive: if the agent legitimately pivots and scores go up,
        that's valid exploration, not drift.
        """
        if len(history) < DRIFT_WINDOW:
            return False

        original = next(
            (s.reflection for s in history if s.reflection is not None), None
        )
        if original is None:
            return False

        # Condition 1: failure type has changed from the original
        current_differs = current.failure_type != original.failure_type
        if not current_differs:
            return False

        # Condition 2: scores are not improving across the window
        recent_scores = [s.reward.composite for s in history[-DRIFT_WINDOW:]]
        score_improving = (max(recent_scores) - min(recent_scores)) > 0.05
        if score_improving:
            return False  # improving scores → not drift, it's valid exploration

        # Condition 3: strategy text no longer references original root cause
        original_keywords = _tokenise(original.root_cause)
        current_keywords  = _tokenise(current.strategy_update)
        keyword_overlap   = _jaccard(original_keywords, current_keywords)

        return keyword_overlap < 0.15


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tokenise(text: str) -> set[str]:
    STOP = {"the","a","an","and","or","in","on","to","for","of","is","are","was",
            "it","this","that","not","be","by","as","at","with","from","but"}
    return {w for w in re.findall(r"\b[a-z]{3,}\b", text.lower()) if w not in STOP}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)
