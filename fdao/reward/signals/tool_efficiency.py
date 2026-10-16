"""ToolEfficiencySignal: penalise unnecessary tool calls in agentic tasks.

Stub — implemented in Phase 5 when tool-use tasks are added.
Returns 1.0 (neutral) for all non-tool-use tasks.
"""

from fdao.reward.composer import RewardSignal
from fdao.tasks.base import Task
from fdao.types import TaskCategory


class ToolEfficiencySignal(RewardSignal):
    name = "tool_efficiency"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    def score(self, task: Task, attempt: str) -> float:
        if task.category != TaskCategory.TOOL_USE:
            return 1.0
        # Phase 5: count tool calls in attempt, score against minimum required.
        raise NotImplementedError("ToolEfficiencySignal is implemented in Phase 5.")
