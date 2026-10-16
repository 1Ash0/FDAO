"""Main loop. Controls iteration budget, stopping criteria, and run logging.

Key improvements over v1:
  - Adaptive patience and iteration budget based on task difficulty
  - Improvement-velocity tracking: exits early if rate of gain < MIN_VELOCITY
  - Divergence detection: high-confidence reflection that causes score drop triggers
    revert to best-seen state (prevents overcorrection spirals)
  - Best-state checkpointing: always returns the highest-scoring step, even if
    the final iteration regresses
"""

from __future__ import annotations

import time
import uuid

from fdao.agent import Agent
from fdao.persistence.run_logger import RunLogger
from fdao.reflection.antipatterns import AntiPattern, AntiPatternDetector
from fdao.reflection.engine import ReflectionEngine
from fdao.reflection.quality import ReflectionQualityScorer
from fdao.reward.composer import RewardComposer
from fdao.strategy_store import StrategyStore
from fdao.tasks.base import Task
from fdao.types import RunResult, RunStep

# Minimum per-iteration score improvement to count as "making progress"
MIN_VELOCITY = 0.02

# Difficulty → (max_iterations, patience)
_DIFFICULTY_CONFIG: dict[str, tuple[int, int]] = {
    "easy":   (3, 2),
    "medium": (5, 3),
    "hard":   (8, 4),
}


class Orchestrator:
    """Drives one episode: task → attempt → reward → reflect → update → repeat.

    Stopping criteria (checked each iteration):
      1. Max iterations reached
      2. Composite score >= solved_threshold
      3. Score hasn't improved in `patience` iterations (early stopping)
      4. Improvement velocity < MIN_VELOCITY for 3+ iterations (stagnation)
      5. HIGH-confidence reflection caused score to drop ≥ 0.10 (divergence guard)
    """

    def __init__(
        self,
        agent: Agent,
        reward_composer: RewardComposer,
        reflection_engine: ReflectionEngine,
        logger: RunLogger,
        solved_threshold: float = 1.0,
        patience: int | None = None,          # None = adapt to task difficulty
        use_llm_quality_judge: bool = False,
    ) -> None:
        self.agent             = agent
        self.reward_composer   = reward_composer
        self.reflection_engine = reflection_engine
        self.logger            = logger
        self.solved_threshold  = solved_threshold
        self._patience_override = patience
        self._quality_scorer   = ReflectionQualityScorer(use_llm_judge=use_llm_quality_judge)
        self._antipattern_detector = AntiPatternDetector()

    def run(self, task: Task, max_iterations: int | None = None) -> RunResult:
        # Adapt budget and patience to task difficulty
        diff_key = task.difficulty.value if hasattr(task.difficulty, "value") else str(task.difficulty)
        default_max, default_patience = _DIFFICULTY_CONFIG.get(diff_key, (5, 3))
        max_iter = max_iterations if max_iterations is not None else default_max
        patience = self._patience_override if self._patience_override is not None else default_patience

        run_id              = str(uuid.uuid4())
        strategy            = StrategyStore.empty()
        steps:  list[RunStep] = []
        no_improve_count    = 0
        best_score          = -1.0
        best_step_idx       = 0          # index into `steps` of highest-scoring attempt
        convergence_iteration: int | None = None
        start               = time.monotonic()
        velocity_history:   list[float] = []

        for i in range(max_iter):
            context = strategy.build_context()
            attempt = self.agent.attempt(task, context)
            reward  = self.reward_composer.score(task, attempt)

            reflection = None
            antipattern = AntiPattern.NONE

            # Skip reflection when correctness is perfect — calling it would
            # invent problems on a passing solution, causing the agent to
            # change working code. Reflection only fires when the answer is
            # objectively wrong (correctness < 1.0).
            correctness = reward.breakdown.get("correctness", reward.composite)
            should_reflect = not reward.is_solved and correctness < 1.0

            if should_reflect:
                reflection = self.reflection_engine.reflect(
                    task=task,
                    attempt=attempt,
                    reward=reward,
                    history=steps,
                )
                ap_result = self._antipattern_detector.detect(
                    current_reflection=reflection,
                    history=steps,
                    current_score=reward.composite,
                )
                antipattern = ap_result.pattern
                strategy.update(reflection, score=reward.composite)

            # If correctness=1.0 but composite isn't (auxiliary signal drag),
            # still treat as solved — the answer is objectively correct.
            if correctness >= 1.0 and not reward.is_solved:
                reward = type(reward)(
                    composite=reward.composite,
                    breakdown=reward.breakdown,
                    is_solved=True,
                    reward_hacked=reward.reward_hacked,
                )

            step = RunStep(
                iteration=i,
                attempt=attempt,
                reward=reward,
                reflection=reflection,
                antipattern=antipattern.value,
            )

            # Retroactively score the previous step's reflection quality
            if len(steps) > 0 and steps[-1].reflection is not None:
                quality = self._quality_scorer.score(
                    prev_step=steps[-1],
                    next_step=step,
                )
                steps[-1].reflection_quality = quality.total
                self.logger.update_quality(
                    run_id=run_id,
                    iteration=steps[-1].iteration,
                    quality=quality.total,
                    antipattern=steps[-1].antipattern,
                )

            steps.append(step)
            self.logger.log_step(run_id=run_id, task_id=task.task_id, step=step)

            # ── Stopping criteria ─────────────────────────────────────────

            # 1. Solved
            if reward.is_solved:
                convergence_iteration = i
                best_step_idx = len(steps) - 1
                break

            # 2. Track best
            delta = reward.composite - best_score
            if reward.composite > best_score:
                best_score    = reward.composite
                best_step_idx = len(steps) - 1
                no_improve_count = 0
            else:
                no_improve_count += 1

            # 3. Patience (no improvement)
            if no_improve_count >= patience:
                break

            # 4. Velocity stagnation: track per-iteration improvement
            if i > 0:
                velocity_history.append(delta)
                if len(velocity_history) >= 3:
                    avg_velocity = sum(velocity_history[-3:]) / 3
                    if avg_velocity < MIN_VELOCITY and no_improve_count >= 2:
                        break  # stagnation detected

            # 5. Divergence guard: HIGH-confidence reflection caused sharp drop
            if (
                len(steps) >= 2
                and steps[-2].reflection is not None
                and getattr(steps[-2].reflection, "confidence", None) is not None
            ):
                from fdao.types import ConfidenceLevel
                prev_conf = steps[-2].reflection.confidence
                score_drop = steps[-2].reward.composite - reward.composite
                if prev_conf == ConfidenceLevel.HIGH and score_drop >= 0.10:
                    # Overcorrection: HIGH-confidence reflection made things worse
                    # Do not continue — log and exit with best state
                    break

        elapsed = time.monotonic() - start

        # Always return from the highest-scoring step (best-state checkpoint)
        final_step = steps[best_step_idx]

        return RunResult(
            run_id=run_id,
            task_id=task.task_id,
            steps=steps,
            converged=convergence_iteration is not None,
            final_score=final_step.reward.composite,
            convergence_iteration=convergence_iteration,
            elapsed_seconds=elapsed,
        )
