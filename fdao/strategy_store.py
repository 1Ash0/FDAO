"""Accumulates reflections and synthesizes a strategy context for the next attempt.

Two modes:
  - Exploitation: structured context ranked by recency and confidence.
  - Exploration: forced when the same failure type recurs 3+ times with <5%
    score improvement — signals the agent is stuck in a local optimum.

Design mirrors RL exploration/exploitation:
  - Exploitation = follow the highest-confidence strategy that improved score.
  - Exploration  = abandon the current policy; reason from first principles.

Oscillation detection uses:
  - Consecutive same-failure-type threshold (3, not 2 — reduces false triggers)
  - Minimum improvement rate (5%) rather than a simple ≤ comparison
"""

from __future__ import annotations

from fdao.types import ConfidenceLevel, StructuredReflection

MAX_STRATEGY_HISTORY = 4          # keep last 4 reflections in context
OSCILLATION_THRESHOLD = 3         # same failure type N times before forcing exploration
MIN_IMPROVEMENT = 0.05            # must improve by at least 5% over window to avoid exploration


class StrategyStore:
    def __init__(self) -> None:
        self.history:          list[StructuredReflection] = []
        self.scores:           list[float]                = []
        self.current_strategy: str                        = ""
        # Track the best-scoring attempt index for context prioritisation
        self._best_idx: int = 0

    def update(self, reflection: StructuredReflection, score: float = 0.0) -> None:
        self.history.append(reflection)
        self.scores.append(score)
        if score >= self.scores[self._best_idx]:
            self._best_idx = len(self.scores) - 1
        self.current_strategy = self._synthesize()

    def build_context(self) -> str:
        if not self.current_strategy:
            return ""
        n = len(self.history)
        best = self.scores[self._best_idx] if self.scores else 0.0
        trend = self._trend_label()
        header = (
            f"LEARNING PROGRESS — attempt {n}, best score {best:.2f}, trend: {trend}\n\n"
        )
        return header + self.current_strategy

    # ── Oscillation detection ─────────────────────────────────────────────

    def is_oscillating(self) -> bool:
        """True when the agent is stuck: same failure type AND negligible improvement."""
        if len(self.history) < OSCILLATION_THRESHOLD:
            return False

        recent_reflections = self.history[-OSCILLATION_THRESHOLD:]
        same_failure = len({r.failure_type for r in recent_reflections}) == 1

        if not same_failure:
            return False

        # Measure improvement over the window — flat or declining = stuck
        window_scores = self.scores[-OSCILLATION_THRESHOLD:]
        improvement = max(window_scores) - min(window_scores)
        stagnant = improvement < MIN_IMPROVEMENT

        return stagnant

    # ── Context synthesis ─────────────────────────────────────────────────

    def _synthesize(self) -> str:
        if self.is_oscillating():
            return self._exploration_prompt()
        return self._exploitation_prompt()

    def _exploitation_prompt(self) -> str:
        """Structured context: best-scoring strategy first, then recent history."""
        lines: list[str] = []

        # Highlight the highest-scoring prior strategy if it differs from most recent
        best = self.history[self._best_idx]
        best_score = self.scores[self._best_idx]
        most_recent_idx = len(self.history) - 1

        if self._best_idx != most_recent_idx and best_score > 0:
            lines.append(
                f"HIGHEST-SCORING STRATEGY (score {best_score:.2f}, "
                f"confidence {best.confidence.value}):\n"
                f"  {best.strategy_update}"
            )
            lines.append("")

        # Recent attempts (last MAX_STRATEGY_HISTORY)
        recent = list(zip(
            self.history[-MAX_STRATEGY_HISTORY:],
            self.scores[-MAX_STRATEGY_HISTORY:],
        ))
        lines.append("RECENT ATTEMPTS:")
        for i, (r, s) in enumerate(recent, start=max(0, len(self.history) - MAX_STRATEGY_HISTORY)):
            conf_marker = "★" if r.confidence == ConfidenceLevel.HIGH else "·"
            lines.append(
                f"  {conf_marker} attempt {i}: score={s:.2f} [{r.failure_type.value}]\n"
                f"    root cause: {r.root_cause}\n"
                f"    → {r.strategy_update}"
            )

        lines.append("")
        lines.append("Apply the most recent strategy. If confidence is HIGH, follow it closely.")
        return "\n".join(lines)

    def _exploration_prompt(self) -> str:
        """Forced exploration: the current approach is provably stuck."""
        last = self.history[-1]
        window_scores = self.scores[-OSCILLATION_THRESHOLD:]
        score_range = f"{min(window_scores):.2f}–{max(window_scores):.2f}"

        return (
            f"WARNING: Your last {OSCILLATION_THRESHOLD} attempts all produced "
            f"[{last.failure_type.value}] errors with scores {score_range} — "
            f"no meaningful improvement.\n\n"
            f"MOST RECENT ROOT CAUSE: {last.root_cause}\n\n"
            f"REQUIRED ACTION: Do NOT refine your previous solution. "
            f"Your current approach has a structural flaw. "
            f"Start completely from scratch:\n"
            f"  • Re-read the problem statement carefully — have you misunderstood it?\n"
            f"  • If you used a loop, try a different data structure or decomposition.\n"
            f"  • If you solved a sub-problem, reconsider what the full problem requires.\n"
            f"  • Write out what the correct output *must* look like before coding."
        )

    def _trend_label(self) -> str:
        if len(self.scores) < 2:
            return "first attempt"
        delta = self.scores[-1] - self.scores[-2]
        if delta > 0.05:
            return f"↑ improving (+{delta:.2f})"
        if delta < -0.05:
            return f"↓ declining ({delta:.2f})"
        return "→ flat"

    @classmethod
    def empty(cls, prior_strategy: str = "") -> StrategyStore:
        store = cls()
        if prior_strategy:
            store.current_strategy = prior_strategy
        return store
