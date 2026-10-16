"""Phase 3 experiment runner — reflection quality + anti-pattern analysis.

Runs the dense_reward config (best from Phase 2) on a mixed suite and
prints a per-task summary including reflection quality scores and
anti-pattern distribution.

Usage:
    python scripts/run_phase3.py
    python scripts/run_phase3.py --tasks 8 --max-iter 4
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
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

_HARD_LOGIC = [t for t in LOGIC_TASKS if t.task_id in {"LOGIC/6","LOGIC/8","LOGIC/13","LOGIC/15","LOGIC/17"}]
DEFAULT_SUITE = HUMANEVAL_HARD[:4] + MATH_TASKS[:4] + _HARD_LOGIC[:4]


def bar(value: float, width: int = 20) -> str:
    filled = round(value * width)
    return "#" * filled + "." * (width - filled)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=os.environ.get("FDAO_DEFAULT_MODEL", "llama-3.3-70b-versatile"))
    parser.add_argument("--max-iter", type=int, default=5)
    parser.add_argument("--tasks", type=int, default=None)
    parser.add_argument("--config", default="experiments/dense_reward.yaml")
    args = parser.parse_args()

    tasks = DEFAULT_SUITE[: args.tasks] if args.tasks else DEFAULT_SUITE

    composer = load_reward_composer(args.config)
    agent    = Agent(model=args.model)
    engine   = ReflectionEngine(model=args.model)
    logger   = RunLogger(experiment_name="phase3_analysis")
    orch     = Orchestrator(
        agent=agent,
        reward_composer=composer,
        reflection_engine=engine,
        logger=logger,
    )

    print(f"\nFDAO Phase 3 — Reflection Quality + Anti-Pattern Analysis")
    print(f"model={args.model}  config={Path(args.config).stem}  tasks={len(tasks)}  max_iter={args.max_iter}\n")

    all_results = []
    for task in tasks:
        print(f"  {task.task_id:<20}", end=" ", flush=True)
        result = orch.run(task, max_iterations=args.max_iter)
        all_results.append((task, result))

        # Per-task inline summary
        status = "SOLVED" if result.converged else f"score={result.final_score:.2f}"
        n_steps = len(result.steps)
        qualities = [s.reflection_quality for s in result.steps if s.reflection_quality is not None]
        avg_q = sum(qualities) / len(qualities) if qualities else 0.0
        antipatterns = [s.antipattern for s in result.steps if s.antipattern != "none"]
        print(f"{status:<12} iters={n_steps}  avg_quality={avg_q:.1f}  antipatterns={antipatterns or 'none'}")

    logger.close()

    # ── Aggregate stats ───────────────────────────────────────────────────────

    all_steps  = [s for _, r in all_results for s in r.steps]
    reflections = [s for s in all_steps if s.reflection is not None]
    scored      = [s for s in all_steps if s.reflection_quality is not None]

    n_conv  = sum(1 for _, r in all_results if r.converged)
    n_total = len(all_results)
    avg_score = sum(r.final_score for _, r in all_results) / n_total

    quality_dist = Counter(s.reflection_quality for s in scored)
    antipattern_dist = Counter(s.antipattern for s in all_steps if s.antipattern != "none")

    print(f"\n{'='*60}")
    print(f"AGGREGATE RESULTS  ({n_conv}/{n_total} converged  avg_score={avg_score:.3f})")
    print(f"{'='*60}")

    print(f"\nReflection Quality Distribution  (n={len(scored)} scored reflections)")
    for score in [3, 2, 1, 0]:
        count = quality_dist.get(score, 0)
        pct   = count / max(len(scored), 1)
        print(f"  [{score}/3]  {bar(pct, 16)} {count:>3}  ({pct*100:.0f}%)")

    if scored:
        avg_q_all = sum(s.reflection_quality for s in scored) / len(scored)
        print(f"\n  mean quality = {avg_q_all:.2f}/3.00")

        # Quality → convergence correlation
        high_q = [s for s in scored if s.reflection_quality >= 2]
        low_q  = [s for s in scored if s.reflection_quality <= 1]
        # For each step, did the NEXT iteration converge or improve?
        # Approximate: did quality>=2 steps precede a higher final score?
        print(f"\n  High-quality reflections (>=2): {len(high_q)}/{len(scored)}")
        print(f"  Low-quality reflections (<=1):  {len(low_q)}/{len(scored)}")

    print(f"\nAnti-Pattern Distribution  (n={len(all_steps)} total steps)")
    if antipattern_dist:
        for ap, count in antipattern_dist.most_common():
            pct = count / len(all_steps)
            print(f"  {ap:<14}  {bar(pct, 16)} {count:>3}  ({pct*100:.1f}%)")
    else:
        print("  No anti-patterns detected.")

    parse_fails = sum(1 for s in all_steps if s.reflection and s.reflection.parse_failed)
    print(f"\nParse failures:  {parse_fails}/{len(reflections)}")
    print(f"Reward hacked:   {sum(1 for s in all_steps if s.reward.reward_hacked)}/{len(all_steps)}")
    print()


if __name__ == "__main__":
    main()
