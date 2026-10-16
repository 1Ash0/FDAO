from __future__ import annotations

from fastapi import APIRouter

from api.db import get_tasks_from_db
from api.schemas import TaskInfoSchema

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks():
    """Tasks seen in the DB, with run counts and average scores."""
    return get_tasks_from_db()


@router.get("/library")
def task_library():
    """All available tasks from the task registry (not just ones that have been run)."""
    from fdao.tasks.humaneval import HUMANEVAL_HARD
    from fdao.tasks.logic_reasoning import LOGIC_TASKS
    from fdao.tasks.math_reasoning import MATH_TASKS

    all_tasks = HUMANEVAL_HARD + MATH_TASKS + LOGIC_TASKS
    return [
        {
            "task_id": t.task_id,
            "category": t.category.value,
            "difficulty": t.difficulty.value,
            "description": t.prompt[:200],
        }
        for t in all_tasks
    ]
