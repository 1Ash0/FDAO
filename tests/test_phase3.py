"""Tests for Phase 3: reflection quality scoring and anti-pattern detection."""


from fdao.reflection.antipatterns import AntiPattern, AntiPatternDetector
from fdao.reflection.quality import ReflectionQualityScorer
from fdao.types import (
    ConfidenceLevel,
    FailureType,
    RewardResult,
    RunStep,
    StructuredReflection,
)

# ── Helpers ───────────────────────────────────────────────────────────────────

def make_reward(composite: float, correct: float = None) -> RewardResult:
    if correct is None:
        correct = composite
    return RewardResult(
        composite=composite,
        breakdown={"correctness": correct},
        is_solved=composite >= 1.0,
    )


def make_reflection(
    failure_type: FailureType = FailureType.LOGIC_ERROR,
    root_cause: str = "wrong algorithm used",
    strategy_update: str = "use dynamic programming instead of brute force",
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM,
) -> StructuredReflection:
    return StructuredReflection(
        failure_type=failure_type,
        root_cause=root_cause,
        what_worked="problem understanding was correct",
        strategy_update=strategy_update,
        confidence=confidence,
    )


def make_step(
    iteration: int,
    score: float,
    reflection: StructuredReflection | None = None,
    attempt: str = "def solve(): pass",
    antipattern: str = "none",
) -> RunStep:
    return RunStep(
        iteration=iteration,
        attempt=attempt,
        reward=make_reward(score),
        reflection=reflection,
        antipattern=antipattern,
    )


# ── ReflectionQualityScorer ───────────────────────────────────────────────────

class TestReflectionQualityScorer:
    scorer = ReflectionQualityScorer()

    def test_all_components_pass(self):
        # Reflection on step 0: logic_error, use DP
        refl = make_reflection(
            failure_type=FailureType.LOGIC_ERROR,
            strategy_update="use dynamic programming memoization cache",
        )
        prev = make_step(0, 0.3, reflection=refl, attempt="brute force approach")
        # Next step: improved score, attempt mentions dp, different failure type
        next_refl = make_reflection(failure_type=FailureType.FORMAT_ERROR)
        nxt = make_step(
            1, 0.7,
            reflection=next_refl,
            attempt="dynamic programming with memoization cache approach",
        )
        result = self.scorer.score(prev, nxt)
        assert result.total == 3
        assert result.score_improved is True
        assert result.strategy_followed is True
        assert result.failure_correctly_identified is True

    def test_score_not_improved(self):
        refl = make_reflection()
        prev = make_step(0, 0.8, reflection=refl)
        nxt = make_step(1, 0.5, reflection=make_reflection(FailureType.FORMAT_ERROR))
        result = self.scorer.score(prev, nxt)
        assert result.score_improved is False
        assert result.total <= 2

    def test_same_failure_type_not_identified_correctly(self):
        refl = make_reflection(failure_type=FailureType.LOGIC_ERROR)
        prev = make_step(0, 0.3, reflection=refl)
        # Same failure type and no meaningful score gain -> diagnosis did not help
        next_refl = make_reflection(failure_type=FailureType.LOGIC_ERROR)
        nxt = make_step(1, 0.31, reflection=next_refl)
        result = self.scorer.score(prev, nxt)
        assert result.failure_correctly_identified is False

    def test_same_failure_type_with_progress_counts_as_identified(self):
        # Documented rule: same error class but score improved >= 0.05 is progress.
        refl = make_reflection(failure_type=FailureType.LOGIC_ERROR)
        prev = make_step(0, 0.3, reflection=refl)
        next_refl = make_reflection(failure_type=FailureType.LOGIC_ERROR)
        nxt = make_step(1, 0.5, reflection=next_refl)
        result = self.scorer.score(prev, nxt)
        assert result.failure_correctly_identified is True

    def test_solved_counts_as_correct_identification(self):
        refl = make_reflection()
        prev = make_step(0, 0.5, reflection=refl)
        # No reflection on next step = solved
        nxt = make_step(1, 1.0, reflection=None)
        result = self.scorer.score(prev, nxt)
        assert result.failure_correctly_identified is True

    def test_no_reflection_returns_zero(self):
        prev = make_step(0, 0.5, reflection=None)
        nxt = make_step(1, 0.8, reflection=None)
        result = self.scorer.score(prev, nxt)
        assert result.total == 0

    def test_strategy_not_followed_when_no_keyword_overlap(self):
        refl = make_reflection(
            strategy_update="implement binary search tree traversal algorithm",
        )
        prev = make_step(0, 0.3, reflection=refl)
        nxt = make_step(
            1, 0.6,
            reflection=make_reflection(FailureType.FORMAT_ERROR),
            attempt="add print statements for debugging purposes",
        )
        result = self.scorer.score(prev, nxt)
        assert result.strategy_followed is False


# ── AntiPatternDetector ───────────────────────────────────────────────────────

class TestAntiPatternDetector:
    detector = AntiPatternDetector()

    def test_no_antipattern(self):
        refl = make_reflection(strategy_update="use completely different sorting approach")
        history = [make_step(0, 0.3, make_reflection(strategy_update="fix the loop index"))]
        result = self.detector.detect(refl, history, current_score=0.6)
        assert result.pattern == AntiPattern.NONE

    def test_circular_detected(self):
        shared_strategy = "use dynamic programming memoization table lookup"
        history = [make_step(0, 0.3, make_reflection(strategy_update=shared_strategy))]
        # Current reflection has same strategy → Jaccard will be high
        refl = make_reflection(strategy_update=shared_strategy)
        result = self.detector.detect(refl, history, current_score=0.35)
        assert result.pattern == AntiPattern.CIRCULAR

    def test_overcorrect_detected(self):
        # Previous step had HIGH confidence reflection
        prev_refl = make_reflection(confidence=ConfidenceLevel.HIGH)
        history = [make_step(0, 0.8, prev_refl)]
        # Current score dropped after that HIGH confidence step
        refl = make_reflection()
        result = self.detector.detect(refl, history, current_score=0.4)
        assert result.pattern == AntiPattern.OVERCORRECT

    def test_overcorrect_not_triggered_when_score_improves(self):
        prev_refl = make_reflection(confidence=ConfidenceLevel.HIGH)
        history = [make_step(0, 0.3, prev_refl)]
        refl = make_reflection()
        result = self.detector.detect(refl, history, current_score=0.7)
        assert result.pattern != AntiPattern.OVERCORRECT

    def test_drift_detected(self):
        # DRIFT_WINDOW=3: need original step to be outside the last-3 window.
        # Use 4 history steps so history[-3:] no longer contains step 0 (LOGIC_ERROR).
        original_refl = make_reflection(
            failure_type=FailureType.LOGIC_ERROR,
            root_cause="wrong sorting algorithm completely unrelated topic",
        )
        history = [
            make_step(0, 0.3, original_refl),
            make_step(1, 0.30, make_reflection(
                failure_type=FailureType.FORMAT_ERROR,
                root_cause="output format needs adjustment"
            )),
            make_step(2, 0.31, make_reflection(
                failure_type=FailureType.FORMAT_ERROR,
                root_cause="missing newlines in output"
            )),
            make_step(3, 0.30, make_reflection(
                failure_type=FailureType.OVERCOMPLICATION,
                root_cause="response too verbose"
            )),
        ]
        # Current reflection still different failure type, no root cause overlap
        drifted_refl = make_reflection(
            failure_type=FailureType.OVERCOMPLICATION,
            strategy_update="simplify output formatting",
            root_cause="response too verbose with unnecessary content"
        )
        result = self.detector.detect(drifted_refl, history, current_score=0.31)
        assert result.pattern == AntiPattern.DRIFT

    def test_no_drift_when_scores_are_improving(self):
        # Same shape as the drift case, but scores rise > 0.05 across the window:
        # a pivot that is working is exploration, not drift.
        original_refl = make_reflection(
            failure_type=FailureType.LOGIC_ERROR,
            root_cause="wrong sorting algorithm completely unrelated topic",
        )
        history = [
            make_step(0, 0.3, original_refl),
            make_step(1, 0.35, make_reflection(failure_type=FailureType.FORMAT_ERROR)),
            make_step(2, 0.40, make_reflection(failure_type=FailureType.FORMAT_ERROR)),
            make_step(3, 0.42, make_reflection(failure_type=FailureType.OVERCOMPLICATION)),
        ]
        refl = make_reflection(
            failure_type=FailureType.OVERCOMPLICATION,
            strategy_update="simplify output formatting",
        )
        result = self.detector.detect(refl, history, current_score=0.45)
        assert result.pattern != AntiPattern.DRIFT

    def test_no_drift_without_enough_history(self):
        # Only 2 steps — DRIFT_WINDOW=3, so not enough history
        history = [
            make_step(0, 0.3, make_reflection(failure_type=FailureType.LOGIC_ERROR)),
            make_step(1, 0.4, make_reflection(failure_type=FailureType.FORMAT_ERROR)),
        ]
        refl = make_reflection(failure_type=FailureType.OVERCOMPLICATION)
        result = self.detector.detect(refl, history, current_score=0.5)
        assert result.pattern != AntiPattern.DRIFT

    def test_empty_history_no_crash(self):
        refl = make_reflection()
        result = self.detector.detect(refl, [], current_score=0.5)
        assert result.pattern == AntiPattern.NONE
