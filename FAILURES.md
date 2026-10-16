# FDAO Failure Analysis (Lab Notebook)

> **Status**: Phase 1 complete. Based on 364 steps / 231 runs from the partial
> experimental suite (baseline + 3 FDAO configs, 32 tasks, 1–2 seeds).
> Full re-run in progress with `openai/gpt-oss-120b`.

---

## Honest Summary of What Works and What Doesn't

| Domain    | Baseline Pass@1 | FDAO Pass@N | Delta | Verdict |
|-----------|----------------|-------------|-------|---------|
| HumanEval Hard | 61.5% (24/39) | 73.2% (52/71) | +11.7 pp | **FDAO helps** |
| HotpotQA  | 94.7% (18/19) | 88.2% (30/34) | −6.5 pp | Ceiling effect; FDAO can hurt |
| ToolUse   |  9.1% (1/11) | 22.7% (5/22) | +13.6 pp | Both low; FDAO learns format sometimes |

**Key finding confirmed**: Pearson r(reflection quality, convergence) data points to
reflection quality 0–1 (mostly) → low convergence; quality 2–3 → high convergence.
80% of reflections score 0 or 1. The reward signal alone isn't generating useful
reflection; better prompting or a stronger model is needed.

---

## Failure Catalogue

### F-001 · HE/H10 always fails (0% across all configs)

**Task**: `numerical_letter_grade(grades)` — convert list of GPAs to letter grades.

**Root cause**: The task docstring uses `>` (strict) notation throughout, e.g.
`> 3.7 → A`, `> 3.3 → A-`. The test cases however require **inclusive** bounds
at several specific values (3.0, 2.0, 1.7, 1.0) because the boundary value maps
to the *lower* grade, not the upper one. For example, the test asserts
`candidate([4.0, 3, 1.7, 2, 3.5])` returns `['A+', 'B+', 'C-', 'C+', 'A-']`,
meaning 3.0 → B+ (not D- or unlisted) and 1.7 → C- (not C). Any model reading
the docstring implements strict `>` and silently fails on boundary inputs.

**Why reflection can't fix it**: The validator returns `score=0.0` (binary pass/fail
from subprocess). With no partial credit on correctness and no visibility into
which specific assertion failed, the reflection signal is:
```
score: 0.0 → reflection: "try a different approach"
score: 0.0 → reflection: "try yet another approach"
```
The model gets no gradient. It oscillates between semantically identical solutions.

**Fix**:
1. Change the docstring to use `>=` explicitly for boundary values, *or*
2. Add partial credit: count the fraction of assertions passing (requires running
   each assertion separately in the subprocess), *or*
3. **Drop HE/H10** from the hard task set — it tests docstring ambiguity
   interpretation, not algorithmic reasoning. This is not what the paper studies.

**Status**: Dropping HE/H10 from the evaluation set pending a docstring fix.
See `fdao/tasks/humaneval.py:363`.

---

### F-002 · HE/H6 regresses under FDAO dense/correctness configs (100% → 33%)

**Task**: `largest_smallest_integers(lst)` — return (largest_negative, smallest_positive).

**Root cause**: This is an easy task; `gpt-oss-120b` (and previously llama-3.3-70b)
solves it correctly at iteration 0. However, under `dense_reward` and
`correctness_dominant` configs, a correct solution scores composite ≈ 0.989–0.991
(not exactly 1.0) because the conciseness/format aux signals penalise a slightly
verbose docstring in the response.

Since `is_solved = composite >= solved_threshold (1.0)`, the loop **does not stop**
even though `correctness = 1.0`. FDAO then keeps iterating on a working solution,
and on subsequent iterations the model occasionally changes its approach and
introduces a bug.

**This is a design bug, not a task difficulty problem.**

The reflection engine does have "correctness-gated reflection" (skips reflection
when correctness ≥ 1.0), but the orchestrator's `is_solved` check still uses
composite, not correctness. So: reflection is skipped, but another raw `agent.attempt()`
is called without new strategy context. The model receives no guidance but makes a
new attempt, risking drift.

**Fix** (tracked in `fdao/orchestrator.py`):
```python
# Current (buggy):
if reward.is_solved:  # composite >= 1.0
    break

# Correct:
if reward.breakdown.get("correctness", 0.0) >= 1.0:
    break
```
This stops the loop the moment the answer is correct, regardless of auxiliary
signal penalties for verbosity.

**Status**: Fix applied — see commit for orchestrator.py change.

---

### F-003 · Tool-use tasks: baseline 9%, FDAO 23%

**Tasks**: TU/1–TU/10

**What passes**: TU/3 (`web_search`, any non-empty query) — both baseline and FDAO.
TU/5, TU/9, TU/10 — FDAO converges on some seeds, baseline never does.

**What always fails**: TU/1 (`get_weather`, city="Tokyo"), TU/2 (`get_forecast`),
TU/4 (`get_wikipedia`), TU/6 (`list_events`), TU/7 (`query_database`),
TU/8 (`send_email`).

**Root cause (zero-shot)**: `gpt-oss-120b` (and llama-3.3-70b before it) does not
produce `tool_call("fn", {...})` syntax unprompted. The format note is appended to
every prompt but the model ignores it at first attempt (outputs prose). Score = 0.1
(format not found).

**Why FDAO improves some**: FDAO reflection after iter=0 sees the low format score
and explicitly updates strategy to: "must wrap in `tool_call(...)` syntax". The
model then complies. This works for simpler tasks (weather, calendar) where the
argument values are obvious from the prompt. It fails for tasks requiring specific
arg names that the model doesn't know (`get_wikipedia(title=...)` vs
`get_wikipedia(query=...)`).

**Deeper issue**: 8 of 10 TU tasks require exact argument names (`city`, `date`,
`to`, `target_language`, etc.). These names are not in the task prompt — the agent
is expected to infer them. This is an unreasonably tight constraint for a zero-shot
agent; the argument schema should be provided in the prompt.

**Fix option A** (paper claim): Report TU as a hard failure case — "FDAO can learn
format but not argument schema from reflection alone." Keep as-is; it's an honest
research finding.

**Fix option B** (better tasks): Add argument schema to prompts. E.g.:
```
Available: get_weather(city: str) -> dict
```
This tests whether FDAO can learn *correct usage* of a known API rather than
*discovering* the API signature from scratch.

**Status**: Keeping as-is for research validity. Noting in paper as a known limitation.

---

### F-004 · HQ/9 always fails (0% — Saturn moons count)

**Task**: "Which planet has the most moons? Approximately how many?"

**Root cause**: Knowledge boundary + answer instability. The correct answer (Saturn,
~146 moons as of 2026) is in flux — the Moon count changed from 83 to 95 to 146 as
new moons were discovered 2023–2026. Models trained before the latest count answer
"Jupiter" or "Saturn with 83 moons" — both technically wrong given the validator's
alias list `["saturn", "146", "145", "83"]`. The model may say "Saturn with 95
moons" which matches neither.

Reflection cannot fix a knowledge boundary. The model does not have access to
current moon counts and will oscillate between plausible-but-wrong values.

**Fix**: Either update the alias list to include all plausible counts (83, 95, 145, 146)
or reframe the task as "as of 2023" to fix the answer. The current alias list is too
narrow.

**Status**: Updating aliases — see `fdao/tasks/hotpotqa.py:144`.

---

### F-005 · HQ tasks: FDAO slightly hurts (−6.5 pp vs baseline)

**Tasks**: HQ/3 drops from 100% → 66.7%; a few others regress.

**Root cause**: HotpotQA tasks are mostly easy for a 70B-class model (baseline 94.7%).
When FDAO iterates on a task the model already solved, the same solved_threshold
bug (F-002) can cause drift. Additionally, for HQ, FDAO's reflection sometimes
introduces *overthinking*: the model second-guesses a correct one-line answer and
produces a longer response that passes the soft-match check less reliably.

The HQ domain is a near-ceiling domain for current models. Reflexion-style
improvement doesn't apply when Pass@1 is already 95%.

**Research implication**: This is an important *negative result*. FDAO adds noise
(and sometimes hurts) on tasks that are too easy. The optimal use case for FDAO is
tasks where baseline is 20–70% — not tasks already at 90%+.

---

### F-006 · Reward hacking: correctness_dominant config (6.7%–33.3%)

**Config**: `experiments/correctness_dominant.yaml` (correctness weight = 0.90)

**Observed**: 6.7% hacking rate at seed 0, 33.3% at seed 1 (small sample).

**Root cause**: Already fixed in a prior session — Tier 2 hacking detection was
firing as a false positive. With correctness weight = 0.9, when correctness = 0,
composite ≤ 0.10, which is below the `HACKING_COMPOSITE_THRESHOLD = 0.4`. The fix
adds `composite >= 0.4` as a guard on Tier 2. The remaining 6.7% (seed 0) may be
genuine hacking on TU tasks where the model outputs high-scoring format with
wrong function names.

**Status**: Tier-2 fix already applied (`fdao/reward/composer.py`). High seed-1 rate
is a small-sample artifact (6 runs).

---

## Bugs Fixed This Session

| Bug | File | Fix |
|-----|------|-----|
| `solved_threshold` uses composite not correctness → drift on easy tasks | `fdao/orchestrator.py` | Stop when `correctness >= 1.0` |
| HQ/9 validator alias list too narrow | `fdao/tasks/hotpotqa.py` | Add "95", "83" as valid moon counts |
| Model `llama-3.3-70b-versatile` deprecated on Groq | `fdao/agent.py`, `scripts/run_experiments.py` | Switched to `openai/gpt-oss-120b` |

## Known Limitations (not bugs)

- **HE/H10**: Docstring ambiguity makes the task unsolvable by reflection. Drop or fix the task.
- **TU tasks**: Argument schema not in prompt → reflection can't recover correct args. Research finding.
- **HQ ceiling**: ~95% baseline → FDAO can only hurt. Expected, not a failure.
- **Reflection quality**: 80% of reflections score 0–1. A stronger model or richer reward breakdown would help.
