"""Tests for the reward composer and all signals.

Covers:
- Weight validation
- Output range [0, 1] for all signals
- Reward hacking detection
- YAML config loading
- Conciseness floor invariant
- Format compliance per task category
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from fdao.reward.composer import RewardComposer
from fdao.reward.config import from_dict, load_reward_composer
from fdao.reward.signals.conciseness import FLOOR, ConcisenessSignal
from fdao.reward.signals.correctness import CorrectnessSignal
from fdao.reward.signals.format_compliance import FormatComplianceSignal
from fdao.reward.signals.progress import ProgressSignal
from fdao.types import TaskCategory, ValidationResult

# ── Stubs ────────────────────────────────────────────────────────────────────

class _AlwaysPassTask:
    task_id = "test/pass"
    category = TaskCategory.QA
    difficulty = None
    prompt = "test"
    def validate(self, attempt: str) -> ValidationResult:
        return ValidationResult(passed=True, score=1.0)

class _AlwaysFailTask:
    task_id = "test/fail"
    category = TaskCategory.QA
    difficulty = None
    prompt = "test"
    def validate(self, attempt: str) -> ValidationResult:
        return ValidationResult(passed=False, score=0.3, details="wrong")

class _CodeTask:
    task_id = "test/code"
    category = TaskCategory.CODE_GENERATION
    difficulty = None
    prompt = "test"
    def validate(self, attempt: str) -> ValidationResult:
        return ValidationResult(passed=False, score=0.0)


# ── Composer invariants ───────────────────────────────────────────────────────

def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="sum to 1.0"):
        RewardComposer(signals=[
            CorrectnessSignal(weight=0.5),
            ConcisenessSignal(weight=0.3),
        ])


def test_single_signal_weight_one() -> None:
    composer = RewardComposer(signals=[CorrectnessSignal(weight=1.0)])
    result = composer.score(_AlwaysPassTask(), "answer")  # type: ignore
    assert result.composite == 1.0
    assert result.is_solved


def test_composite_always_in_range() -> None:
    composer = RewardComposer(signals=[
        CorrectnessSignal(weight=0.6),
        ConcisenessSignal(weight=0.2),
        FormatComplianceSignal(weight=0.2),
    ])
    for task in [_AlwaysPassTask(), _AlwaysFailTask(), _CodeTask()]:
        for attempt in ["", "x", "x" * 2000, "def foo(): pass"]:
            result = composer.score(task, attempt)  # type: ignore
            assert 0.0 <= result.composite <= 1.0


def test_reward_hacking_flagged() -> None:
    """High composite with correctness=0 should set reward_hacked=True."""
    composer = RewardComposer(signals=[
        CorrectnessSignal(weight=0.20),
        ConcisenessSignal(weight=0.70),
        FormatComplianceSignal(weight=0.10),
    ])
    # Short wrong answer: correctness=0, conciseness=1, format=1
    result = composer.score(_AlwaysFailTask(), "no")  # type: ignore
    assert result.breakdown["correctness"] == 0.0
    assert result.composite > 0.4
    assert result.reward_hacked is True


def test_no_hacking_when_correctness_high() -> None:
    composer = RewardComposer(signals=[
        CorrectnessSignal(weight=0.70),
        ConcisenessSignal(weight=0.20),
        FormatComplianceSignal(weight=0.10),
    ])
    result = composer.score(_AlwaysPassTask(), "short")  # type: ignore
    assert result.reward_hacked is False


# ── Conciseness signal ────────────────────────────────────────────────────────

def test_conciseness_at_baseline_is_one() -> None:
    sig = ConcisenessSignal(weight=1.0)
    task = _AlwaysPassTask()
    short_answer = "x" * 100   # well within QA baseline of 120
    assert sig.score(task, short_answer) == 1.0  # type: ignore


def test_conciseness_floor_respected() -> None:
    sig = ConcisenessSignal(weight=1.0)
    task = _AlwaysPassTask()
    very_long = "x" * 10_000
    score = sig.score(task, very_long)  # type: ignore
    assert score >= FLOOR


def test_conciseness_never_rewards_empty() -> None:
    sig = ConcisenessSignal(weight=1.0)
    task = _AlwaysPassTask()
    assert sig.score(task, "") == 1.0   # type: ignore  # empty = neutral, not a bonus


@given(length=st.integers(min_value=0, max_value=50_000))
@settings(max_examples=200)
def test_conciseness_always_in_range(length: int) -> None:
    sig = ConcisenessSignal(weight=1.0)
    task = _AlwaysPassTask()
    score = sig.score(task, "x" * length)  # type: ignore
    assert FLOOR <= score <= 1.0


# ── Format compliance ─────────────────────────────────────────────────────────

def test_format_code_with_fenced_block() -> None:
    sig = FormatComplianceSignal(weight=1.0)
    task = _CodeTask()
    assert sig.score(task, "```python\ndef foo():\n    pass\n```") == 1.0  # type: ignore


def test_format_code_with_bare_def() -> None:
    sig = FormatComplianceSignal(weight=1.0)
    task = _CodeTask()
    assert sig.score(task, "def foo(x):\n    return x") == 1.0  # type: ignore


def test_format_code_no_def_fails() -> None:
    sig = FormatComplianceSignal(weight=1.0)
    task = _CodeTask()
    assert sig.score(task, "the answer is 42") == 0.0  # type: ignore


def test_format_qa_empty_fails() -> None:
    sig = FormatComplianceSignal(weight=1.0)
    task = _AlwaysPassTask()
    assert sig.score(task, "") == 0.0  # type: ignore


def test_format_qa_short_passes() -> None:
    sig = FormatComplianceSignal(weight=1.0)
    task = _AlwaysPassTask()
    assert sig.score(task, "42") == 1.0  # type: ignore


# ── Progress vs Correctness distinction ──────────────────────────────────────

def test_progress_gives_partial_credit() -> None:
    """ProgressSignal uses score (0.3) while CorrectnessSignal uses passed (0)."""
    task = _AlwaysFailTask()   # score=0.3, passed=False
    assert ProgressSignal(weight=1.0).score(task, "x") == pytest.approx(0.3)  # type: ignore
    assert CorrectnessSignal(weight=1.0).score(task, "x") == 0.0              # type: ignore


# ── YAML config loading ───────────────────────────────────────────────────────

def test_from_dict_valid() -> None:
    config = {
        "reward_composer": {
            "solved_threshold": 1.0,
            "signals": [
                {"name": "correctness", "weight": 0.7},
                {"name": "conciseness", "weight": 0.3},
            ],
        }
    }
    composer = from_dict(config)
    assert len(composer.signals) == 2
    assert composer.signal_names == ["correctness", "conciseness"]


def test_from_dict_weights_enforced() -> None:
    config = {
        "reward_composer": {
            "signals": [
                {"name": "correctness", "weight": 0.5},
                {"name": "conciseness", "weight": 0.3},
            ]
        }
    }
    with pytest.raises(ValueError):
        from_dict(config)


def test_from_dict_unknown_signal() -> None:
    config = {
        "reward_composer": {
            "signals": [{"name": "nonexistent_signal", "weight": 1.0}]
        }
    }
    with pytest.raises(ValueError, match="Unknown signal"):
        from_dict(config)


def test_load_all_experiment_configs() -> None:
    """Every YAML in experiments/ must load without error."""
    experiments_dir = Path("experiments")
    if not experiments_dir.exists():
        pytest.skip("experiments/ dir not found — run from repo root")
    for yaml_file in experiments_dir.glob("*.yaml"):
        composer = load_reward_composer(yaml_file)
        assert len(composer.signals) > 0

