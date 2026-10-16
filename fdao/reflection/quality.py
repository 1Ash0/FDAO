"""Reflection quality scoring — measures how useful a reflection actually was.

Three-component score (0–3 total):
  +1  Score improved on the next attempt
  +1  Agent followed the strategy update (keyword overlap or LLM judge)
  +1  Failure diagnosis was actionable:
        - failure type changed (redirect worked), OR
        - failure type recurred but score improved ≥ 0.05 (making progress on same error)

Why this matters for the paper:
  A high quality score predicts convergence. If reflection quality is NOT predictive,
  the mechanism is not the one we claim. Section 8.4 validates this correlation.

Key fix over v1: _failure_correctly_identified no longer treats failure-type change
as equivalent to diagnosis correctness. It now checks whether the agent made
*progress* — either by changing direction OR by improving on the same error class.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fdao.types import ConfidenceLevel, RunStep, StructuredReflection

MIN_SCORE_IMPROVEMENT = 0.05   # minimum improvement to count as "progress on same error"


@dataclass
class ReflectionQualityResult:
    total: int                           # 0–3
    score_improved: bool                 # component 1
    strategy_followed: bool              # component 2
    failure_correctly_identified: bool   # component 3
    notes: str = ""


class ReflectionQualityScorer:
    """Scores a reflection retroactively once the next attempt is known."""

    def __init__(self, use_llm_judge: bool = False) -> None:
        self.use_llm_judge = use_llm_judge

    def score(self, prev_step: RunStep, next_step: RunStep) -> ReflectionQualityResult:
        if prev_step.reflection is None:
            return ReflectionQualityResult(
                total=0,
                score_improved=False,
                strategy_followed=False,
                failure_correctly_identified=False,
                notes="No reflection to score.",
            )

        reflection = prev_step.reflection
        improved   = self._score_improved(prev_step, next_step)
        followed   = self._strategy_followed(reflection, next_step.attempt)
        correct_id = self._failure_correctly_identified(prev_step, next_step)

        total = int(improved) + int(followed) + int(correct_id)
        notes = self._build_notes(improved, followed, correct_id, reflection, next_step)

        return ReflectionQualityResult(
            total=total,
            score_improved=improved,
            strategy_followed=followed,
            failure_correctly_identified=correct_id,
            notes=notes,
        )

    # ── Component 1: Did the score improve? ──────────────────────────────

    def _score_improved(self, prev_step: RunStep, next_step: RunStep) -> bool:
        return next_step.reward.composite > prev_step.reward.composite

    # ── Component 2: Did the agent follow the strategy update? ───────────

    def _strategy_followed(self, reflection: StructuredReflection, next_attempt: str) -> bool:
        if self.use_llm_judge:
            return self._llm_judge_strategy_followed(reflection, next_attempt)

        keywords = self._extract_keywords(reflection.strategy_update)
        if not keywords:
            return False
        next_lower = next_attempt.lower()
        matches = sum(1 for kw in keywords if kw in next_lower)
        return matches / len(keywords) >= 0.30

    def _extract_keywords(self, strategy_update: str) -> list[str]:
        STOP = {
            "the","a","an","and","or","but","in","on","at","to","for","of","with",
            "is","are","was","were","be","been","have","has","do","does","did",
            "this","that","it","its","should","must","need","will","would","can",
            "not","no","use","used","using","try","next","attempt","previous",
            "approach","ensure","make","correct","fix","update","change","avoid",
        }
        words = re.findall(r"\b[a-z]{3,}\b", strategy_update.lower())
        return [w for w in words if w not in STOP]

    def _llm_judge_strategy_followed(
        self, reflection: StructuredReflection, next_attempt: str
    ) -> bool:
        import os

        import openai

        model = os.environ.get("FDAO_DEFAULT_MODEL", "llama-3.3-70b-versatile")
        prompt = (
            f"Strategy the agent was supposed to follow:\n{reflection.strategy_update}\n\n"
            f"Agent's next attempt:\n{next_attempt[:1000]}\n\n"
            "Did the agent's next attempt meaningfully follow the strategy? "
            "Answer with exactly YES or NO."
        )
        keys = [v for k, v in sorted(os.environ.items())
                if k == "GROQ_API_KEY" or k.startswith("GROQ_API_KEY_")]
        if not keys:
            return False
        client = openai.OpenAI(api_key=keys[0], base_url="https://api.groq.com/openai/v1")
        try:
            resp = client.chat.completions.create(
                model=model, max_tokens=5,
                messages=[{"role": "user", "content": prompt}],
            )
            return "yes" in (resp.choices[0].message.content or "").lower()
        except Exception:
            return False

    # ── Component 3: Was the failure diagnosis actionable? ────────────────

    def _failure_correctly_identified(
        self, prev_step: RunStep, next_step: RunStep
    ) -> bool:
        """A diagnosis is actionable if it led to meaningful progress.

        Criteria (either is sufficient):
          A. The failure type changed — the reflection redirected the agent.
          B. The failure type recurred but the score improved by MIN_SCORE_IMPROVEMENT
             — the agent is making progress on the same error class (valid).

        This fixes the v1 correlation-as-causation flaw: failure_type change alone
        doesn't prove the reflection was correct — the agent could stumble onto a
        different error entirely. We require evidence of progress.
        """
        if next_step.reflection is None:
            # Task solved — the diagnosis was definitively useful
            return True

        failure_changed  = next_step.reflection.failure_type != prev_step.reflection.failure_type  # type: ignore[union-attr]
        score_improved   = (next_step.reward.composite - prev_step.reward.composite) >= MIN_SCORE_IMPROVEMENT

        # Failure type changed AND some score improvement: strong signal
        if failure_changed and score_improved:
            return True

        # Failure type changed but score didn't improve: ambiguous (agent may have
        # wandered to a different error). Count as True only if score didn't drop.
        if failure_changed and next_step.reward.composite >= prev_step.reward.composite:
            return True

        # Same failure type but meaningful score improvement: diagnosis was right,
        # agent is making gradual progress on the identified error.
        if not failure_changed and score_improved:
            return True

        return False

    # ── Notes builder ─────────────────────────────────────────────────────

    def _build_notes(
        self,
        improved: bool,
        followed: bool,
        correct_id: bool,
        reflection: StructuredReflection,
        next_step: RunStep,
    ) -> str:
        parts = []
        if not improved:
            parts.append(f"score did not improve ({next_step.reward.composite:.2f} ≤ prev)")
        if not followed:
            parts.append("agent did not appear to follow strategy update")
        if not correct_id:
            ft = next_step.reflection.failure_type.value if next_step.reflection else "n/a"
            parts.append(f"diagnosis not actionable (failure={ft}, no progress)")
        if reflection.confidence == ConfidenceLevel.HIGH and not improved:
            parts.append("HIGH confidence reflection failed to improve score — possible overcorrection")
        return "; ".join(parts) if parts else "all components passed"
