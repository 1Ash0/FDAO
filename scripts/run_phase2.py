"""Phase 2 experiment runner — compare reward configs side by side.

Runs the same task suite under multiple reward configurations and prints
a comparison table. Also flags reward hacking instances.

Usage:
    python scripts/run_phase2.py                             # all 4 configs, default suite
    python scripts/run_phase2.py --suite math --tasks 10
    python scripts/run_phase2.py --hacking-demo              # runs the broken config only
    python scripts/run_phase2.py --config experiments/dense_reward.yaml
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
from fdao.reward.config import load_reward_composer
from fdao.tasks.humaneval import HUMANEVAL_HARD
from fdao.tasks.logic_reasoning import LOGIC_TASKS
from fdao.tasks.math_reasoning import MATH_TASKS
from fdao.tasks.registry import filter_tasks
from fdao.types import Difficulty

_HARD_LOGIC = [t for t in LOGIC_TASKS if t.task_id in {"LOGIC/6","LOGIC/8","LOGIC/13","LOGIC/15","LOGIC/17"}]

SUITES = {
    "default": HUMANEVAL_HARD[:5] + MATH_TASKS[:5] + _HARD_LOGIC[:3],
    "math":    MATH_TASKS,
    "code":    HUMANEVAL_HARD,
    "logic":   LOGIC_TASKS,
    "hard":    filter_tasks(difficulty=Difficulty.HARD),
}

COMPARISON_CONFIGS = [
    "experiments/sparse_reward.yaml",
    "experiments/medium_reward.yaml",
    "experiments/dense_reward.yaml",
    "experiments/correctness_dominant.yaml",
]


def run_config(
    config_path: str,
    tasks: list,
    model: str,
    max_iter: int,
) -> dict:
    composer = load_reward_composer(config_path)
    exp_name = Path(config_path).stem
    agent = Agent(model=model)
    engine = ReflectionEngine(model=model)
    logger = RunLogger(experiment_name=exp_name)

    orch = Orchestrator(
        agent=agent,
        reward_composer=composer,
        reflection_engine=engine,
        logger=logger,
    )

    results = []
    hacking_instances = []

    for task in tasks:
        result = orch.run(task, max_iterations=max_iter)
        results.append(result)
        # Collect reward hacking instances
        for step in result.steps:
            if step.reward.reward_hacked:
                hacking_instances.append({
                    "task": task.task_id,
                    "iteration": step.iteration,
                    "composite": step.reward.composite,
                    "breakdown": step.reward.breakdown,
                })

    logger.close()

    n_conv = sum(1 for r in results if r.converged)
    avg_final = sum(r.final_score for r in results) / len(results)
    avg_iters = sum(
        r.convergence_iteration + 1 for r in results if r.converged
    ) / max(n_conv, 1)
    parse_fails = sum(
        1 for r in results for s in r.steps
        if s.reflection and s.reflection.parse_failed
    )

    return {
        "config": exp_name,
        "n_tasks": len(results),
        "converged": n_conv,
        "avg_final": avg_final,
        "avg_iters_to_conv": avg_iters,
        "parse_fails": parse_fails,
        "hacking_instances": hacking_instances,
    }


def print_comparison(runs: list[dict]) -> None:
    print(f"\n{'Config':<26} {'Conv':<8} {'Avg Score':<12} {'Avg Iters':<12} {'Hacked':<8} {'Parse Fails'}")
    print("-" * 80)
    for r in runs:
        hacked = len(r["hacking_instances"])
        print(
            f"{r['config']:<26} "
            f"{r['converged']}/{r['n_tasks']:<5} "
            f"{r['avg_final']:<12.3f} "
            f"{r['avg_iters_to_conv']:<12.1f} "
            f"{hacked:<8} "
            f"{r['parse_fails']}"
        )

    # Print hacking instances
    all_hacking = [
        (r["config"], h) for r in runs for h in r["hacking_instances"]
    ]
    if all_hacking:
        print(f"\n{'='*60}")
        print("REWARD HACKING INSTANCES")
        print(f"{'='*60}")
        for config, h in all_hacking:
            breakdown_str = "  ".join(f"{k}={v:.2f}" for k, v in h["breakdown"].items())
            print(f"  [{config}] {h['task']} iter{h['iteration']}: composite={h['composite']:.3f}  {breakdown_str}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("FDAO_DEFAULT_MODEL", "claude-sonnet-4-6"))
    parser.add_argument("--max-iter", type=int, default=5)
    parser.add_argument("--tasks", type=int, default=None)
    parser.add_argument("--suite", default="default", choices=list(SUITES.keys()))
    parser.add_argument("--config", default=None, help="Run a single config file")
    parser.add_argument("--hacking-demo", action="store_true", help="Run only the hacking demo config")
    args = parser.parse_args()

    tasks = SUITES[args.suite]
    if args.tasks:
        tasks = tasks[: args.tasks]

    if args.hacking_demo:
        configs = ["experiments/reward_hacking_demo.yaml"]
    elif args.config:
        configs = [args.config]
    else:
        configs = COMPARISON_CONFIGS

    print(f"\nFDAO Phase 2 — Reward Composer Comparison")
    print(f"model={args.model}  suite={args.suite}  tasks={len(tasks)}  max_iter={args.max_iter}")
    print(f"configs: {[Path(c).stem for c in configs]}")

    runs = []
    for config_path in configs:
        print(f"\n  Running {Path(config_path).stem}...", end=" ", flush=True)
        result = run_config(config_path, tasks, args.model, args.max_iter)
        runs.append(result)
        print(f"done  ({result['converged']}/{result['n_tasks']} converged)")

    print_comparison(runs)


if __name__ == "__main__":
    main()
