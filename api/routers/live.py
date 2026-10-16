"""Live run endpoint — streams a single task execution via SSE.

POST /api/live  { prompt, model, config, max_iterations }
→ SSE stream of step events as the agent runs.
"""

from __future__ import annotations

import os
import sys
import threading
import uuid
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.events import bus, format_sse

router = APIRouter(prefix="/api/live", tags=["live"])


class LiveRunRequest(BaseModel):
    prompt: str
    model: str = "llama-3.3-70b-versatile"
    config: str = "experiments/dense_reward.yaml"
    max_iterations: int = 4


@router.post("")
async def run_live(req: LiveRunRequest):
    run_id = str(uuid.uuid4())

    async def generate():
        yield format_sse({"event": "start", "run_id": run_id, "prompt": req.prompt[:120]})

        t = threading.Thread(target=_execute, args=(run_id, req), daemon=True)
        t.start()

        async for event in bus.subscribe(run_id):
            yield format_sse(event)

        yield format_sse({"event": "done", "run_id": run_id})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Category auto-detection ───────────────────────────────────────────────────

def _detect_task_category(prompt: str):
    """Infer task category from prompt text so the right reward baselines apply."""
    import re as _re
    from fdao.types import TaskCategory

    pl = prompt.lower()

    # Hard triggers — any one of these alone = CODE_GENERATION
    hard_code = [
        "write a python function",
        "write a function",
        "implement a function",
        "implement a python",
        "create a function",
        "def ",
        "class ",
    ]
    if any(sig in pl for sig in hard_code):
        return TaskCategory.CODE_GENERATION

    # Soft triggers — need 2+ hits
    soft_code = [
        "function", "algorithm", "recursive", "iterative",
        "returns ", "return ", "->", "→",
        "sort", "search", "traverse", "implement",
    ]
    soft_score = sum(1 for sig in soft_code if sig in pl)

    # Backtick-quoted identifier followed by ( is a strong code signal
    if _re.search(r"`\w+\s*\(", prompt):
        soft_score += 3

    if soft_score >= 3:
        return TaskCategory.CODE_GENERATION

    tool_signals = ["call the", "use the api", "invoke", "tool_call", "function_call"]
    if any(sig in pl for sig in tool_signals):
        return TaskCategory.TOOL_USE

    return TaskCategory.QA


def _detect_difficulty(prompt: str, test_cases: list) -> str:
    """Rough difficulty based on test case count and prompt complexity."""
    from fdao.types import Difficulty
    words = len(prompt.split())
    n = len(test_cases)
    if n >= 4 or words > 200:
        return Difficulty.HARD
    if n >= 2 or words > 80:
        return Difficulty.MEDIUM
    return Difficulty.EASY


# ── Background worker ─────────────────────────────────────────────────────────

def _execute(run_id: str, req: LiveRunRequest) -> None:
    from dotenv import load_dotenv
    load_dotenv()

    from fdao.agent import Agent
    from fdao.orchestrator import Orchestrator
    from fdao.persistence.run_logger import RunLogger
    from fdao.reflection.engine import ReflectionEngine
    from fdao.reward.config import load_reward_composer
    from fdao.tasks.base import Task
    from fdao.types import TaskCategory, Difficulty, ValidationResult

    # Pre-detect so PromptTask and difficulty are consistent
    detected_category = _detect_task_category(req.prompt)

    class PromptTask(Task):
        """Ad-hoc task built from a free-form user prompt.

        Scoring:
          CODE_GENERATION prompts:
            - Run extracted test cases (fn(args) -> expected) against exec'd code
            - all pass  → score=1.0, passed=True
            - partial   → 0.45 + rate*0.5
            - no cases  → 0.72 (function defined, unverifiable)
            - syntax/runtime error → 0.2–0.3

          QA / TOOL_USE prompts:
            - Length + reasoning heuristic → 0.1–0.65
            - Never returns passed=True (no ground truth)

        Category is auto-detected at init time so the correct conciseness
        baseline (QA=120 chars, CODE=600 chars) applies.
        """

        def __init__(self, user_prompt: str) -> None:
            self.task_id    = f"live/{run_id[:8]}"
            self._prompt    = user_prompt
            self.category   = detected_category
            self._test_cases = _extract_test_cases(user_prompt, _guess_fn_name(user_prompt))
            self.difficulty = _detect_difficulty(user_prompt, self._test_cases)

        @property
        def prompt(self) -> str:
            return self._prompt

        def validate(self, attempt: str) -> ValidationResult:
            words = len(attempt.split())
            if words < 4:
                return ValidationResult(passed=False, score=0.05, details="too short")

            # ── Code path ────────────────────────────────────────────────
            code = _extract_code(attempt)
            if code:
                # Syntax check
                try:
                    compile(code, "<attempt>", "exec")
                except SyntaxError as e:
                    return ValidationResult(passed=False, score=0.2, details=f"syntax error: {e.msg}")

                # Execution check
                namespace: dict = {}
                try:
                    exec(code, namespace)  # noqa: S102
                except Exception as e:
                    return ValidationResult(passed=False, score=0.3, details=f"runtime error: {e}")

                fns = [k for k, v in namespace.items() if callable(v) and not k.startswith("_")]
                if not fns:
                    return ValidationResult(passed=False, score=0.45, details="code ran but no callable defined")

                fn = namespace[fns[0]]
                test_cases = self._test_cases or _extract_test_cases(req.prompt, fns[0])

                if not test_cases:
                    return ValidationResult(
                        passed=False,
                        score=0.72,
                        details=f"function '{fns[0]}' defined — no test cases to verify",
                    )

                passed_n, failures = 0, []
                for args, expected in test_cases:
                    try:
                        got = fn(*args)
                        if got == expected:
                            passed_n += 1
                        else:
                            failures.append(
                                f"{fns[0]}({', '.join(repr(a) for a in args)}) "
                                f"→ got {got!r}, want {expected!r}"
                            )
                    except Exception as exc:
                        failures.append(f"{fns[0]}(...) raised {type(exc).__name__}: {exc}")

                rate = passed_n / len(test_cases)
                if rate == 1.0:
                    return ValidationResult(
                        passed=True,
                        score=1.0,
                        details=f"all {len(test_cases)} test cases passed ✓",
                    )

                score = round(0.45 + rate * 0.5, 3)
                detail = (
                    f"{passed_n}/{len(test_cases)} passed. First failure: {failures[0]}"
                    if failures else f"{passed_n}/{len(test_cases)} passed"
                )
                return ValidationResult(passed=False, score=score, details=detail)

            # ── Text/QA path ─────────────────────────────────────────────
            has_reasoning = any(w in attempt.lower() for w in [
                "because", "therefore", "so", "thus", "since", "means",
                "equals", "result", "answer", "conclude", "=",
            ])
            base = min(0.5, words / 200)
            return ValidationResult(
                passed=False,
                score=round(base + (0.15 if has_reasoning else 0.0), 3),
                details=f"{words} words, reasoning={'yes' if has_reasoning else 'no'}",
            )

    # ── Helpers (module-level closures) ──────────────────────────────────────

    def _guess_fn_name(prompt: str) -> str:
        """Pull the first backtick-quoted identifier that looks like a function name."""
        import re
        m = re.search(r"`(\w+)\(", prompt)
        return m.group(1) if m else ""

    def _extract_test_cases(prompt: str, fn_name: str) -> list:
        """Parse lines like `fn_name([1,2,3]) -> "1-3"` from the prompt."""
        import re, ast
        if not fn_name:
            return []
        cases: list = []
        # Accept ASCII -> and => plus Unicode → (U+2192) that users type in the UI
        pattern = re.compile(rf'{re.escape(fn_name)}\((.+?)\)\s*(?:->|=>|→|==)\s*(.+)')
        for line in prompt.splitlines():
            m = pattern.search(line.strip())
            if not m:
                continue
            try:
                args     = ast.literal_eval(f"({m.group(1).strip()},)")
                expected = ast.literal_eval(m.group(2).strip())
                cases.append((args, expected))
            except Exception:
                continue
        return cases

    def _extract_code(text: str) -> str:
        """Return Python from a fenced block, or raw text if it looks like code."""
        if "```" in text:
            parts = text.split("```")
            for i, block in enumerate(parts):
                if i % 2 == 1:
                    code = block.lstrip("python").lstrip("py").strip()
                    if code:
                        return code
        if "def " in text or "return " in text:
            return text.strip()
        return ""

    # ── Build and wire objects ────────────────────────────────────────────────

    model    = os.environ.get("FDAO_DEFAULT_MODEL", req.model)
    composer = load_reward_composer(req.config)
    agent    = Agent(model=model)
    engine   = ReflectionEngine(model=model)
    logger   = RunLogger(experiment_name="live")
    orch     = Orchestrator(agent=agent, reward_composer=composer,
                            reflection_engine=engine, logger=logger)
    task     = PromptTask(req.prompt)

    live_run_id = run_id
    _orig_log   = logger.log_step

    def _patched_log(**kwargs):
        _orig_log(**kwargs)
        step = kwargs.get("step")
        if step is None:
            return
        ref = None
        if step.reflection:
            ref = {
                "failure_type":    step.reflection.failure_type.value,
                "root_cause":      step.reflection.root_cause,
                "what_worked":     step.reflection.what_worked,
                "strategy_update": step.reflection.strategy_update,
                "confidence":      step.reflection.confidence.value,
                "parse_failed":    step.reflection.parse_failed,
            }
        bus.emit(live_run_id, {
            "event":             "step",
            "run_id":            live_run_id,
            "task_id":           kwargs.get("task_id", ""),
            "iteration":         step.iteration,
            "attempt":           step.attempt,
            "score_composite":   step.reward.composite,
            "score_breakdown":   step.reward.breakdown,
            "reward_hacked":     step.reward.reward_hacked,
            "reflection":        ref,
            "antipattern":       step.antipattern,
            "converged":         step.reward.is_solved,
            "task_category":     task.category.value,
        })

    logger.log_step = _patched_log

    try:
        orch.run(task, max_iterations=req.max_iterations)
    finally:
        logger.close()
        bus.finish(live_run_id)
