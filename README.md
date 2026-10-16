# FDAO: Feedback-Driven Agent Optimizer

An LLM agent that improves its own task performance through reward-guided structured
reflection, with no weight updates. Each iteration is treated as a policy-improvement step:
the reward signal plays the role of value estimation, the reflection plays the role of the
gradient, and the updated strategy context is the new policy.

**Research question:** under which reward structures, task types, and iteration budgets does
reflection-based improvement work, and when does it fail?

> Status: work in progress. The core loop, reward composer, reflection engine, run logging,
> API and dashboard exist. The baseline comparison (zero-shot, Reflexion, oracle reward) and
> the written analysis are not finished, so this repo makes no performance claims yet.

## How it works

```
Orchestrator
  -> Agent.attempt(task, strategy_context)
  -> RewardComposer.score(task, attempt)        # weighted signals -> composite in [0, 1]
  -> ReflectionEngine.reflect(...)              # structured: failure type, root cause, update
  -> StrategyStore.update(reflection)           # context for the next attempt
  -> RunLogger                                  # every step to SQLite
```

| Part | What it does |
|---|---|
| `fdao/reward/` | Composable signals (correctness, conciseness, format compliance, progress, stability, tool efficiency) with per-experiment weights from YAML |
| `fdao/reflection/` | Structured reflection parser, retroactive reflection-quality score (0 to 3), anti-pattern detector (circular, overcorrect, drift) |
| `fdao/tasks/` | Tasks with deterministic validators: HumanEval-style coding, math, logic, multi-hop QA, tool use |
| `experiments/*.yaml` | Reward configs: sparse, medium, dense, correctness-dominant, and a deliberately broken one for reward-hacking demos |
| `api/` + `dashboard/` | FastAPI backend and Next.js dashboard for live runs, score curves, and reflection history |

Two design choices worth knowing about:

- **Validators are ground truth.** Task validators are deterministic and contain no LLM calls,
  so reward signals are scored against something objective.
- **Reward hacking is a first-class failure mode.** Runs where the composite score is high but
  correctness is low are flagged (`reward_hacked`), and `experiments/reward_hacking_demo.yaml`
  shows the failure on purpose. Do not use that config for real experiments.

## Setup

Requires Python 3.11 or newer.

```bash
pip install -e ".[dev]"
cp .env.example .env     # add at least one provider key (Anthropic, OpenAI, or Groq)
pytest                   # unit tests, no API key needed
```

Models are selected by name: `claude-*` (Anthropic), `gpt-*` (OpenAI), Groq model names, or
`ollama/<model>`. Set `FDAO_DEFAULT_MODEL` in `.env`.

## Running

```bash
python scripts/run_experiments.py --tasks HE/1,HE/2 --seeds 1   # small run
python scripts/run_experiments.py --mode baseline               # zero-shot only
uvicorn api.main:app --port 8000                                # API, docs at /docs
cd dashboard && npm install && npm run dev                      # dashboard on :3000
```

Runs are written to SQLite (`FDAO_DB_PATH`). Database files and `.env` are git-ignored.

## Roadmap

- [ ] Baselines: zero-shot, few-shot, Reflexion reproduction, random strategy, oracle reward
- [ ] Reward-density and weight-sensitivity experiments with per-task confidence intervals
- [ ] Reflection quality vs convergence analysis
- [ ] Judge audit: compare LLM-judge scores against validator ground truth, with canary runs
- [ ] Trace adapter so external agent runs can be evaluated

## Related work

Reflexion (Shinn et al., 2023) showed verbal reflection can improve agents. This project
studies the part Reflexion leaves open: how the structure of the reward signal affects it.
