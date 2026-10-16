"""Phase 6 analysis -- reads fdao_runs.db and prints paper-ready tables.

Usage:
    python scripts/analyze_results.py
    python scripts/analyze_results.py --db path/to/fdao_runs.db
    python scripts/analyze_results.py --exp dense_reward
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DEFAULT_DB = Path("fdao_runs.db")


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# == Table 1: Overall pass rates ==============================================

def table_pass_rates(conn: sqlite3.Connection, exp_filter: str | None = None) -> None:
    """Pass@1 = solved on first attempt. Pass@N = solved by any iteration.

    Convergence = correctness signal == 1.0 (objective) OR composite >= 0.999.
    Using correctness avoids false negatives when auxiliary signals drag
    composite below 1.0 on a correct answer.
    """
    where = f"WHERE experiment_name LIKE '%{exp_filter}%'" if exp_filter else ""

    rows = conn.execute(f"""
        SELECT experiment_name, task_id, run_id,
               MAX(CASE WHEN iteration=0 THEN score_composite END) AS iter0_score,
               MAX(CASE WHEN
                     score_composite >= 0.999
                     OR CAST(json_extract(score_breakdown,'$.correctness') AS REAL) >= 1.0
                   THEN 1 ELSE 0 END) AS converged
        FROM runs {where}
        GROUP BY experiment_name, task_id, run_id
    """).fetchall()

    if not rows:
        print("No data found.")
        return

    # Only show structured experiments, not live runs
    exps = sorted(set(r["experiment_name"] for r in rows
                  if not r["experiment_name"].startswith("live")))

    print("\n== Table 1: Pass rates by experiment ================================")
    print(f"{'Experiment':<32} {'Pass@1':>8} {'Pass@N':>8} {'N runs':>7}")
    print("-" * 57)
    for exp in exps:
        exp_rows = [r for r in rows if r["experiment_name"] == exp]
        p1 = sum(1 for r in exp_rows if (r["iter0_score"] or 0) >= 0.999) / len(exp_rows)
        pN = sum(r["converged"] for r in exp_rows) / len(exp_rows)
        print(f"{exp:<32} {p1*100:>7.1f}% {pN*100:>7.1f}% {len(exp_rows):>7}")


# == Table 1b: Aggregated by mode (baseline vs FDAO) ==========================

def table_aggregate(conn: sqlite3.Connection) -> None:
    """The headline number: FDAO vs baseline, aggregated across all configs."""
    rows = conn.execute("""
        SELECT experiment_name, task_id, run_id,
               MAX(CASE WHEN iteration=0 THEN score_composite END) AS iter0_score,
               MAX(CASE WHEN
                     score_composite >= 0.999
                     OR CAST(json_extract(score_breakdown,'$.correctness') AS REAL) >= 1.0
                   THEN 1 ELSE 0 END) AS converged
        FROM runs
        WHERE experiment_name NOT LIKE 'live%'
          AND experiment_name != 'phase3_analysis'
        GROUP BY experiment_name, task_id, run_id
    """).fetchall()

    baseline = [r for r in rows if r["experiment_name"].startswith("baseline")]
    fdao     = [r for r in rows if r["experiment_name"].startswith("fdao")]

    print("\n== HEADLINE: FDAO vs Baseline (aggregated) ==========================")
    print(f"{'Method':<20} {'Pass@1':>8} {'Pass@N':>8} {'N runs':>7}")
    print("-" * 45)
    if baseline:
        p1 = sum(1 for r in baseline if (r["iter0_score"] or 0) >= 0.999) / len(baseline)
        pN = sum(r["converged"] for r in baseline) / len(baseline)
        print(f"{'Baseline (0-shot)':<20} {p1*100:>7.1f}% {pN*100:>7.1f}% {len(baseline):>7}")
    if fdao:
        p1 = sum(1 for r in fdao if (r["iter0_score"] or 0) >= 0.999) / len(fdao)
        pN = sum(r["converged"] for r in fdao) / len(fdao)
        delta = pN - (sum(r["converged"] for r in baseline)/len(baseline) if baseline else 0)
        print(f"{'FDAO (all configs)':<20} {p1*100:>7.1f}% {pN*100:>7.1f}% {len(fdao):>7}   (+{delta*100:.1f}pp)")


# == Table 2: Per-task convergence ============================================

def table_per_task(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT experiment_name, task_id, run_id,
               MAX(CASE WHEN
                     score_composite >= 0.999
                     OR CAST(json_extract(score_breakdown,'$.correctness') AS REAL) >= 1.0
                   THEN 1 ELSE 0 END) AS converged
        FROM runs
        WHERE experiment_name NOT LIKE 'live%'
          AND experiment_name != 'phase3_analysis'
        GROUP BY experiment_name, task_id, run_id
    """).fetchall()

    if not rows:
        return

    # Aggregate seeds together per (exp_type, task)
    # exp_type = "baseline" | config name
    def exp_type(name: str) -> str:
        if name.startswith("baseline"):
            return "baseline"
        # fdao-dense_reward-s0 -> dense_reward
        parts = name.split("-")
        return "-".join(parts[1:-1]) if len(parts) >= 3 else name

    task_ids = sorted(set(r["task_id"] for r in rows))
    types    = sorted(set(exp_type(r["experiment_name"]) for r in rows))

    print("\n== Table 2: Per-task convergence rate (%) ===========================")
    header = f"{'Task':<14}"
    for t in types:
        header += f"  {t[:18]:>18}"
    print(header)
    print("-" * (14 + 20 * len(types)))

    for tid in task_ids:
        line = f"{tid:<14}"
        for t in types:
            runs = [r for r in rows
                    if r["task_id"] == tid and exp_type(r["experiment_name"]) == t]
            if not runs:
                line += f"  {'--':>18}"
            else:
                rate = sum(r["converged"] for r in runs) / len(runs) * 100
                line += f"  {rate:>17.0f}%"
        print(line)


# == Table 3: Reflection quality -> convergence ================================

def table_reflection_quality(conn: sqlite3.Connection) -> None:
    """Core FDAO claim: higher reflection quality predicts convergence."""
    rows = conn.execute("""
        SELECT q.run_id, q.avg_quality, c.converged
        FROM (
            SELECT run_id, AVG(reflection_quality) AS avg_quality
            FROM runs
            WHERE reflection_quality IS NOT NULL
              AND experiment_name NOT LIKE '%baseline%'
              AND experiment_name NOT LIKE 'live%'
            GROUP BY run_id
        ) q
        JOIN (
            SELECT run_id,
                   MAX(CASE WHEN
                         score_composite >= 0.999
                         OR CAST(json_extract(score_breakdown,'$.correctness') AS REAL) >= 1.0
                       THEN 1 ELSE 0 END) AS converged
            FROM runs
            WHERE experiment_name NOT LIKE '%baseline%'
              AND experiment_name NOT LIKE 'live%'
            GROUP BY run_id
        ) c ON q.run_id = c.run_id
    """).fetchall()

    if not rows:
        print("\n== Table 3: No reflection quality data yet ==========================")
        return

    buckets = {
        "Low  (0-1)": [r["converged"] for r in rows if (r["avg_quality"] or 0) < 1.0],
        "Med  (1-2)": [r["converged"] for r in rows if 1.0 <= (r["avg_quality"] or 0) < 2.0],
        "High (2-3)": [r["converged"] for r in rows if (r["avg_quality"] or 0) >= 2.0],
    }

    print("\n== Table 3: Reflection quality -> convergence rate ==================")
    print(f"{'Quality':<14} {'Converged':>10} {'Total':>7} {'Rate':>8}")
    print("-" * 41)
    for bucket, convs in buckets.items():
        if not convs:
            continue
        print(f"{bucket:<14} {sum(convs):>10} {len(convs):>7} {sum(convs)/len(convs)*100:>7.1f}%")

    # Pearson correlation (rudimentary)
    qs = [r["avg_quality"] or 0 for r in rows]
    cs = [r["converged"] for r in rows]
    n  = len(rows)
    if n > 1:
        mean_q = sum(qs) / n
        mean_c = sum(cs) / n
        cov  = sum((qs[i] - mean_q) * (cs[i] - mean_c) for i in range(n)) / n
        sd_q = (sum((q - mean_q)**2 for q in qs) / n) ** 0.5
        sd_c = (sum((c - mean_c)**2 for c in cs) / n) ** 0.5
        corr = cov / (sd_q * sd_c) if sd_q * sd_c > 0 else 0
        print(f"\n  Pearson r(quality, converged) = {corr:.3f}  (n={n})")


# == Table 4: Anti-pattern rates ==============================================

def table_antipatterns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT antipattern, COUNT(*) AS count
        FROM runs
        WHERE antipattern != 'none'
          AND experiment_name NOT LIKE '%baseline%'
          AND experiment_name NOT LIKE 'live%'
        GROUP BY antipattern
        ORDER BY count DESC
    """).fetchall()

    total = conn.execute("""
        SELECT COUNT(*) AS n FROM runs
        WHERE experiment_name NOT LIKE '%baseline%'
          AND experiment_name NOT LIKE 'live%'
    """).fetchone()["n"]

    print("\n== Table 4: Anti-pattern rates ======================================")
    if not rows:
        print("  None detected.")
        return
    print(f"{'Pattern':<16} {'Count':>8} {'% of steps':>12}")
    print("-" * 38)
    for r in rows:
        print(f"{r['antipattern']:<16} {r['count']:>8} {r['count']/total*100:>11.1f}%")


# == Table 5: Reward hacking ==================================================

def table_reward_hacking(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT experiment_name,
               SUM(reward_hacked) AS hacked,
               COUNT(*) AS total
        FROM runs
        WHERE experiment_name NOT LIKE 'live%'
          AND experiment_name != 'phase3_analysis'
        GROUP BY experiment_name
        HAVING hacked > 0
    """).fetchall()

    print("\n== Table 5: Reward hacking incidence ================================")
    if not rows:
        print("  No reward hacking detected.")
        return
    print(f"{'Experiment':<32} {'Hacked':>8} {'Total':>7} {'Rate':>8}")
    print("-" * 57)
    for r in rows:
        print(f"{r['experiment_name']:<32} {r['hacked']:>8} {r['total']:>7} {r['hacked']/r['total']*100:>7.1f}%")


# == Table 6: Convergence speed ===============================================

def table_convergence_speed(conn: sqlite3.Connection) -> None:
    rows = conn.execute("""
        SELECT run_id, MIN(iteration) AS conv_iter
        FROM runs
        WHERE (score_composite >= 0.999
               OR CAST(json_extract(score_breakdown,'$.correctness') AS REAL) >= 1.0)
          AND experiment_name NOT LIKE '%baseline%'
          AND experiment_name NOT LIKE 'live%'
        GROUP BY run_id
    """).fetchall()

    print("\n== Table 6: Convergence speed (FDAO runs that converged) ============")
    if not rows:
        print("  No convergences recorded yet.")
        return

    from collections import Counter
    dist  = Counter(r["conv_iter"] for r in rows)
    total = len(rows)
    print(f"{'Iteration':>10} {'Count':>8} {'%':>8}")
    print("-" * 28)
    for i in sorted(dist):
        print(f"{i:>10} {dist[i]:>8} {dist[i]/total*100:>7.1f}%")
    avg = sum(r["conv_iter"] for r in rows) / total
    print(f"\n  Mean convergence iteration: {avg:.2f}")
    print(f"  % solved on first attempt: {dist.get(0,0)/total*100:.1f}%")


# == Main =====================================================================

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db",  default=str(DEFAULT_DB))
    parser.add_argument("--exp", help="Filter by experiment name substring")
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"No DB at {db_path}. Run scripts/run_experiments.py first.")
        return

    conn = connect(db_path)
    n    = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
    runs = conn.execute("SELECT COUNT(DISTINCT run_id) FROM runs").fetchone()[0]
    print(f"\nDatabase: {db_path}  ({n} steps, {runs} runs)")

    table_aggregate(conn)
    table_pass_rates(conn, args.exp)
    table_per_task(conn)
    table_reflection_quality(conn)
    table_antipatterns(conn)
    table_reward_hacking(conn)
    table_convergence_speed(conn)
    conn.close()


if __name__ == "__main__":
    main()
