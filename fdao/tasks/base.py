"""Abstract base class for all FDAO tasks."""

from abc import ABC, abstractmethod

from fdao.types import Difficulty, TaskCategory, ValidationResult


class Task(ABC):
    """Every task must define a prompt and an objective validator.

    The validator is the ground truth — reward signals score against it.
    Keep validators fast and deterministic: no LLM calls inside validate().
    """

    task_id: str
    category: TaskCategory
    difficulty: Difficulty

    @property
    @abstractmethod
    def prompt(self) -> str:
        """What the agent sees. Must not leak the expected answer."""
        ...

    @abstractmethod
    def validate(self, attempt: str) -> ValidationResult:
        """Objective correctness check. Returns partial credit where applicable."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.task_id!r}, difficulty={self.difficulty.value})"
