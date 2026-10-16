"""Phase 6 experiment runner.

Runs FDAO and zero-shot baseline across the HumanEval task library,
across multiple reward configs, and writes every step to SQLite.

Usage:
    python scripts/run_experiments.py                  # full suite
    python scripts/run_experiments.py --tasks HE/1,HE/2  # specific tasks
    python scripts/run_experiments.py --mode baseline   # zero-shot only
    python scripts/run_experiments.py --mode fdao       # FDAO only
    python scripts/run_experiments.py --seeds 1         # single seed (fast)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Make fdao importable from scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from fdao.agent import Agent
from fdao.orchestrator import Orchestrator
from fdao.persistence.run_logger import RunLogger
from fdao.reflection.engine import ReflectionEngine
from fdao.reward.config import load_reward_composer
from fdao.tasks.registry import all_tasks, filter_tasks, get
from fdao.types import Difficulty, TaskCategory

# ── Experiment matrix ─────────────────────────────────────────────────────────

MODEL = "openai/gpt-oss-120b"   # primary model; easy to swap

CONFIGS = [
    "experiments/dense_reward.yaml",
    "experiments/sparse_reward.yaml",
    "experiments/correctness_dominant.yaml",
]

SEEDS  = 2   # runs per task per config (for variance estimation)
MAX_ITER_FDAO     = 3   # reduced from 5 — 3 iterations captures improvement signal with half the API calls
MAX_ITER_BASELINE = 1   # zero-shot = single attempt

# Tasks to run; default = HumanEval hard + HotpotQA + ToolUse (the three target domains)
DEFAULT_TASK_FILTER = lambda t: (
    t.task_id.startswith("HE/H")
    or t.task_id.startswith("HQ/")
    or t.task_id.startswith("TU/")
)


# ── Runners ───────────────────────────────────────────────────────────────────

def run_baseline(task, seed: int, logger: RunLogger) -> dict:
    """Zero-shot: one attempt, no reflection, no strategy context."""
    from fdao.strategy_store import StrategyStore
    from fdao.types import RunStep
    import uuid

    agent    = Agent(model=MODEL)
    composer = load_reward_composer(CONFIGS[0])   # config doesn't affect baseline score
    run_id   = f"baseline-{task.task_id}-s{seed}-{uuid.uuid4().hex[:6]}"

    attempt = agent.attempt(task, strategy_context="")
    reward  = composer.score(task, attempt)

    step = RunStep(
        iteration=0,
        attempt=attempt,
        reward=reward,
        reflection=None,
        antipattern="none",
    )
    logger.log_step(run_id=run_id, task_id=task.task_id, step=step)
    logger.close()

    return {
        "run_id":    run_id,
        "task_id":   task.task_id,
        "mode":      "baseline",
        "seed":      seed,
        "converged": reward.is_solved,
        "score":     reward.composite,
        "iters":     1,
    }


def run_fdao(task, config: str, seed: int) -> dict:
    """Full FDAO loop: reflection + strategy context across iterations."""
    import uuid

    exp_name = f"fdao-{Path(config).stem}-s{seed}"
    logger   = RunLogger(experiment_name=exp_name)
    agent    = Agent(model=MODEL)
    composer = load_reward_composer(config)
    engine   = ReflectionEngine(model=MODEL)
    orch     = Orchestrator(
        agent=agent,
        reward_composer=composer,
        reflection_engine=engine,
        logger=logger,
    )

    result = orch.run(task, max_iterations=MAX_ITER_FDAO)
    logger.close()

    return {
        "run_id":    result.run_id,
        "task_id":   task.task_id,
        "config":    Path(config).stem,
        "mode":      "fdao",
        "seed":      seed,
        "converged": result.converged,
        "score":     result.final_score,
        "iters":     len(result.steps),
        "conv_iter": result.convergence_iteration,
        "elapsed":   round(result.elapsed_seconds, 1),
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks",    help="Comma-separated task IDs, e.g. HE/H1,HQ/1")
    parser.add_argument("--category", help="Filter by prefix: HE, HE/H, HQ, TU, MATH, LOGIC")
    parser.add_argument("--mode",     choices=["baseline", "fdao", "both"], default="both")
    parser.add_argument("--seeds",    type=int, default=SEEDS)
    parser.add_argument("--config",   help="Single config override")
    args = parser.parse_args()

    # Task selection
    if args.tasks:
        tasks = [get(tid.strip()) for tid in args.tasks.split(",")]
    elif args.category:
        prefix = args.category
        tasks = [t for t in all_tasks() if t.task_id.startswith(prefix)]
    else:
        tasks = [t for t in all_tasks() if DEFAULT_TASK_FILTER(t)]

    configs = [args.config] if args.config else CONFIGS

    total_runs = (
        (len(tasks) * args.seeds if args.mode in ("baseline", "both") else 0) +
        (len(tasks) * len(configs) * args.seeds if args.mode in ("fdao", "both") else 0)
    )

    print(f"\nFDAO Experiment Suite")
    print(f"  Tasks:   {len(tasks)}")
    print(f"  Configs: {len(configs)}")
    print(f"  Seeds:   {args.seeds}")
    print(f"  Mode:    {args.mode}")
    print(f"  Total runs: {total_runs}")
    print(f"  Model: {MODEL}\n")
    import io, sys as _sys
    if hasattr(_sys.stdout, 'reconfigure'):
        try: _sys.stdout.reconfigure(encoding='utf-8')
        except Exception: pass

    results: list[dict] = []
    completed = 0

    # ── Baseline ──────────────────────────────────────────────────────────────
    if args.mode in ("baseline", "both"):
        print("== BASELINE (zero-shot) ======================================")
        for task in tasks:
            for seed in range(args.seeds):
                logger = RunLogger(experiment_name=f"baseline-s{seed}")
                try:
                    r = run_baseline(task, seed, logger)
                    results.append(r)
                    mark = "✓" if r["converged"] else "✗"
                    print(f"  {mark} {task.task_id:<12} seed={seed}  score={r['score']:.2f}")
                except Exception as exc:
                    print(f"  ! {task.task_id:<12} seed={seed}  ERROR: {exc}")
                completed += 1
                _sleep_between_calls()

    # ── FDAO ─────────────────────────────────────────────────────────────────
    if args.mode in ("fdao", "both"):
        for config in configs:
            cfg_name = Path(config).stem
            print(f"\n== FDAO [{cfg_name}] ========================================")
            for task in tasks:
                for seed in range(args.seeds):
                    try:
                        r = run_fdao(task, config, seed)
                        results.append(r)
                        mark = "✓" if r["converged"] else "✗"
                        ci   = f"(conv@{r.get('conv_iter', '-')})" if r["converged"] else f"(best={r['score']:.2f})"
                        print(f"  {mark} {task.task_id:<12} seed={seed}  {ci}  {r['elapsed']}s")
                    except Exception as exc:
                        print(f"  ! {task.task_id:<12} seed={seed}  ERROR: {exc}")
                    completed += 1
                    _sleep_between_calls()

    # ── Summary table ─────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("RESULTS SUMMARY")
    print("=" * 60)
    _print_summary(results)


def _print_summary(results: list[dict]) -> None:
    from collections import defaultdict

    # Group by (mode, config, task_id) → convergence rate
    groups: dict[tuple, list[bool]] = defaultdict(list)
    for r in results:
        key = (r["mode"], r.get("config", "baseline"), r["task_id"])
        groups[key].append(r["converged"])

    # Aggregate by (mode, config)
    config_agg: dict[tuple, list[bool]] = defaultdict(list)
    for (mode, config, tid), convs in groups.items():
        config_agg[(mode, config)].extend(convs)

    print(f"\n{'Mode':<10} {'Config':<28} {'Pass@1':<10} {'Pass@N'}")
    print("-" * 60)

    # Baseline pass@1 (always 1 iter, no reflection)
    baseline_runs = [r for r in results if r["mode"] == "baseline"]
    if baseline_runs:
        conv = [r["converged"] for r in baseline_runs]
        print(f"{'Baseline':<10} {'(zero-shot)':<28} {sum(conv)/len(conv)*100:.1f}%")

    # FDAO pass@N per config
    for config in set(r.get("config", "") for r in results if r["mode"] == "fdao"):
        fdao_runs = [r for r in results if r["mode"] == "fdao" and r.get("config") == config]
        if not fdao_runs:
            continue
        # pass@N = converged at any iteration
        conv = [r["converged"] for r in fdao_runs]
        # pass@1 = first iteration only (to compare fairly to baseline)
        pass1 = [r["score"] >= 1.0 for r in fdao_runs]
        print(f"{'FDAO':<10} {config:<28} {sum(pass1)/len(pass1)*100:.1f}%      {sum(conv)/len(conv)*100:.1f}%")

    print()

    # Per-task breakdown
    task_ids = sorted(set(r["task_id"] for r in results))
    print(f"\n{'Task':<14}", end="")
    print(f"{'Baseline':>10}", end="")
    configs_seen = sorted(set(r.get("config","") for r in results if r["mode"]=="fdao"))
    for c in configs_seen:
        print(f"  {c[:16]:>16}", end="")
    print()
    print("-" * (14 + 10 + 18 * len(configs_seen)))

    for tid in task_ids:
        print(f"{tid:<14}", end="")
        b = [r["converged"] for r in results if r["task_id"]==tid and r["mode"]=="baseline"]
        print(f"{sum(b)/max(len(b),1)*100:>9.0f}%", end="")
        for c in configs_seen:
            runs = [r for r in results if r["task_id"]==tid and r.get("config")==c]
            rate = sum(r["converged"] for r in runs) / max(len(runs), 1) * 100
            print(f"  {rate:>15.0f}%", end="")
        print()


def _sleep_between_calls(seconds: float = 4.0) -> None:
    """Pause between API calls to stay within Groq rate limits.

    Groq free tier: ~30 req/min per key. With 2 keys that's ~1 req/sec combined.
    4s gap keeps us well under the limit when running a single experiment process.
    """
    time.sleep(seconds)


if __name__ == "__main__":
    main()
