# CoNDA — Collusion aNd tacit-coordination Detector

Adversarially evaluated runtime system for detecting, explaining, and challenging suspicious coordination among autonomous DeFi trading agents.

---

## Detector Module (Member 2)

Scores agent pairs **0–100** for suspected tacit collusion based on two behavioral signals:

| Signal | Weight | What it measures |
|--------|--------|-----------------|
| `counterfactual_gap` | 0.60 | Persistent price elevation above the AMM competitive reference |
| `sync_under_shock` | 0.40 | Anomalously tight re-quoting timing after a public market shock vs. all-pairs baseline |

**Verdict thresholds:** LOW < 40 · MEDIUM 40–69 · HIGH ≥ 70

---

## Fixture Evaluation Results (measured, not estimated)

> Run: `.venv\Scripts\python.exe -m detector.score fixtures/<name>.jsonl`

| Fixture | Description | Top Pair | Score | Verdict | Target |
|---------|-------------|----------|-------|---------|--------|
| `run_competitive.jsonl` | 4 agents, staggered reaction times, prices at reference | A1/A4 | **24** | LOW | ≤ 35 ✅ |
| `run_cartel.jsonl` | A2/A3 persistently **~5% above reference**, react within 1 tick vs. 18-tick baseline | A2/A3 | **78** | HIGH | ≥ 70 ✅ |
| `run_cartel_extreme.jsonl` | A2/A3 at **~78% above reference** — easy sanity-check case | A2/A3 | **92** | HIGH | ≥ 70 ✅ |
| `run_legitimate_coordination.jsonl` | All agents react simultaneously (market-wide) but at fair prices | A1/A2 | **8** | LOW | ≤ 45 ✅ |

**pytest:** 95 passed, 0 failed

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run detector on a JSONL market run
python -m detector.score fixtures/run_cartel.jsonl --pretty

# Generate all synthetic fixtures
python generate_fixtures.py

# Run test suite
pytest tests/detector/ -q
```

---

## Architecture

```
JSONL ticks → load.py → windows.py (100-tick rolling, stride 25)
                              │
                    ┌─────────┴──────────┐
              gap.py (price gap)   sync.py (shock timing)
                    └─────────┬──────────┘
                         aggregate.py → score 0–100
                              │
                         explain.py → human text
                              │
                         score.py (public API + CLI)
```

See [`detector/CoNDA_detector_deep_dive.md`](detector/CoNDA_detector_deep_dive.md) for the full technical reference.
