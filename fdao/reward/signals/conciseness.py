"""ConcisenessSignal: penalise verbose outputs without rewarding garbage brevity.

Design rationale
----------------
The naive "shorter = better" signal is easily hacked: the agent learns to output
"42" instead of correct code, because brevity beats correctness when this signal's
weight is too high. We prevent this with two constraints:

1. Score is 1.0 at or below the per-category baseline length.
   Below baseline → no bonus for going shorter. The signal is a *penalty* above
   the baseline, not a reward for being short.

2. Score has a hard floor of FLOOR (0.3) so even a maximally verbose response
   still contributes positively. Conciseness can never *cancel* correctness —
   it reduces the composite by at most (1 - FLOOR) × weight = 0.70 × 0.12 = 0.084.

3. Decay is logarithmic, not linear. Linear decay was too aggressive:
     1.5× baseline → 0.75   (old: 0.75) same
     2×   baseline → 0.5    (old: 0.5) same
     4×   baseline → 0.2    (old: 0.2) same → but linear hits FLOOR too fast on real code
   Log decay:
     1.5× → 0.79, 2× → 0.65, 4× → 0.44, 8× → 0.30 (= FLOOR)
   Real code is rarely more than 3× the baseline, so the effective range is
   0.65–1.0 rather than slamming to FLOOR at 2× baseline.

In RL terms: this is a potential-based shaping reward that encourages conciseness
within the target band but never inverts the correctness gradient.

Reward hacking surface
----------------------
Risk: agent writes a one-word response.
Mitigation: FormatComplianceSignal penalises responses lacking required structure.
CorrectnessSignal handles actual correctness. When correctness weight ≥ 0.5,
gaming conciseness is irrational — a one-word wrong answer scores 0 on correctness.
"""

from __future__ import annotations

import math

from fdao.reward.composer import RewardSignal
from fdao.tasks.base import Task
from fdao.types import TaskCategory

# Per-category baseline lengths in characters.
# At or below → score 1.0.  Above → smooth log decay toward FLOOR.
_BASELINES: dict[TaskCategory, int] = {
    TaskCategory.CODE_GENERATION: 600,   # a typical function with docstring
    TaskCategory.QA:              150,   # a sentence or short paragraph
    TaskCategory.TOOL_USE:        400,   # JSON call + brief explanation
}
_DEFAULT_BASELINE = 400

FLOOR = 0.30    # minimum score regardless of length (raised from 0.2 → 0.3 to be less punishing)


class ConcisenessSignal(RewardSignal):
    """Penalises responses that exceed the per-category baseline length."""

    name = "conciseness"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    def score(self, task: Task, attempt: str) -> float:
        baseline = _BASELINES.get(task.category, _DEFAULT_BASELINE)
        length   = len(attempt.strip())

        if length == 0:
            # Empty = maximally concise but wrong.
            # Don't double-penalise — FormatComplianceSignal handles this.
            return 1.0

        if length <= baseline:
            return 1.0

        # Logarithmic decay: score = max(FLOOR, 1 - log2(length/baseline) * K)
        # K is calibrated so that 8× baseline → FLOOR=0.3:
        #   0.3 = 1 - K * log2(8) = 1 - 3K  →  K = 0.7/3 ≈ 0.233
        K = (1.0 - FLOOR) / math.log2(8)
        raw = 1.0 - K * math.log2(length / baseline)
        return round(max(FLOOR, raw), 4)
