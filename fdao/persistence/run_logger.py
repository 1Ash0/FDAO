"""Logs every run step to SQLite. Schema is the single source of truth for analysis."""

import json
import sqlite3
from pathlib import Path

from fdao.types import RunStep

DB_PATH = Path("fdao_runs.db")

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    run_id                  TEXT NOT NULL,
    task_id                 TEXT NOT NULL,
    iteration               INTEGER NOT NULL,
    attempt                 TEXT NOT NULL,
    score_composite         REAL NOT NULL,
    score_breakdown         TEXT NOT NULL,   -- JSON: {signal_name: score}
    reward_hacked           INTEGER DEFAULT 0,
    reflection              TEXT,            -- JSON of StructuredReflection, NULL if solved
    reflection_parse_failed INTEGER DEFAULT 0,
    reflection_quality      INTEGER,         -- 0–3, NULL until next step completes
    antipattern             TEXT DEFAULT 'none',
    strategy_snapshot       TEXT,
    experiment_name         TEXT DEFAULT 'default',
    timestamp               TEXT NOT NULL,
    PRIMARY KEY (run_id, iteration)
);
"""


class RunLogger:
    def __init__(self, db_path: Path = DB_PATH, experiment_name: str = "default") -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(CREATE_TABLE)
        self.conn.commit()
        self.experiment_name = experiment_name

    def log_step(self, run_id: str, task_id: str, step: RunStep) -> None:
        reflection_json = None
        if step.reflection:
            reflection_json = json.dumps({
                "failure_type": step.reflection.failure_type.value,
                "root_cause": step.reflection.root_cause,
                "what_worked": step.reflection.what_worked,
                "strategy_update": step.reflection.strategy_update,
                "confidence": step.reflection.confidence.value,
            })

        parse_failed = int(step.reflection.parse_failed) if step.reflection else 0
        self.conn.execute(
            """INSERT INTO runs
               (run_id, task_id, iteration, attempt, score_composite, score_breakdown,
                reward_hacked, reflection, reflection_parse_failed,
                reflection_quality, antipattern, experiment_name, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run_id, task_id, step.iteration, step.attempt,
                step.reward.composite, json.dumps(step.reward.breakdown),
                int(step.reward.reward_hacked),
                reflection_json, parse_failed,
                step.reflection_quality,   # NULL at insert time, updated retroactively
                step.antipattern,
                self.experiment_name,
                step.timestamp.isoformat(),
            ),
        )
        self.conn.commit()

    def update_quality(self, run_id: str, iteration: int, quality: int, antipattern: str) -> None:
        """Retroactively fill in reflection_quality once the next step is known."""
        self.conn.execute(
            "UPDATE runs SET reflection_quality=?, antipattern=? WHERE run_id=? AND iteration=?",
            (quality, antipattern, run_id, iteration),
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()
