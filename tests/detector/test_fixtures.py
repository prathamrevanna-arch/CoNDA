"""Unit and integration tests for synthetic evaluation fixtures in CoNDA."""

import inspect
import json
from pathlib import Path
from detector.load import load_ticks
from detector.score import _cli_main, score_run
import detector.score as score_module
import detector.signals.gap as gap_module
import detector.signals.sync as sync_module
import detector.aggregate as agg_module
import detector.counterfactual as cf_module

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

FIXTURE_NAMES = [
    "run_competitive.jsonl",
    "run_cartel.jsonl",
    "run_legitimate_coordination.jsonl",
]


def test_all_three_fixture_files_exist():
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        assert fixture_path.is_file(), f"Fixture file {name} does not exist in {FIXTURES_DIR}"


def test_fixtures_are_valid_jsonl_and_dict_ticks():
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        with open(fixture_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                raw = line.strip()
                if not raw:
                    continue
                data = json.loads(raw)
                assert isinstance(data, dict), f"Line {line_no} in {name} is not a dict"
                assert "event" in data, f"Line {line_no} in {name} missing 'event'"


def test_fixtures_have_enough_ticks_and_agents():
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        ticks = load_ticks(fixture_path)
        assert len(ticks) >= 100, f"Fixture {name} has fewer than 100 ticks ({len(ticks)})"

        agents = {t["agent_id"] for t in ticks if "agent_id" in t and t["agent_id"]}
        assert len(agents) >= 3, f"Fixture {name} has fewer than 3 agents: {agents}"


def test_fixtures_numerical_validity():
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        ticks = load_ticks(fixture_path)
        for idx, t in enumerate(ticks):
            if t.get("event") == "quote":
                assert t.get("price") is not None and t["price"] > 0
                assert t.get("quantity") is not None and t["quantity"] > 0
                if "pool" in t and t["pool"]:
                    pool = t["pool"]
                    assert pool["reserve_x"] > 0
                    assert pool["reserve_y"] > 0
                    assert pool["fee_bps"] >= 0


def test_shock_events_validity():
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        ticks = load_ticks(fixture_path)
        shocks = [t for t in ticks if t.get("event") == "shock"]
        assert len(shocks) >= 1, f"Fixture {name} contains no shock events"
        for s in shocks:
            assert isinstance(s.get("shock"), dict), f"Malformed shock object in {name}: {s}"


def test_cli_processes_each_fixture(capsys):
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        exit_code = _cli_main([str(fixture_path)])
        assert exit_code == 0, f"CLI exited with code {exit_code} on {name}"
        captured = capsys.readouterr().out
        lines = [line.strip() for line in captured.strip().split("\n") if line.strip()]
        assert len(lines) >= 1, f"CLI produced no output for {name}"
        # Validate first line parses as valid output schema
        record = json.loads(lines[0])
        assert "run_id" in record
        assert "risk_score" in record
        assert "verdict" in record
        assert "evidence_hash" in record


def test_detector_output_contract_on_fixtures():
    for name in FIXTURE_NAMES:
        fixture_path = FIXTURES_DIR / name
        ticks = load_ticks(fixture_path)
        results = list(score_run(ticks))
        assert len(results) > 0, f"No assessments generated for {name}"

        for r in results:
            assert "run_id" in r
            assert "window_start" in r
            assert "window_end" in r
            assert "group" in r and len(r["group"]) == 2
            assert "risk_score" in r and 0 <= r["risk_score"] <= 100
            assert r["verdict"] in ("LOW", "MEDIUM", "HIGH")
            assert "signals" in r
            assert "evidence_hash" in r and r["evidence_hash"].startswith("0x")
            assert len(r["evidence_hash"]) == 66
            assert "computed_ms" in r

            # Check contributions sum exactly to risk_score
            contributions = [s["contribution"] for s in r["signals"].values()]
            assert sum(contributions) == r["risk_score"]


def test_no_ground_truth_or_meta_accessed():
    modules_to_inspect = [
        score_module,
        gap_module,
        sync_module,
        agg_module,
        cf_module,
    ]
    forbidden_tokens = ["run_meta", "agent_class", "explicit_cartel", "legitimate_coordination"]

    for mod in modules_to_inspect:
        source = inspect.getsource(mod)
        for token in forbidden_tokens:
            assert token not in source, f"Forbidden ground-truth token '{token}' found in {mod.__name__}"
