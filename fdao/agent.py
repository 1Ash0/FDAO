"""LLM agent wrapper. Abstracts model calls behind a single attempt() interface."""

from __future__ import annotations

import os
from typing import Any

from fdao.tasks.base import Task

AGENT_SYSTEM_PROMPT = """\
You are an agent that improves its answers through iterative feedback.

REWARD SIGNAL: After each attempt you receive a composite score (0–1) broken down into:
  • correctness   — whether the answer is objectively right (highest priority)
  • progress      — how close you are to the solution
  • format        — whether output format matches requirements
  • conciseness   — whether the answer is appropriately brief

LEARNING RULE: When prior attempts and reflections are provided:
  1. Read the SCORE TRAJECTORY — understand which signals are low and why.
  2. Read the ROOT CAUSE — it identifies the specific error in the previous attempt.
  3. Follow the STRATEGY UPDATE — apply it directly, not loosely.
  4. Honor CONFIDENCE signals: HIGH = follow precisely; LOW = treat as one hypothesis.
  5. If a WARNING appears (same error 3+ times), you are stuck. Abandon your current
     approach entirely and reason from first principles about the problem structure.

EXPLORATION vs EXPLOITATION:
  - If score improves between attempts: continue refining (exploitation).
  - If score is flat or drops for 2+ attempts: fundamentally change your approach.
  - "Fundamentally change" means a different algorithm, data structure, or framing —
    not minor edits to the same solution.

OUTPUT: Provide only your answer. No preamble, no meta-commentary.
"""

# Groq models available for fast inference
GROQ_MODELS = {
    # Legacy (pre-2026-Q3)
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    # Current Groq catalog (2026-Q4)
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "allam-2-7b",
}


class Agent:
    """Wraps an LLM and exposes a single attempt() method.

    Swapping models is a one-line change:
        Agent(model="claude-sonnet-4-6")
        Agent(model="gpt-4o-mini")
        Agent(model="llama-3.3-70b-versatile")   # Groq
        Agent(model="ollama/mistral")
    """

    def __init__(self, model: str = "claude-sonnet-4-6", max_tokens: int = 1024) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._provider, self._client = self._build_client(model)

    def attempt(self, task: Task, strategy_context: str = "") -> str:
        """Send task + strategy context to the LLM. Returns the raw attempt string."""
        user_content = task.prompt
        if strategy_context:
            user_content = f"{strategy_context}\n\n{task.prompt}"

        if self._provider == "anthropic":
            return self._call_anthropic(user_content)
        else:
            return self._call_openai_compat(user_content)

    # ------------------------------------------------------------------
    # Internal dispatch
    # ------------------------------------------------------------------

    def _call_anthropic(self, user_content: str) -> str:
        import anthropic
        client: anthropic.Anthropic = self._client
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=AGENT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        return str(message.content[0].text)

    def _call_openai_compat(self, user_content: str) -> str:
        """Handles OpenAI, Groq (OpenAI-compatible), and Ollama.
        For Groq: rotates through available API keys on rate limit before waiting."""
        import time

        import openai

        def _make_client(key: str) -> openai.OpenAI:
            if self._provider == "groq":
                return openai.OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
            return self._client

        client: openai.OpenAI = self._client
        groq_keys: list[str] = getattr(self, "_groq_keys", [])
        key_idx: int = getattr(self, "_groq_key_idx", 0)

        MAX_RETRIES = 6
        for attempt_num in range(MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=[
                        {"role": "system", "content": AGENT_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                )
                return response.choices[0].message.content or ""
            except openai.RateLimitError:
                if groq_keys:
                    next_idx = (key_idx + 1) % len(groq_keys)
                    key_idx = next_idx
                    self._groq_key_idx = key_idx
                    client = _make_client(groq_keys[key_idx])
                    print(f"\n  [rate limit] switching to Groq key {key_idx+1}/{len(groq_keys)}...", flush=True)
                    # After a full cycle through all keys, sleep before retrying
                    if next_idx == 0:
                        wait = 62
                        print(f"\n  [rate limit] all keys exhausted, waiting {wait}s...", flush=True)
                        time.sleep(wait)
                else:
                    wait = 62
                    print(f"\n  [rate limit] waiting {wait}s...", flush=True)
                    time.sleep(wait)

        raise RuntimeError(f"LLM call failed after {MAX_RETRIES} attempts due to rate limiting")

    def _build_client(self, model: str) -> tuple[str, Any]:
        """Return (provider_name, sdk_client) based on model name."""
        if model.startswith("claude"):
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise OSError("ANTHROPIC_API_KEY not set")
            return "anthropic", anthropic.Anthropic(api_key=api_key)

        if model in GROQ_MODELS:
            import openai
            # Collect all GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, ... in order
            keys = [v for k, v in sorted(os.environ.items())
                    if k == "GROQ_API_KEY" or (k.startswith("GROQ_API_KEY_") and v)]
            if not keys:
                raise OSError("No GROQ_API_KEY found in environment")
            self._groq_keys = keys
            self._groq_key_idx = 0
            return "groq", openai.OpenAI(
                api_key=keys[0],
                base_url="https://api.groq.com/openai/v1",
            )

        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            import openai
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise OSError("OPENAI_API_KEY not set")
            return "openai", openai.OpenAI(api_key=api_key)

        if model.startswith("ollama/"):
            import openai
            # strip "ollama/" prefix — Ollama server uses bare model names
            self.model = model.removeprefix("ollama/")
            return "ollama", openai.OpenAI(
                api_key="ollama",
                base_url="http://localhost:11434/v1",
            )

        raise ValueError(
            f"Unrecognised model: {model!r}. "
            "Prefix with 'ollama/' for local models, or add it to GROQ_MODELS."
        )
