"""Show per-pair scores for ALL fixtures with the current formula."""
import json, math, subprocess

fixtures = [
    ("fixtures/run_competitive.jsonl",             "Competitive"),
    ("fixtures/run_cartel.jsonl",                  "Cartel realistic ~5%"),
    ("fixtures/run_cartel_extreme.jsonl",          "Cartel extreme ~78%"),
    ("fixtures/run_legitimate_coordination.jsonl", "Legitimate Coordination"),
]

for path, name in fixtures:
    result = subprocess.run(
        [".venv/Scripts/python.exe", "-m", "detector.score", path],
        capture_output=True, text=True, cwd="."
    )
    assessments = [json.loads(l) for l in result.stdout.strip().splitlines() if l.strip()]
    print(f"\n=== {name} ===")
    print(f"  {'Pair':<14} {'Score':>5}  {'Verdict':<8}  {'gap_value':>10}  {'sync_value':>10}")
    seen = set()
    for a in sorted(assessments, key=lambda x: (-x["risk_score"], str(x["group"]))):
        key = tuple(a["group"])
        if key in seen: continue
        seen.add(key)
        gv = a["signals"]["counterfactual_gap"]["value"]
        sv = a["signals"]["sync_under_shock"]["value"]
        print(f"  {str(a['group']):<14} {a['risk_score']:>5}  {a['verdict']:<8}  {gv:>10.4f}  {sv:>10.4f}")

# Also compute what tanh would give for the cartel pair
print("\n=== tanh normalization preview ===")
GAP_REF = 0.05
for label, raw_gap in [("Cartel 5%", 0.0505), ("Cartel 78%", 0.78), ("Competitive", 0.001)]:
    tanh_val = math.tanh(raw_gap / GAP_REF)
    sync = 0.8095 if "Cartel" in label else 0.6
    score = round((tanh_val * 0.60 + sync * 0.40) * 100)
    print(f"  {label:<16}  raw={raw_gap:.4f}  tanh_val={tanh_val:.4f}  est_score={score}")
