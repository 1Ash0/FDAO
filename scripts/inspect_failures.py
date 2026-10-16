"""Quick inspection of failed runs from the SQLite log."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

task_filter = sys.argv[1:] or ["HE/H1", "HE/H2", "HE/H10"]
conn = sqlite3.connect("fdao_runs.db")

for task_id in task_filter:
    rows = conn.execute(
        "SELECT iteration, score_composite, attempt, reflection FROM runs "
        "WHERE task_id = ? ORDER BY iteration",
        (task_id,),
    ).fetchall()

    print(f"\n{'='*60}")
    print(f"Task: {task_id}")
    for it, score, attempt, ref in rows:
        print(f"\n  iter{it}  score={score}")
        print(f"  attempt (first 300 chars):\n    {attempt[:300].replace(chr(10), chr(10)+'    ')}")
        if ref:
            r = json.loads(ref)
            print(f"  failure_type : {r['failure_type']}")
            print(f"  root_cause   : {r['root_cause']}")
            print(f"  strategy_upd : {r['strategy_update']}")
            print(f"  confidence   : {r['confidence']}")

conn.close()
