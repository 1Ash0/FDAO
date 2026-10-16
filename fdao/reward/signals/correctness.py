"""CorrectnessSignal: binary pass/fail via the task's own validator.

Deliberately binary (0 or 1) — not partial credit. This is the hard ground-truth
signal. Use ProgressSignal alongside it if you want a soft gradient.

In RL terms: this is the sparse reward. Clean, unambiguous, but slow to converge
when the agent is far from the correct answer.
"""

from fdao.reward.composer import RewardSignal
from fdao.tasks.base import Task


class CorrectnessSignal(RewardSignal):
    name = "correctness"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    def score(self, task: Task, attempt: str) -> float:
        result = task.validate(attempt)
        return 1.0 if result.passed else 0.0
