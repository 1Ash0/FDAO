"""Print best and worst scored reflections from the DB for manual analysis."""

import json
import sqlite3
from pathlib import Path

conn = sqlite3.connect(Path(__file__).parent.parent / "fdao_runs.db")
rows = conn.execute("""
    SELECT task_id, iteration, reflection_quality, antipattern,
           score_composite, reflection
    FROM runs
    WHERE reflection IS NOT NULL AND reflection_quality IS NOT NULL
    ORDER BY reflection_quality DESC, score_composite ASC
""").fetchall()
conn.close()

for r in rows:
    ref = json.loads(r[5])
    q = r[2]
    marker = "BEST" if q >= 2 else ("WORST" if q == 0 else "MID")
    print(f"[{marker}] task={r[0]}  iter={r[1]}  quality={q}/3  antipattern={r[3]}  score={r[4]:.2f}")
    print(f"  FAILURE_TYPE : {ref['failure_type']}")
    print(f"  CONFIDENCE   : {ref['confidence']}")
    print(f"  ROOT_CAUSE   : {ref['root_cause'].strip()}")
    print(f"  WHAT_WORKED  : {ref['what_worked'].strip()}")
    print(f"  STRATEGY     : {ref['strategy_update'].strip()}")
    print()
