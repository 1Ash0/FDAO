"""Pydantic response models for the API. Mirrors the DB schema."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class ReflectionSchema(BaseModel):
    failure_type: str
    root_cause: str
    what_worked: str
    strategy_update: str
    confidence: str


class StepSchema(BaseModel):
    iteration: int
    attempt: str
    score_composite: float
    score_breakdown: dict[str, float]
    reward_hacked: bool
    reflection: ReflectionSchema | None
    reflection_parse_failed: bool
    reflection_quality: int | None
    antipattern: str
    timestamp: str


class RunSummarySchema(BaseModel):
    run_id: str
    task_id: str
    experiment_name: str
    n_iterations: int
    final_score: float
    converged: bool
    reward_hacked_count: int
    antipattern_count: int
    timestamp: str   # first step timestamp


class RunDetailSchema(BaseModel):
    run_id: str
    task_id: str
    experiment_name: str
    steps: list[StepSchema]
    final_score: float
    converged: bool


class ExperimentSummarySchema(BaseModel):
    experiment_name: str
    n_runs: int
    n_tasks: int
    converged: int
    avg_final_score: float
    avg_reflection_quality: float | None
    reward_hacked_total: int
    antipattern_breakdown: dict[str, int]


class AggregateMetricsSchema(BaseModel):
    total_runs: int
    total_steps: int
    overall_convergence_rate: float
    avg_final_score: float
    avg_reflection_quality: float | None
    parse_failure_rate: float
    reward_hacking_rate: float
    antipattern_breakdown: dict[str, int]


class TaskInfoSchema(BaseModel):
    task_id: str
    category: str
    difficulty: str
    description: str


class SSEStepEvent(BaseModel):
    event: str = "step"
    run_id: str
    task_id: str
    iteration: int
    score_composite: float
    score_breakdown: dict[str, float]
    antipattern: str
    converged: bool
