"""Math reasoning tasks — multi-step word problems with numeric answers.

Validators use tolerance-based float comparison so formatting
differences ("42" vs "42.0" vs "The answer is 42.") don't matter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fdao.tasks.base import Task
from fdao.types import Difficulty, TaskCategory, ValidationResult

_NUM_PATTERN = re.compile(r"-?\d+(?:\.\d+)?")


def _extract_number(text: str) -> float | None:
    """Pull the last number from the agent's response."""
    nums = _NUM_PATTERN.findall(text.strip())
    if not nums:
        return None
    try:
        return float(nums[-1])
    except ValueError:
        return None


@dataclass
class MathTask(Task):
    """A math word problem with a single numeric answer."""

    task_id: str
    _prompt: str
    answer: float
    tolerance: float = 1e-6
    category: TaskCategory = TaskCategory.QA
    difficulty: Difficulty = Difficulty.MEDIUM
    _unit: str = ""                       # e.g. "hours", "dollars" — displayed only

    @property
    def prompt(self) -> str:
        suffix = (
            f"\n\nAnswer with a single number{' in ' + self._unit if self._unit else ''}. "
            "Do not include units or explanation — just the number."
        )
        return self._prompt + suffix

    def validate(self, attempt: str) -> ValidationResult:
        val = _extract_number(attempt)
        if val is None:
            return ValidationResult(passed=False, score=0.0, details="No number found in response.")
        if abs(val - self.answer) <= self.tolerance:
            return ValidationResult(passed=True, score=1.0)
        # partial credit: score based on relative closeness (capped at 0.8)
        if self.answer != 0:
            rel_err = abs(val - self.answer) / abs(self.answer)
            partial = max(0.0, min(0.8, 1.0 - rel_err))
        else:
            partial = 0.0
        return ValidationResult(
            passed=False,
            score=partial,
            details=f"Expected {self.answer}, got {val}",
        )


MATH_TASKS: list[MathTask] = [
    # ── Arithmetic & rates ──────────────────────────────────────────────
    MathTask(
        task_id="MATH/1",
        _prompt=(
            "A train travels 120 km at 60 km/h, then 180 km at 90 km/h. "
            "What is the total travel time in hours?"
        ),
        answer=4.0,
        _unit="hours",
        difficulty=Difficulty.EASY,
    ),
    MathTask(
        task_id="MATH/2",
        _prompt=(
            "A store sells apples for $1.20 each and oranges for $0.80 each. "
            "Alice buys 5 apples and 8 oranges. How much does she pay in dollars?"
        ),
        answer=12.40,
        tolerance=0.01,
        _unit="dollars",
        difficulty=Difficulty.EASY,
    ),
    MathTask(
        task_id="MATH/3",
        _prompt=(
            "Two workers together can complete a job in 6 hours. "
            "Worker A alone takes 10 hours. "
            "How many hours does Worker B need to complete the job alone?"
        ),
        answer=15.0,
        _unit="hours",
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/4",
        _prompt=(
            "A tank fills through pipe A in 4 hours and drains through pipe B in 6 hours. "
            "If both pipes are open simultaneously, how many hours to fill an empty tank?"
        ),
        answer=12.0,
        _unit="hours",
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/5",
        _prompt=(
            "A car depreciates by 15% each year. "
            "If it is worth $20,000 today, what is its value after 3 years? "
            "Round to the nearest dollar."
        ),
        answer=12282.0,
        tolerance=1.0,
        _unit="dollars",
        difficulty=Difficulty.MEDIUM,
    ),
    # ── Combinatorics & probability ─────────────────────────────────────
    MathTask(
        task_id="MATH/6",
        _prompt=(
            "How many distinct 3-letter codes can be formed from the letters A, B, C, D, E "
            "if no letter may be repeated?"
        ),
        answer=60.0,
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/7",
        _prompt=(
            "A bag contains 4 red and 6 blue marbles. "
            "Two marbles are drawn without replacement. "
            "What is the probability (as a decimal) that both are red?"
        ),
        answer=round(4/10 * 3/9, 10),
        tolerance=1e-4,
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/8",
        _prompt=(
            "In how many ways can 5 people be seated in a row such that "
            "two specific people (Alice and Bob) are never adjacent?"
        ),
        answer=72.0,
        difficulty=Difficulty.HARD,
    ),
    # ── Number theory ────────────────────────────────────────────────────
    MathTask(
        task_id="MATH/9",
        _prompt=(
            "What is the sum of all integers from 1 to 100 that are divisible by 3 or 5?"
        ),
        answer=2418.0,
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/10",
        _prompt=(
            "What is the largest prime factor of 13195?"
        ),
        answer=29.0,
        difficulty=Difficulty.HARD,
    ),
    # ── Geometry ────────────────────────────────────────────────────────
    MathTask(
        task_id="MATH/11",
        _prompt=(
            "A right triangle has legs of length 9 and 40. "
            "What is the length of the hypotenuse?"
        ),
        answer=41.0,
        difficulty=Difficulty.EASY,
    ),
    MathTask(
        task_id="MATH/12",
        _prompt=(
            "A cylinder has radius 5 and height 12. "
            "What is its volume? Use π ≈ 3.14159265. "
            "Round to 2 decimal places."
        ),
        answer=round(3.14159265 * 25 * 12, 2),
        tolerance=0.1,
        difficulty=Difficulty.EASY,
    ),
    # ── Multi-step logic with numbers ────────────────────────────────────
    MathTask(
        task_id="MATH/13",
        _prompt=(
            "Alice is 3 times as old as Bob. In 10 years, Alice will be twice as old as Bob. "
            "How old is Alice now?"
        ),
        answer=30.0,
        _unit="years",
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/14",
        _prompt=(
            "A sequence is defined by a(1)=2, a(2)=3, a(n)=a(n-1)+a(n-2) for n>2. "
            "What is a(8)?"
        ),
        answer=34.0,
        difficulty=Difficulty.MEDIUM,
    ),
    MathTask(
        task_id="MATH/15",
        _prompt=(
            "You invest $1000 at 5% annual interest compounded monthly. "
            "What is the value after 2 years? Round to 2 decimal places."
        ),
        answer=round(1000 * (1 + 0.05/12) ** 24, 2),
        tolerance=0.05,
        _unit="dollars",
        difficulty=Difficulty.HARD,
    ),
]
