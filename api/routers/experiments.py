from __future__ import annotations

import asyncio
import os
import sys
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api.db import get_all_experiments, get_experiment_runs
from api.events import bus
from api.schemas import ExperimentSummarySchema, RunSummarySchema

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


class StartExperimentRequest(BaseModel):
    experiment_name: str
    config: str = "experiments/dense_reward.yaml"
    model: str = "llama-3.3-70b-versatile"
    suite: str = "default"          # default | math | code | logic
    max_iterations: int = 5
    max_tasks: int | None = None


@router.get("", response_model=list[ExperimentSummarySchema])
def list_experiments():
    return get_all_experiments()


@router.get("/{experiment_name}", response_model=list[RunSummarySchema])
def get_experiment(experiment_name: str):
    runs = get_experiment_runs(experiment_name)
    if not runs:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return runs


@router.post("")
def start_experiment(req: StartExperimentRequest, background_tasks: BackgroundTasks):
    """Launch an experiment as a background task. Returns run_ids as they start."""
    background_tasks.add_task(_run_experiment, req)
    return {"status": "started", "experiment_name": req.experiment_name}


def _run_experiment(req: StartExperimentRequest) -> None:
    """Runs in a background thread. Emits SSE events via the bus."""
    # Import here so the module loads fast at startup
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from dotenv import load_dotenv
    load_dotenv()

    from fdao.agent import Agent
    from fdao.orchestrator import Orchestrator
    from fdao.persistence.run_logger import RunLogger
    from fdao.reflection.engine import ReflectionEngine
    from fdao.reward.config import load_reward_composer
    from fdao.tasks.humaneval import HUMANEVAL_HARD
    from fdao.tasks.logic_reasoning import LOGIC_TASKS
    from fdao.tasks.math_reasoning import MATH_TASKS

    _HARD_LOGIC = [t for t in LOGIC_TASKS if t.task_id in {"LOGIC/6","LOGIC/8","LOGIC/13","LOGIC/15","LOGIC/17"}]
    SUITES: dict[str, list] = {
        "default": HUMANEVAL_HARD[:4] + MATH_TASKS[:4] + _HARD_LOGIC[:4],
        "math":    MATH_TASKS,
        "code":    HUMANEVAL_HARD,
        "logic":   LOGIC_TASKS,
    }

    tasks = SUITES.get(req.suite, SUITES["default"])
    if req.max_tasks:
        tasks = tasks[: req.max_tasks]

    model = os.environ.get("FDAO_DEFAULT_MODEL", req.model)
    composer = load_reward_composer(req.config)
    agent    = Agent(model=model)
    engine   = ReflectionEngine(model=model)
    logger   = RunLogger(experiment_name=req.experiment_name)

    # Wrap orchestrator to emit SSE events
    orch = _InstrumentedOrchestrator(
        agent=agent,
        reward_composer=composer,
        reflection_engine=engine,
        logger=logger,
        experiment_name=req.experiment_name,
    )

    for task in tasks:
        orch.run(task, max_iterations=req.max_iterations)

    logger.close()


class _InstrumentedOrchestrator:
    """Thin wrapper that emits bus events after each step."""

    def __init__(self, agent, reward_composer, reflection_engine, logger, experiment_name):
        from fdao.orchestrator import Orchestrator
        self._orch = Orchestrator(
            agent=agent,
            reward_composer=reward_composer,
            reflection_engine=reflection_engine,
            logger=logger,
        )
        self._exp = experiment_name

    def run(self, task, max_iterations: int):
        import uuid as _uuid
        run_id = str(_uuid.uuid4())
        result = self._orch.run(task, max_iterations=max_iterations)
        # Emit one event per step retroactively (run already completed)
        for step in result.steps:
            bus.emit(run_id, {
                "event": "step",
                "run_id": run_id,
                "task_id": task.task_id,
                "experiment_name": self._exp,
                "iteration": step.iteration,
                "score_composite": step.reward.composite,
                "score_breakdown": step.reward.breakdown,
                "antipattern": step.antipattern,
                "converged": step.reward.is_solved,
            })
        bus.finish(run_id)
        return result
