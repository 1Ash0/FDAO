"""Logic and reasoning tasks — deduction, patterns, puzzles, language reasoning.

Validators use exact string matching against a set of accepted answers,
normalised to lowercase with whitespace stripped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fdao.tasks.base import Task
from fdao.types import Difficulty, TaskCategory, ValidationResult


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


@dataclass
class LogicTask(Task):
    """A reasoning task with a short, deterministic answer."""

    task_id: str
    _prompt: str
    accepted_answers: list[str]           # all are normalised at construction
    category: TaskCategory = TaskCategory.QA
    difficulty: Difficulty = Difficulty.MEDIUM
    hint: str = ""                        # shown at end of prompt

    def __post_init__(self) -> None:
        self.accepted_answers = [_normalise(a) for a in self.accepted_answers]

    @property
    def prompt(self) -> str:
        base = self._prompt
        if self.hint:
            base += f"\n\nHint: {self.hint}"
        return base + "\n\nAnswer concisely — one word, number, or short phrase."

    def validate(self, attempt: str) -> ValidationResult:
        cleaned = _normalise(attempt)
        # exact match anywhere in the response (tolerates "The answer is X.")
        for ans in self.accepted_answers:
            if ans in cleaned:
                return ValidationResult(passed=True, score=1.0)
        return ValidationResult(
            passed=False,
            score=0.0,
            details=f"Expected one of {self.accepted_answers!r}, got {cleaned!r}",
        )


LOGIC_TASKS: list[LogicTask] = [
    # ── Deductive syllogisms ─────────────────────────────────────────────
    LogicTask(
        task_id="LOGIC/1",
        _prompt=(
            "All mammals are warm-blooded. All whales are mammals. "
            "Is a whale warm-blooded? Answer yes or no."
        ),
        accepted_answers=["yes"],
        difficulty=Difficulty.EASY,
    ),
    LogicTask(
        task_id="LOGIC/2",
        _prompt=(
            "Some scientists are poets. All poets are creative. "
            "Can we conclude that some scientists are creative? Answer yes or no."
        ),
        accepted_answers=["yes"],
        difficulty=Difficulty.EASY,
    ),
    LogicTask(
        task_id="LOGIC/3",
        _prompt=(
            "If it rains, the ground gets wet. The ground is wet. "
            "Does it necessarily follow that it rained? Answer yes or no."
        ),
        accepted_answers=["no"],
        difficulty=Difficulty.MEDIUM,
        hint="This is the fallacy of affirming the consequent.",
    ),
    # ── Pattern / sequence completion ───────────────────────────────────
    LogicTask(
        task_id="LOGIC/4",
        _prompt="What is the next number in the sequence: 2, 6, 12, 20, 30, ?",
        accepted_answers=["42"],
        difficulty=Difficulty.MEDIUM,
        hint="Look at the differences between consecutive terms.",
    ),
    LogicTask(
        task_id="LOGIC/5",
        _prompt="What is the next number in the sequence: 1, 1, 2, 3, 5, 8, 13, ?",
        accepted_answers=["21"],
        difficulty=Difficulty.EASY,
    ),
    LogicTask(
        task_id="LOGIC/6",
        _prompt="What is the next term: O, T, T, F, F, S, S, E, N, ?",
        accepted_answers=["t", "ten"],
        difficulty=Difficulty.HARD,
        hint="The terms are initials of something.",
    ),
    # ── Spatial / lateral reasoning ─────────────────────────────────────
    LogicTask(
        task_id="LOGIC/7",
        _prompt=(
            "A rooster lays an egg on the peak of a roof. "
            "Which way does the egg roll — left, right, or neither?"
        ),
        accepted_answers=["neither", "roosters don't lay eggs", "it doesn't"],
        difficulty=Difficulty.MEDIUM,
    ),
    LogicTask(
        task_id="LOGIC/8",
        _prompt=(
            "You have a 3-litre jug and a 5-litre jug. No markings. "
            "What is the minimum number of steps (fill/empty/pour) needed to measure exactly 4 litres?"
        ),
        accepted_answers=["6"],
        difficulty=Difficulty.HARD,
    ),
    # ── Word / language reasoning ────────────────────────────────────────
    LogicTask(
        task_id="LOGIC/9",
        _prompt=(
            "The word RACECAR reads the same forwards and backwards. "
            "How many letters are in RACECAR?"
        ),
        accepted_answers=["7"],
        difficulty=Difficulty.EASY,
    ),
    LogicTask(
        task_id="LOGIC/10",
        _prompt=(
            "Re-arrange the letters of LISTEN to form another common English word."
        ),
        accepted_answers=["silent", "enlist", "tinsel", "inlets"],
        difficulty=Difficulty.EASY,
    ),
    LogicTask(
        task_id="LOGIC/11",
        _prompt=(
            "What single word can follow 'fire', 'over', and 'under' "
            "to form three compound words?"
        ),
        accepted_answers=["work", "works"],
        difficulty=Difficulty.MEDIUM,
    ),
    # ── Causal / counterfactual reasoning ────────────────────────────────
    LogicTask(
        task_id="LOGIC/12",
        _prompt=(
            "A study shows that cities with more ice cream sales have more drowning deaths. "
            "Does ice cream cause drowning? Answer yes or no, and name the lurking variable."
        ),
        accepted_answers=["no", "temperature", "summer", "heat", "weather"],
        difficulty=Difficulty.MEDIUM,
    ),
    LogicTask(
        task_id="LOGIC/13",
        _prompt=(
            "A bat and a ball cost $1.10 in total. "
            "The bat costs $1.00 more than the ball. "
            "How much does the ball cost in dollars?"
        ),
        accepted_answers=["0.05", "5 cents", "$0.05", "five cents"],
        difficulty=Difficulty.MEDIUM,
        hint="Don't go with your first instinct.",
    ),
    # ── Constraint satisfaction ──────────────────────────────────────────
    LogicTask(
        task_id="LOGIC/14",
        _prompt=(
            "Alice, Bob, and Carol each wear a different colour: red, blue, or green. "
            "Alice does not wear red. Bob does not wear blue. Carol wears green. "
            "What colour does Alice wear?"
        ),
        accepted_answers=["blue"],
        difficulty=Difficulty.EASY,
    ),
    LogicTask(
        task_id="LOGIC/15",
        _prompt=(
            "Five houses in a row are painted in five different colours. "
            "The green house is immediately to the left of the white house. "
            "The green house owner drinks coffee. The owner of the red house drinks tea. "
            "The person in the middle house drinks milk. "
            "The Norwegian lives in the first house. "
            "The Norwegian lives next to the blue house. "
            "What colour is the first house?"
        ),
        accepted_answers=["yellow", "red"],
        difficulty=Difficulty.HARD,
        hint="This is a simplified Einstein riddle variant.",
    ),
    # ── Algorithmic thinking (no code required) ──────────────────────────
    LogicTask(
        task_id="LOGIC/16",
        _prompt=(
            "You have 8 identical-looking coins. One is slightly heavier than the rest. "
            "Using a balance scale, what is the minimum number of weighings guaranteed "
            "to find the heavy coin?"
        ),
        accepted_answers=["2"],
        difficulty=Difficulty.MEDIUM,
    ),
    LogicTask(
        task_id="LOGIC/17",
        _prompt=(
            "A man has to cross a river with a fox, a chicken, and a bag of grain. "
            "His boat can only carry him and one other item. "
            "The fox eats the chicken if left alone with it; the chicken eats the grain. "
            "What is the minimum number of river crossings needed?"
        ),
        accepted_answers=["7"],
        difficulty=Difficulty.MEDIUM,
    ),
    # ── Meta-reasoning ──────────────────────────────────────────────────
    LogicTask(
        task_id="LOGIC/18",
        _prompt=(
            "I am thinking of a number between 1 and 100. "
            "You may ask yes/no questions. "
            "What is the minimum number of questions guaranteed to find my number?"
        ),
        accepted_answers=["7"],
        difficulty=Difficulty.MEDIUM,
        hint="Think about halving the search space.",
    ),
]
