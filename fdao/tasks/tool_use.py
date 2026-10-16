"""Tool-use tasks — agent must emit a structured tool call.

Format the agent must produce:
    tool_call("function_name", {"arg": value, ...})

The validator parses that call from the response and checks:
  - correct function name
  - required args are present and match expected values

The LLM is taught the expected format in the task prompt.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from typing import Any

from fdao.tasks.base import Task
from fdao.types import Difficulty, TaskCategory, ValidationResult

# Pattern: tool_call("name", {...}) or tool_call('name', {...})
_CALL_PATTERN = re.compile(
    r'tool_call\s*\(\s*["\'](\w+)["\']\s*,\s*(\{[^}]*\})\s*\)',
    re.DOTALL,
)

_FORMAT_NOTE = (
    "\n\nRespond with a single tool_call in this exact format:\n"
    '  tool_call("function_name", {"arg1": value1, "arg2": value2})\n'
    "No other text is needed."
)


def _parse_call(text: str) -> tuple[str, dict[str, Any]] | None:
    m = _CALL_PATTERN.search(text)
    if not m:
        return None
    fn_name = m.group(1)
    try:
        args = json.loads(m.group(2))
    except json.JSONDecodeError:
        try:
            args = ast.literal_eval(m.group(2))
        except Exception:
            return None
    return fn_name, args


def _values_match(expected: object, got: object) -> bool:
    """Case-insensitive string comparison; exact comparison for others."""
    if isinstance(expected, str) and isinstance(got, str):
        return expected.lower().strip() == got.lower().strip()
    return expected == got


@dataclass
class ToolUseTask(Task):
    """Agent must call the right function with the right arguments."""

    task_id: str
    _prompt: str
    expected_fn: str
    required_args: dict[str, Any]          # arg_name -> expected_value (None = any non-empty value)
    category: TaskCategory = TaskCategory.TOOL_USE
    difficulty: Difficulty = Difficulty.MEDIUM

    @property
    def prompt(self) -> str:
        return self._prompt + _FORMAT_NOTE

    def validate(self, attempt: str) -> ValidationResult:
        parsed = _parse_call(attempt)

        if parsed is None:
            # Did they at least name the right function?
            if self.expected_fn in attempt:
                return ValidationResult(
                    passed=False, score=0.3,
                    details="Correct function named but format invalid — missing tool_call(...) wrapper",
                )
            return ValidationResult(
                passed=False, score=0.1,
                details=f"No valid tool_call found. Expected tool_call(\"{self.expected_fn}\", ...)",
            )

        fn_name, args = parsed

        # Wrong function
        if fn_name != self.expected_fn:
            return ValidationResult(
                passed=False, score=0.2,
                details=f"Wrong function: got '{fn_name}', expected '{self.expected_fn}'",
            )

        # Check required args
        missing, wrong = [], []
        for arg, expected_val in self.required_args.items():
            if arg not in args:
                missing.append(arg)
            elif expected_val is not None and not _values_match(expected_val, args[arg]):
                wrong.append(f"{arg}: got {args[arg]!r}, want {expected_val!r}")

        if missing or wrong:
            partial = 0.5 + 0.3 * (len(self.required_args) - len(missing) - len(wrong)) / max(len(self.required_args), 1)
            detail = "; ".join([f"missing: {missing}" if missing else "", "; ".join(wrong)]).strip("; ")
            return ValidationResult(passed=False, score=round(partial, 3), details=detail)

        return ValidationResult(passed=True, score=1.0,
                                details=f"tool_call({fn_name!r}, {args}) correct")


TOOL_USE_TASKS: list[ToolUseTask] = [
    # ── Weather ───────────────────────────────────────────────────────────────
    ToolUseTask(
        task_id="TU/1",
        _prompt='The user says: "What\'s the weather like in Tokyo right now?" '
                'Call the appropriate function to get the current weather.',
        expected_fn="get_weather",
        required_args={"city": "Tokyo"},
        difficulty=Difficulty.EASY,
    ),
    ToolUseTask(
        task_id="TU/2",
        _prompt='The user asks: "Will it rain in London tomorrow?" '
                'Call the function that retrieves a weather forecast.',
        expected_fn="get_forecast",
        required_args={"city": "London", "days": None},   # any days value
        difficulty=Difficulty.EASY,
    ),
    # ── Search ────────────────────────────────────────────────────────────────
    ToolUseTask(
        task_id="TU/3",
        _prompt='The user asks: "Find me recent news about climate change." '
                'Call the web search function with an appropriate query.',
        expected_fn="web_search",
        required_args={"query": None},    # any non-empty query
        difficulty=Difficulty.EASY,
    ),
    ToolUseTask(
        task_id="TU/4",
        _prompt='The user asks: "Look up the Wikipedia article for Alan Turing." '
                'Use the function that fetches a Wikipedia article by title.',
        expected_fn="get_wikipedia",
        required_args={"title": "Alan Turing"},
        difficulty=Difficulty.EASY,
    ),
    # ── Calendar / scheduling ─────────────────────────────────────────────────
    ToolUseTask(
        task_id="TU/5",
        _prompt='The user says: "Schedule a meeting with Alice on 2026-07-15 at 14:00." '
                'Call the calendar function to create this event.',
        expected_fn="create_event",
        required_args={"title": None, "date": "2026-07-15", "time": None},
        difficulty=Difficulty.MEDIUM,
    ),
    ToolUseTask(
        task_id="TU/6",
        _prompt='The user asks: "Show me all events on my calendar for next Monday, 2026-06-22." '
                'Call the function that lists calendar events for a specific date.',
        expected_fn="list_events",
        required_args={"date": "2026-06-22"},
        difficulty=Difficulty.EASY,
    ),
    # ── Database / data ───────────────────────────────────────────────────────
    ToolUseTask(
        task_id="TU/7",
        _prompt='You have a `query_database` function. '
                'The user asks: "How many users signed up in the last 30 days?" '
                'Call the function with an appropriate SQL query.',
        expected_fn="query_database",
        required_args={"sql": None},      # any SQL that references users
        difficulty=Difficulty.MEDIUM,
    ),
    ToolUseTask(
        task_id="TU/8",
        _prompt='The user wants to send an email: '
                '"Send a thank-you email to bob@example.com with subject \'Thanks\'." '
                'Call the email function.',
        expected_fn="send_email",
        required_args={"to": "bob@example.com", "subject": "Thanks"},
        difficulty=Difficulty.MEDIUM,
    ),
    # ── Multi-arg / harder ────────────────────────────────────────────────────
    ToolUseTask(
        task_id="TU/9",
        _prompt='The user says: "Translate \'Hello, how are you?\' from English to Spanish." '
                'Call the translation function.',
        expected_fn="translate",
        required_args={"text": "Hello, how are you?", "target_language": "Spanish"},
        difficulty=Difficulty.MEDIUM,
    ),
    ToolUseTask(
        task_id="TU/10",
        _prompt='The user asks: "Convert 250 USD to EUR using today\'s exchange rate." '
                'Call the currency conversion function with the right arguments.',
        expected_fn="convert_currency",
        required_args={"amount": None, "from_currency": "USD", "to_currency": "EUR"},
        difficulty=Difficulty.MEDIUM,
    ),
]
