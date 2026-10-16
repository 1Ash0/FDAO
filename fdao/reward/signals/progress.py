"""ProgressSignal: partial credit from the task's own validator.

Distinct from CorrectnessSignal (which is binary). ProgressSignal uses
ValidationResult.score which is continuous in [0, 1] — tasks can award
partial credit for being close (e.g. MathTask awards based on relative error).

In RL terms: this is dense reward shaping on top of the sparse correctness signal.
It gives the agent a gradient signal even when the binary correctness is 0,
which speeds convergence but introduces reward shaping risks (see ConcisenessSignal).
"""

from fdao.reward.composer import RewardSignal
from fdao.tasks.base import Task


class ProgressSignal(RewardSignal):
    name = "progress"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    def score(self, task: Task, attempt: str) -> float:
        result = task.validate(attempt)
        return float(result.score)
