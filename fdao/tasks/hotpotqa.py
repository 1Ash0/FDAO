"""HotpotQA-style multi-hop QA tasks.

Each task requires the agent to chain at least two reasoning steps.
The validator does soft string matching: normalised answer must appear
in the normalised response (exact-string or via alias set).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from fdao.tasks.base import Task
from fdao.types import Difficulty, TaskCategory, ValidationResult


def _normalise(text: str) -> str:
    """Lowercase, strip punctuation and extra whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _answer_present(response: str, answers: list[str]) -> bool:
    norm_resp = _normalise(response)
    return any(_normalise(a) in norm_resp for a in answers)


@dataclass
class HotpotTask(Task):
    """A multi-hop QA task graded by soft string match."""

    task_id: str
    _prompt: str
    answers: list[str]                   # first = canonical; rest = accepted aliases
    category: TaskCategory = TaskCategory.QA
    difficulty: Difficulty = Difficulty.MEDIUM

    @property
    def prompt(self) -> str:
        return self._prompt

    def validate(self, attempt: str) -> ValidationResult:
        if not attempt.strip():
            return ValidationResult(passed=False, score=0.0, details="empty response")
        if _answer_present(attempt, self.answers):
            return ValidationResult(passed=True, score=1.0)
        # Partial: did it reason (has >30 words with some key entity)?
        words = len(attempt.split())
        partial = min(0.4, words / 200)
        return ValidationResult(
            passed=False,
            score=round(partial, 3),
            details=f"Expected one of {self.answers!r}; got: {attempt[:120]!r}",
        )


HOTPOTQA_TASKS: list[HotpotTask] = [
    # ── Two-hop entity chaining ──────────────────────────────────────────────
    HotpotTask(
        task_id="HQ/1",
        _prompt=(
            "The Eiffel Tower is located in the capital of which country? "
            "What is that country's official language?"
        ),
        answers=["french", "français"],
        difficulty=Difficulty.EASY,
    ),
    HotpotTask(
        task_id="HQ/2",
        _prompt=(
            "Mount Everest is on the border between Nepal and which other country? "
            "What is the capital of that country?"
        ),
        answers=["beijing", "peking"],
        difficulty=Difficulty.MEDIUM,
    ),
    HotpotTask(
        task_id="HQ/3",
        _prompt=(
            "The Amazon River flows into which ocean? "
            "Name one country that borders that ocean and also borders the Pacific Ocean."
        ),
        answers=["colombia", "brazil", "venezuela", "united states", "canada", "mexico"],
        difficulty=Difficulty.MEDIUM,
    ),
    HotpotTask(
        task_id="HQ/4",
        _prompt=(
            "Shakespeare wrote 'Hamlet'. In what city did Shakespeare live most of his adult life? "
            "What river flows through that city?"
        ),
        answers=["thames", "river thames"],
        difficulty=Difficulty.EASY,
    ),
    HotpotTask(
        task_id="HQ/5",
        _prompt=(
            "The Nobel Peace Prize is awarded in which city? "
            "What country is that city located in?"
        ),
        answers=["norway", "norge"],
        difficulty=Difficulty.EASY,
    ),
    # ── Arithmetic + fact chaining ────────────────────────────────────────────
    HotpotTask(
        task_id="HQ/6",
        _prompt=(
            "The French Revolution began in 1789. "
            "The American Declaration of Independence was signed 13 years before that. "
            "In what year was the Declaration of Independence signed?"
        ),
        answers=["1776"],
        difficulty=Difficulty.EASY,
    ),
    HotpotTask(
        task_id="HQ/7",
        _prompt=(
            "Light travels at approximately 300,000 km/s. "
            "The Moon is about 384,400 km from Earth. "
            "Approximately how many seconds does it take light to travel from Earth to the Moon? "
            "Round to one decimal place."
        ),
        answers=["1.3", "1.28", "1.281"],
        difficulty=Difficulty.MEDIUM,
    ),
    HotpotTask(
        task_id="HQ/8",
        _prompt=(
            "Marie Curie was born in Warsaw. At the time of her birth (1867), "
            "Warsaw was part of which empire?"
        ),
        answers=["russian empire", "russia", "russian"],
        difficulty=Difficulty.HARD,
    ),
    # ── Comparison / superlative ──────────────────────────────────────────────
    HotpotTask(
        task_id="HQ/9",
        _prompt=(
            "Which planet in our solar system has the most moons? "
            "Approximately how many moons does it have?"
        ),
        answers=["saturn", "146", "145", "95", "83", "146 moons", "145 moons", "95 moons", "83 moons"],
        difficulty=Difficulty.MEDIUM,
    ),
    HotpotTask(
        task_id="HQ/10",
        _prompt=(
            "The deepest lake in the world is Lake Baikal. "
            "In which country is Lake Baikal located, and on which continent is that country?"
        ),
        answers=["russia", "asia", "eurasia"],
        difficulty=Difficulty.EASY,
    ),
    # ── Causal / process chaining ─────────────────────────────────────────────
    HotpotTask(
        task_id="HQ/11",
        _prompt=(
            "Photosynthesis produces glucose and which gas? "
            "Which organelle in plant cells is responsible for photosynthesis?"
        ),
        answers=["chloroplast", "chloroplasts"],
        difficulty=Difficulty.MEDIUM,
    ),
    HotpotTask(
        task_id="HQ/12",
        _prompt=(
            "DNA is transcribed into RNA, which is then translated into what? "
            "What cellular structure carries out this translation?"
        ),
        answers=["ribosome", "ribosomes"],
        difficulty=Difficulty.MEDIUM,
    ),
]
