"""StabilitySignal: penalise outputs that vary wildly across semantically identical prompts.

This signal requires multiple samples for the same task, so it cannot be computed
inline during a single run. Instead it is computed POST-HOC from the run log:
run the same task N times with the same strategy context, measure output variance.

During a live run, this signal returns 1.0 (neutral) as a placeholder.
The real stability score is computed by scripts/analyze_results.py after the run.

In RL terms: this measures policy variance — a stable policy has low variance
across identical states. High variance is a symptom of the agent not having
actually learned a strategy, just getting lucky occasionally.
"""

from fdao.reward.composer import RewardSignal
from fdao.tasks.base import Task


class StabilitySignal(RewardSignal):
    """Placeholder during live runs. Real score is computed post-hoc."""

    name = "stability"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    def score(self, task: Task, attempt: str) -> float:
        # Returns 1.0 during live run — neutral, does not affect composite.
        # Post-hoc analysis computes the real stability score from the DB.
        return 1.0
