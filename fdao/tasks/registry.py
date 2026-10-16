"""Task registry — single source of all tasks, queryable by category/difficulty."""

from __future__ import annotations

from fdao.tasks.base import Task
from fdao.tasks.hotpotqa import HOTPOTQA_TASKS
from fdao.tasks.humaneval import HUMANEVAL_10, HUMANEVAL_HARD
from fdao.tasks.logic_reasoning import LOGIC_TASKS
from fdao.tasks.math_reasoning import MATH_TASKS
from fdao.tasks.tool_use import TOOL_USE_TASKS
from fdao.types import Difficulty, TaskCategory

_ALL: list[Task] = [*HUMANEVAL_10, *HUMANEVAL_HARD, *MATH_TASKS, *LOGIC_TASKS, *HOTPOTQA_TASKS, *TOOL_USE_TASKS]

# Map for quick lookup
_BY_ID: dict[str, Task] = {t.task_id: t for t in _ALL}


def all_tasks() -> list[Task]:
    return list(_ALL)


def get(task_id: str) -> Task:
    if task_id not in _BY_ID:
        raise KeyError(f"Unknown task_id: {task_id!r}")
    return _BY_ID[task_id]


def filter_tasks(
    category: TaskCategory | None = None,
    difficulty: Difficulty | None = None,
    max_tasks: int | None = None,
) -> list[Task]:
    tasks = _ALL
    if category is not None:
        tasks = [t for t in tasks if t.category == category]
    if difficulty is not None:
        tasks = [t for t in tasks if t.difficulty == difficulty]
    if max_tasks is not None:
        tasks = tasks[:max_tasks]
    return tasks


def summary() -> None:
    """Print a table of all registered tasks."""
    print(f"\n{'ID':<14} {'Category':<20} {'Difficulty'}")
    print("-" * 50)
    for t in _ALL:
        print(f"{t.task_id:<14} {t.category.value:<20} {t.difficulty.value}")
    print(f"\nTotal: {len(_ALL)} tasks")
