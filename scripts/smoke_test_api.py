"""Quick smoke test for all API endpoints."""
import json, urllib.request

BASE = "http://localhost:8000"

def get(path):
    try:
        with urllib.request.urlopen(f"{BASE}{path}") as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ERROR": str(e)}

print("=== /health ===")
print(get("/health"))

print("\n=== /api/runs ===")
runs = get("/api/runs")
print(f"Total runs in DB: {len(runs)}")
if runs:
    r = runs[0]
    print(f"  run_id={r['run_id'][:8]}...  task={r['task_id']}  final_score={r['final_score']:.2f}  converged={r['converged']}")

print("\n=== /api/runs/{id}/steps ===")
if runs:
    rid = runs[0]["run_id"]
    steps = get(f"/api/runs/{rid}/steps")
    print(f"  Steps in run: {len(steps)}")
    for s in steps:
        print(f"  iter={s['iteration']}  score={s['score_composite']:.2f}  ap={s['antipattern']}")

print("\n=== /api/experiments ===")
exps = get("/api/experiments")
print(json.dumps(exps, indent=2))

print("\n=== /api/metrics/aggregate ===")
m = get("/api/metrics/aggregate")
print(json.dumps(m, indent=2))

print("\n=== /api/tasks/library ===")
lib = get("/api/tasks/library")
print(f"Total tasks: {len(lib)}")
for t in lib[:4]:
    print(f"  {t['task_id']:<14}  {t['category']:<18}  {t['difficulty']}")
