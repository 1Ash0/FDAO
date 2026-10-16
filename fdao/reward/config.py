"""Load a RewardComposer from a YAML experiment config.

Config format:
    reward_composer:
      solved_threshold: 1.0      # optional, default 1.0
      signals:
        - name: correctness
          weight: 0.7
        - name: conciseness
          weight: 0.2
        - name: format_compliance
          weight: 0.1

Signal names map to the registry below. Adding a new signal:
  1. Implement RewardSignal subclass in fdao/reward/signals/
  2. Add it to _SIGNAL_REGISTRY
  3. Reference it by name in YAML
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from fdao.reward.composer import RewardComposer, RewardSignal
from fdao.reward.signals.conciseness import ConcisenessSignal
from fdao.reward.signals.correctness import CorrectnessSignal
from fdao.reward.signals.format_compliance import FormatComplianceSignal
from fdao.reward.signals.progress import ProgressSignal
from fdao.reward.signals.stability import StabilitySignal
from fdao.reward.signals.tool_efficiency import ToolEfficiencySignal

_SIGNAL_REGISTRY: dict[str, type[RewardSignal]] = {
    "correctness":       CorrectnessSignal,
    "conciseness":       ConcisenessSignal,
    "format_compliance": FormatComplianceSignal,
    "progress":          ProgressSignal,
    "stability":         StabilitySignal,
    "tool_efficiency":   ToolEfficiencySignal,
}


def load_reward_composer(config_path: str | Path) -> RewardComposer:
    """Build a RewardComposer from a YAML experiment config file."""
    raw = yaml.safe_load(Path(config_path).read_text())
    return from_dict(raw)


def from_dict(config: dict[str, Any]) -> RewardComposer:
    """Build a RewardComposer from an already-parsed config dict."""
    rc_conf = config.get("reward_composer", config)  # tolerate bare or nested
    solved_threshold = float(rc_conf.get("solved_threshold", 1.0))
    signals: list[RewardSignal] = []

    for sig_conf in rc_conf["signals"]:
        name = sig_conf["name"]
        weight = float(sig_conf["weight"])
        if name not in _SIGNAL_REGISTRY:
            raise ValueError(
                f"Unknown signal {name!r}. Available: {list(_SIGNAL_REGISTRY)}"
            )
        signals.append(_SIGNAL_REGISTRY[name](weight=weight))

    return RewardComposer(signals=signals, solved_threshold=solved_threshold)


def default_composer() -> RewardComposer:
    """Sparse baseline: correctness only. Used when no config is specified."""
    return RewardComposer(signals=[CorrectnessSignal(weight=1.0)])
