"""Read-only SQLite access for the API layer.

All writes go through RunLogger. The API only reads.
Returns plain dicts so routers can validate into Pydantic schemas.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path("fdao_runs.db")


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Runs ──────────────────────────────────────────────────────────────────────

def get_all_runs() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT
                run_id,
                task_id,
                experiment_name,
                COUNT(*)            AS n_iterations,
                MAX(score_composite) AS final_score,
                MAX(CASE WHEN reflection IS NULL AND score_composite >= 1.0 THEN 1 ELSE 0 END) AS converged,
                SUM(reward_hacked)  AS reward_hacked_count,
                SUM(CASE WHEN antipattern != 'none' THEN 1 ELSE 0 END) AS antipattern_count,
                MIN(timestamp)      AS timestamp
            FROM runs
            GROUP BY run_id
            ORDER BY MIN(timestamp) DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_run_steps(run_id: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT iteration, attempt, score_composite, score_breakdown,
                   reward_hacked, reflection, reflection_parse_failed,
                   reflection_quality, antipattern, timestamp
            FROM runs
            WHERE run_id = ?
            ORDER BY iteration
        """, (run_id,)).fetchall()
    steps = []
    for r in rows:
        d = dict(r)
        d["score_breakdown"] = json.loads(d["score_breakdown"])
        d["reflection"] = json.loads(d["reflection"]) if d["reflection"] else None
        d["reward_hacked"] = bool(d["reward_hacked"])
        d["reflection_parse_failed"] = bool(d["reflection_parse_failed"])
        steps.append(d)
    return steps


def get_run_meta(run_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("""
            SELECT run_id, task_id, experiment_name,
                   MAX(score_composite) AS final_score,
                   MAX(CASE WHEN reflection IS NULL AND score_composite >= 1.0 THEN 1 ELSE 0 END) AS converged
            FROM runs WHERE run_id = ?
        """, (run_id,)).fetchone()
    return dict(row) if row else None


# ── Experiments ───────────────────────────────────────────────────────────────

def get_all_experiments() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT
                experiment_name,
                COUNT(DISTINCT run_id)  AS n_runs,
                COUNT(DISTINCT task_id) AS n_tasks,
                SUM(CASE WHEN reflection IS NULL AND score_composite >= 1.0 THEN 1 ELSE 0 END) AS converged,
                AVG(CASE WHEN iteration = (
                    SELECT MAX(iteration) FROM runs r2 WHERE r2.run_id = runs.run_id
                ) THEN score_composite END) AS avg_final_score,
                AVG(reflection_quality) AS avg_reflection_quality,
                SUM(reward_hacked)      AS reward_hacked_total
            FROM runs
            GROUP BY experiment_name
            ORDER BY MIN(timestamp) DESC
        """).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        # antipattern breakdown per experiment
        with _connect() as conn2:
            aps = conn2.execute("""
                SELECT antipattern, COUNT(*) AS cnt
                FROM runs
                WHERE experiment_name = ? AND antipattern != 'none'
                GROUP BY antipattern
            """, (d["experiment_name"],)).fetchall()
        d["antipattern_breakdown"] = {a["antipattern"]: a["cnt"] for a in aps}
        results.append(d)
    return results


def get_experiment_runs(experiment_name: str) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute("""
            SELECT run_id, task_id, experiment_name,
                   COUNT(*) AS n_iterations,
                   MAX(score_composite) AS final_score,
                   MAX(CASE WHEN reflection IS NULL AND score_composite >= 1.0 THEN 1 ELSE 0 END) AS converged,
                   SUM(reward_hacked) AS reward_hacked_count,
                   SUM(CASE WHEN antipattern != 'none' THEN 1 ELSE 0 END) AS antipattern_count,
                   MIN(timestamp) AS timestamp
            FROM runs
            WHERE experiment_name = ?
            GROUP BY run_id
            ORDER BY MIN(timestamp) DESC
        """, (experiment_name,)).fetchall()
    return [dict(r) for r in rows]


# ── Aggregate metrics ─────────────────────────────────────────────────────────

def get_aggregate_metrics() -> dict:
    with _connect() as conn:
        r = conn.execute("""
            SELECT
                COUNT(DISTINCT run_id)  AS total_runs,
                COUNT(*)                AS total_steps,
                AVG(CASE WHEN reflection IS NULL AND score_composite >= 1.0 THEN 1.0 ELSE 0.0 END) AS overall_convergence_rate,
                AVG(score_composite)    AS avg_final_score,
                AVG(reflection_quality) AS avg_reflection_quality,
                AVG(reflection_parse_failed) AS parse_failure_rate,
                AVG(reward_hacked)      AS reward_hacking_rate
            FROM runs
        """).fetchone()
        aps = conn.execute("""
            SELECT antipattern, COUNT(*) AS cnt
            FROM runs WHERE antipattern != 'none'
            GROUP BY antipattern
        """).fetchall()
    d = dict(r)
    d["antipattern_breakdown"] = {a["antipattern"]: a["cnt"] for a in aps}
    return d


# ── Tasks ─────────────────────────────────────────────────────────────────────

def get_tasks_from_db() -> list[dict]:
    """Return distinct task_ids seen in runs, with their latest score."""
    with _connect() as conn:
        rows = conn.execute("""
            SELECT DISTINCT task_id,
                   AVG(score_composite) AS avg_score,
                   COUNT(DISTINCT run_id) AS n_runs
            FROM runs GROUP BY task_id ORDER BY task_id
        """).fetchall()
    return [dict(r) for r in rows]
