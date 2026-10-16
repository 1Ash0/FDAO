"""Tests for the reflection parser."""

import pytest

from fdao.reflection.parser import parse_reflection
from fdao.types import ConfidenceLevel, FailureType

VALID_REFLECTION = """
FAILURE_TYPE: logic_error
ROOT_CAUSE: The agent incorrectly assumed the list was sorted, skipping the sort step entirely.
WHAT_WORKED: The function signature and return type were correct.
STRATEGY_UPDATE: Always verify input assumptions explicitly; add a sort step before binary search.
CONFIDENCE: high
"""

PREAMBLE_REFLECTION = """
Here is my analysis of the failure:

FAILURE_TYPE: format_error
ROOT_CAUSE: The output was missing the required JSON wrapper around the result.
WHAT_WORKED: The core calculation logic produced the right number.
STRATEGY_UPDATE: Wrap the final answer in {"result": ...} as required by the task.
CONFIDENCE: medium
"""

BRACKET_FAILURE_TYPE = """
FAILURE_TYPE: [partial_solution]
ROOT_CAUSE: Only the first half of the test cases passed.
WHAT_WORKED: The base case was handled correctly.
STRATEGY_UPDATE: Handle the recursive case when n > 1.
CONFIDENCE: low
"""


def test_parse_valid_reflection() -> None:
    r = parse_reflection(VALID_REFLECTION)
    assert r.failure_type == FailureType.LOGIC_ERROR
    assert "sort" in r.root_cause.lower()
    assert r.confidence == ConfidenceLevel.HIGH
    assert r.strategy_update != ""
    assert not r.parse_failed


def test_parse_with_preamble() -> None:
    """Parser should tolerate LLM adding explanation before the structured fields."""
    r = parse_reflection(PREAMBLE_REFLECTION)
    assert r.failure_type == FailureType.FORMAT_ERROR
    assert r.confidence == ConfidenceLevel.MEDIUM
    assert not r.parse_failed


def test_parse_brackets_around_failure_type() -> None:
    """Some models output [logic_error] — should strip brackets."""
    r = parse_reflection(BRACKET_FAILURE_TYPE)
    assert r.failure_type == FailureType.PARTIAL_SOLUTION
    assert not r.parse_failed


def test_parse_fallback_on_garbage() -> None:
    r = parse_reflection("this is not structured output at all")
    assert r.failure_type == FailureType.MISUNDERSTANDING
    assert r.confidence == ConfidenceLevel.LOW
    assert r.parse_failed


def test_parse_unknown_failure_type_falls_back() -> None:
    raw = VALID_REFLECTION.replace("logic_error", "completely_made_up_type")
    r = parse_reflection(raw)
    assert r.failure_type == FailureType.MISUNDERSTANDING


@pytest.mark.parametrize("failure_type", [ft.value for ft in FailureType])
def test_all_failure_types_parse(failure_type: str) -> None:
    raw = VALID_REFLECTION.replace("logic_error", failure_type)
    r = parse_reflection(raw)
    assert r.failure_type == FailureType(failure_type)
    assert not r.parse_failed
