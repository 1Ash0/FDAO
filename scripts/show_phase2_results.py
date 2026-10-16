"""Print a summary of Phase 2 results from the run DB."""
import sqlite3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

conn = sqlite3.connect("fdao_runs.db")

# Per-experiment summary: convergence, avg score, hacking, parse failures
rows = conn.execute("""
    SELECT
        experiment_name,
        COUNT(DISTINCT run_id) as n_runs,
        AVG(score_composite) as avg_score,
        SUM(reward_hacked) as hacked,
        SUM(reflection_parse_failed) as parse_fails
    FROM runs
    GROUP BY experiment_name
    ORDER BY experiment_name
""").fetchall()

print(f"\n{'Config':<26} {'Runs':<7} {'AvgScore':<11} {'Hacked':<9} {'ParseFail'}")
print("-" * 65)
for name, n_runs, avg_score, hacked, parse_fails in rows:
    print(f"{name:<26} {n_runs:<7} {avg_score:<11.3f} {hacked:<9} {parse_fails}")

# Show hacking instances
hacked_rows = conn.execute("""
    SELECT experiment_name, task_id, iteration, score_composite, score_breakdown
    FROM runs WHERE reward_hacked = 1
    ORDER BY experiment_name, task_id, iteration
""").fetchall()

if hacked_rows:
    print(f"\n{'='*65}")
    print("REWARD HACKING INSTANCES")
    print(f"{'='*65}")
    import json
    for exp, task, it, composite, breakdown_json in hacked_rows:
        breakdown = json.loads(breakdown_json)
        bd_str = "  ".join(f"{k}={v:.2f}" for k, v in breakdown.items())
        print(f"  [{exp}] {task} iter{it}: composite={composite:.3f}  {bd_str}")
else:
    print("\nNo reward hacking instances detected.")

conn.close()
