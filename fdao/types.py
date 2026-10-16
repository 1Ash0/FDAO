"""Shared data types used across all FDAO modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class FailureType(str, Enum):
    LOGIC_ERROR = "logic_error"
    FORMAT_ERROR = "format_error"
    MISUNDERSTANDING = "misunderstanding"
    TOOL_MISUSE = "tool_misuse"
    OVERCOMPLICATION = "overcomplication"
    PARTIAL_SOLUTION = "partial_solution"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskCategory(str, Enum):
    CODE_GENERATION = "code_generation"
    QA = "qa"
    TOOL_USE = "tool_use"


class Difficulty(str, Enum):
    EASY = "easy"      # >70% zero-shot pass rate
    MEDIUM = "medium"  # 30-70%
    HARD = "hard"      # <30%


@dataclass
class ValidationResult:
    passed: bool
    score: float          # partial credit in [0, 1]
    details: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RewardResult:
    composite: float                      # weighted sum, always in [0, 1]
    breakdown: dict[str, float]           # signal_name -> score
    is_solved: bool = False
    reward_hacked: bool = False           # composite high but correctness = 0

    def __post_init__(self) -> None:
        assert 0.0 <= self.composite <= 1.0, f"Composite reward {self.composite} out of [0,1]"


@dataclass
class StructuredReflection:
    failure_type: FailureType
    root_cause: str
    what_worked: str
    strategy_update: str
    confidence: ConfidenceLevel
    raw: str = ""                         # full unparsed LLM output
    parse_failed: bool = False            # True if any field fell back to default


@dataclass
class RunStep:
    iteration: int
    attempt: str
    reward: RewardResult
    reflection: StructuredReflection | None
    reflection_quality: int | None = None      # 0–3, computed retroactively
    antipattern: str = "none"                  # AntiPattern.value
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RunResult:
    run_id: str
    task_id: str
    steps: list[RunStep]
    converged: bool
    final_score: float
    convergence_iteration: int | None     # first iteration where is_solved=True
    elapsed_seconds: float = 0.0
