"""ReflectionEngine: structured self-critique after each failed attempt."""

from __future__ import annotations

import os

from fdao.reflection.parser import parse_reflection
from fdao.tasks.base import Task
from fdao.types import RewardResult, RunStep, StructuredReflection

# Max chars of the attempt to include — prevents token overflow for long code
_MAX_ATTEMPT_CHARS = 1500

REFLECTION_PROMPT = """\
You are a diagnostic agent analyzing why an AI agent failed a task. Be specific and actionable.

TASK:
{task_prompt}

AGENT'S ATTEMPT:
{attempt}

REWARD BREAKDOWN (signals contributing to composite score):
{score_breakdown}

SCORE TRAJECTORY (previous attempts this run):
{history_summary}

DIAGNOSIS INSTRUCTIONS:
- ROOT_CAUSE must identify the specific flaw in this attempt (not generic advice).
- STRATEGY_UPDATE must be directly actionable on the next attempt.
- CONFIDENCE should reflect how certain you are the strategy will improve the score.
  Use LOW if the error is ambiguous; HIGH only if the fix is clear and sufficient.
- Consider all reward signals: if correctness=0 but format=1.0, the output structure
  may be correct but the logic is wrong — diagnose accordingly.

Respond with exactly these fields, in this order:

FAILURE_TYPE: [logic_error | format_error | misunderstanding | tool_misuse | overcomplication | partial_solution]
ROOT_CAUSE: [1–2 sentences, specific to this attempt — reference the actual code or reasoning]
WHAT_WORKED: [1 sentence describing what was correct, or "nothing" if score=0]
STRATEGY_UPDATE: [1–2 concrete sentences describing what to change next]
CONFIDENCE: [low | medium | high]
"""


class ReflectionEngine:
    """Calls an LLM to produce a structured reflection on a failed attempt."""

    def __init__(self, model: str = "claude-sonnet-4-6") -> None:
        self.model = model

    def reflect(
        self,
        task: Task,
        attempt: str,
        reward: RewardResult,
        history: list[RunStep],
    ) -> StructuredReflection:
        history_summary = self._summarize_history(history)

        # Include signal names + values + weights context for the reflection LLM
        score_breakdown = ", ".join(
            f"{k}={v:.2f}" for k, v in sorted(reward.breakdown.items())
        )
        if reward.reward_hacked:
            score_breakdown += " ⚠ reward_hacked=True (high composite with zero correctness)"

        # Truncate long attempts to avoid token overflow
        attempt_text = attempt
        if len(attempt) > _MAX_ATTEMPT_CHARS:
            attempt_text = attempt[:_MAX_ATTEMPT_CHARS] + "\n[... truncated ...]"

        prompt = REFLECTION_PROMPT.format(
            task_prompt=task.prompt,
            attempt=attempt_text,
            score_breakdown=score_breakdown,
            history_summary=history_summary or "This is the first attempt.",
        )

        raw = self._call_llm(prompt)
        return parse_reflection(raw)

    def _summarize_history(self, history: list[RunStep]) -> str:
        if not history:
            return ""
        lines = []
        for step in history:
            ft = step.reflection.failure_type.value if step.reflection else "solved"
            lines.append(
                f"  attempt {step.iteration}: score={step.reward.composite:.2f}"
                f" [{ft}]"
                + (f" → {step.reflection.strategy_update[:80]}…"
                   if step.reflection and len(step.reflection.strategy_update) > 80
                   else (f" → {step.reflection.strategy_update}" if step.reflection else ""))
            )
        return "\n".join(lines)

    def _call_llm(self, prompt: str) -> str:
        if self.model.startswith("claude"):
            return self._call_anthropic(prompt)
        return self._call_openai_compat(prompt)

    def _call_anthropic(self, prompt: str) -> str:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise OSError("ANTHROPIC_API_KEY not set")
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=self.model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        return str(message.content[0].text)

    def _call_openai_compat(self, prompt: str) -> str:
        import time

        import openai

        from fdao.agent import GROQ_MODELS

        is_groq = self.model in GROQ_MODELS
        if is_groq:
            keys = [v for k, v in sorted(os.environ.items())
                    if k == "GROQ_API_KEY" or (k.startswith("GROQ_API_KEY_") and v)]
            if not keys:
                raise OSError("No GROQ_API_KEY found in environment")
        else:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise OSError("OPENAI_API_KEY not set")
            keys = [api_key]

        def _client(key: str) -> openai.OpenAI:
            if is_groq:
                return openai.OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            return openai.OpenAI(api_key=key)

        key_idx = 0
        client  = _client(keys[0])
        for _ in range(len(keys) + 3):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    max_tokens=600,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content or ""
            except openai.RateLimitError:
                next_idx = (key_idx + 1) % len(keys)
                if next_idx != key_idx:
                    key_idx = next_idx
                    client  = _client(keys[key_idx])
                    print(f"\n  [reflection rate limit] switching to key {key_idx+1}/{len(keys)}…", flush=True)
                    continue
                print("\n  [reflection rate limit] waiting 60s…", flush=True)
                time.sleep(60)
        return ""
