"""Check how often the reflection parser fails across all logged runs."""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

conn = sqlite3.connect("fdao_runs.db")
rows = conn.execute(
    "SELECT task_id, iteration, reflection FROM runs WHERE reflection IS NOT NULL"
).fetchall()

total = len(rows)
parse_fails = [
    (t, i, json.loads(r))
    for t, i, r in rows
    if json.loads(r)["root_cause"] == "Could not parse reflection."
]

print(f"Total reflections: {total}")
print(f"Parse failures:    {len(parse_fails)}  ({100*len(parse_fails)/total:.1f}%)")
if parse_fails:
    print("\nFailed on:")
    for t, i, r in parse_fails:
        print(f"  {t} iter{i}")
conn.close()
