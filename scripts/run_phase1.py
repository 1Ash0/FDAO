"""Phase 1 milestone runner — supports code, math, and logic tasks.

Usage:
    python scripts/run_phase1.py                            # mixed hard set (default)
    python scripts/run_phase1.py --suite easy               # easy tasks from all categories
    python scripts/run_phase1.py --suite code               # hard HumanEval only
    python scripts/run_phase1.py --suite math               # math tasks only
    python scripts/run_phase1.py --suite logic              # logic tasks only
    python scripts/run_phase1.py --suite all                # everything
    python scripts/run_phase1.py --model llama-3.3-70b-versatile --max-iter 5 --tasks 10
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv  # type: ignore[import]
load_dotenv()

from fdao.agent import Agent
from fdao.orchestrator import Orchestrator
from fdao.persistence.run_logger import RunLogger
from fdao.reflection.engine import ReflectionEngine
from fdao.reward.composer import RewardComposer
from fdao.reward.signals.correctness import CorrectnessSignal
from fdao.tasks.humaneval import HUMANEVAL_HARD
from fdao.tasks.logic_reasoning import LOGIC_TASKS
from fdao.tasks.math_reasoning import MATH_TASKS
from fdao.tasks.registry import filter_tasks
from fdao.types import Difficulty, TaskCategory

_HARD_LOGIC = [t for t in LOGIC_TASKS if t.task_id in {"LOGIC/6","LOGIC/8","LOGIC/13","LOGIC/15","LOGIC/17"}]

SUITES = {
    "default": HUMANEVAL_HARD[:5] + MATH_TASKS[:3] + _HARD_LOGIC,
    "easy":    filter_tasks(difficulty=Difficulty.EASY),
    "hard":    filter_tasks(difficulty=Difficulty.HARD),
    "code":    HUMANEVAL_HARD,
    "math":    MATH_TASKS,
    "logic":   LOGIC_TASKS,
    "all":     filter_tasks(),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model",
        default=os.environ.get("FDAO_DEFAULT_MODEL", "claude-sonnet-4-6"),
    )
    parser.add_argument("--max-iter", type=int, default=5)
    parser.add_argument(
        "--tasks", type=int, default=None,
        help="Limit number of tasks (default: all in suite)",
    )
    parser.add_argument(
        "--suite", default="default",
        choices=list(SUITES.keys()),
        help="Task suite to run",
    )
    args = parser.parse_args()

    agent = Agent(model=args.model)
    reward_composer = RewardComposer(signals=[CorrectnessSignal(weight=1.0)])
    reflection_engine = ReflectionEngine(model=args.model)
    logger = RunLogger()

    orchestrator = Orchestrator(
        agent=agent,
        reward_composer=reward_composer,
        reflection_engine=reflection_engine,
        logger=logger,
    )

    tasks = SUITES[args.suite]
    if args.tasks:
        tasks = tasks[: args.tasks]

    print(f"\nFDAO Phase 1 — model={args.model}  suite={args.suite}  max_iter={args.max_iter}\n")
    col_w = args.max_iter * 6
    print(f"{'Task':<14} {'Cat':<8} {'Conv?':<7}", end="")
    for i in range(args.max_iter):
        print(f" it{i}  ", end="")
    print()
    print("-" * (14 + 8 + 7 + args.max_iter * 6))

    results = []
    for task in tasks:
        result = orchestrator.run(task, max_iterations=args.max_iter)
        results.append(result)

        scores = {s.iteration: s.reward.composite for s in result.steps}
        conv = "YES" if result.converged else "no"
        cat = task.category.value[:7]
        print(f"{task.task_id:<14} {cat:<8} {conv:<7}", end="")
        for i in range(args.max_iter):
            score = scores.get(i)
            print(f" {score:.2f} " if score is not None else "  —   ", end="")
        print()

    print()
    n_conv = sum(1 for r in results if r.converged)
    avg = sum(r.final_score for r in results) / len(results)
    parse_fails = sum(
        1 for r in results
        for s in r.steps
        if s.reflection and s.reflection.parse_failed
    )
    print(f"Converged:      {n_conv}/{len(results)}")
    print(f"Avg final score:{avg:.3f}")
    print(f"Parse failures: {parse_fails}")
    logger.close()


if __name__ == "__main__":
    main()
