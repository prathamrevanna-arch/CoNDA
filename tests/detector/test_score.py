"""Unit and integration tests for detector/score.py."""

import json
from pathlib import Path
import time
from detector.score import _cli_main, score_run, score_window


def _make_sample_ticks(n: int = 100, agents=("A1", "A2"), price: float = 104.3, ref_price: float = 100.0):
    ticks = []
    for i in range(n):
        ag = agents[i % len(agents)]
        ticks.append({
            "run_id": "r_test_01",
            "t": 100 + i,
            "event": "quote",
            "agent_id": ag,
            "side": "ask",
            "price": price,
            "quantity": 5.0,
            "pool": {
                "reserve_x": 10000.0,
                "reserve_y": 10000.0 * ref_price,
                "fee_bps": 0,
            },
            "oracle_price": ref_price,
            "shock": None,
        })
    return ticks


def test_imports_successfully():
    from detector.score import score_run, score_window
    assert callable(score_run)
    assert callable(score_window)


def test_score_run_accepts_iterable_and_schema():
    ticks = _make_sample_ticks(100)
    # Pass as generator iterable
    gen = (t for t in ticks)
    results = list(score_run(gen, window_size=100, stride=25))
    assert len(results) >= 1

    first = results[0]
    expected_keys = {
        "run_id",
        "window_start",
        "window_end",
        "group",
        "risk_score",
        "verdict",
        "signals",
        "counterfactual",
        "evidence_hash",
        "computed_ms",
    }
    assert expected_keys.issubset(first.keys())
    assert first["run_id"] == "r_test_01"
    assert first["group"] == ["A1", "A2"]
    assert isinstance(first["risk_score"], int)
    assert first["verdict"] in ("LOW", "MEDIUM", "HIGH")
    assert "counterfactual_gap" in first["signals"]
    assert "sync_under_shock" in first["signals"]


def test_rolling_windows_and_stride():
    # 150 ticks: with window_size 100 and stride 25:
    # 0-99 (start 100, end 199)
    # 25-124 (start 125, end 224)
    # 50-149 (start 150, end 249)
    ticks = _make_sample_ticks(150)
    results = list(score_run(ticks, window_size=100, stride=25))
    # 3 windows, 1 pair each -> 3 results
    assert len(results) == 3
    assert results[0]["window_start"] == 100
    assert results[1]["window_start"] == 125
    assert results[2]["window_start"] == 150


def test_pair_enumeration_and_deterministic_order():
    # 3 agents in 100 ticks -> exactly 3 pairs: (A1, A2), (A1, A3), (A2, A3)
    ticks = _make_sample_ticks(100, agents=("A3", "A1", "A2"))
    results = list(score_run(ticks, window_size=100, stride=25))
    assert len(results) == 3
    groups = [r["group"] for r in results]
    assert groups == [["A1", "A2"], ["A1", "A3"], ["A2", "A3"]]


def test_contributions_sum_exactly_to_risk_score():
    ticks = _make_sample_ticks(100, price=105.5)
    results = list(score_run(ticks, window_size=100))
    for res in results:
        sig_contributions = [s["contribution"] for s in res["signals"].values()]
        assert sum(sig_contributions) == res["risk_score"]


def test_verdict_threshold_integration():
    # Competitive quotes -> risk score < 40 -> LOW
    comp_ticks = _make_sample_ticks(100, price=100.0, ref_price=100.0)
    res_comp = score_window(comp_ticks)
    assert res_comp["risk_score"] < 40
    assert res_comp["verdict"] == "LOW"


def test_evidence_hash_sha256_and_deterministic():
    ticks = _make_sample_ticks(100)
    res1 = score_window(ticks)
    res2 = score_window(ticks)

    h1 = res1["evidence_hash"]
    h2 = res2["evidence_hash"]

    assert h1 == h2
    assert h1.startswith("0x")
    # '0x' + 64 hex chars = 66 chars
    assert len(h1) == 66


def test_evidence_hash_changes_when_signals_change():
    ticks1 = _make_sample_ticks(100, price=100.0)
    ticks2 = _make_sample_ticks(100, price=120.0)

    res1 = score_window(ticks1)
    res2 = score_window(ticks2)

    assert res1["evidence_hash"] != res2["evidence_hash"]


def test_counterfactual_summary_populated():
    ticks = _make_sample_ticks(100, price=104.1, ref_price=99.8)
    res = score_window(ticks)
    cf = res["counterfactual"]
    assert "reference_price" in cf
    assert "observed_price" in cf
    assert "gap_pct" in cf
    assert cf["reference_price"] > 0
    assert cf["observed_price"] > 0


def test_empty_and_insufficient_ticks():
    assert list(score_run([])) == []

    res_empty = score_window([])
    assert res_empty["risk_score"] == 0
    assert res_empty["verdict"] == "LOW"

    # Fewer than 100 ticks (e.g. 40 ticks)
    short_ticks = _make_sample_ticks(40)
    results_short = list(score_run(short_ticks, window_size=100))
    # Yields 1 window with available ticks safely
    assert len(results_short) == 1
    assert results_short[0]["group"] == ["A1", "A2"]


def test_single_agent_no_pair_assessment():
    single_agent_ticks = [
        {"run_id": "r1", "t": i, "event": "quote", "agent_id": "A1", "price": 100.0}
        for i in range(100)
    ]
    # In score_run: no candidate pairs, so no pair assessment yielded
    assert list(score_run(single_agent_ticks)) == []

    # In score_window: returns safe LOW assessment
    res = score_window(single_agent_ticks)
    assert res["risk_score"] == 0
    assert res["verdict"] == "LOW"
    assert res["group"] == ["A1"]


def test_malformed_input_does_not_crash():
    malformed = [
        "not a dict",
        None,
        {"t": float("nan"), "event": "quote", "price": "invalid"},
        {"agent_id": None},
        {"run_id": "r1", "t": 10, "event": "quote", "agent_id": "A1", "price": float("inf")},
        {"run_id": "r1", "t": 11, "event": "quote", "agent_id": "A2", "price": -50.0},
    ]
    # 1. Must not crash
    res = score_window(malformed)
    # 2. Returned verdict is LOW
    assert res["verdict"] == "LOW"
    # 3. Returned risk_score is 0
    assert res["risk_score"] == 0
    # 4. Assessment contains the word 'error' in an existing note/explanation field
    assert "error" in res["signals"]["counterfactual_gap"]["explanation"].lower()
    assert "error" in res["signals"]["sync_under_shock"]["explanation"].lower()


def test_malformed_inputs_comprehensive():
    # Various malformed input variants: None, non-iterable, list of invalid types
    cases = [
        None,
        "string_instead_of_list",
        12345,
        [None, "invalid_item"],
        [{"not_a_valid_tick": True}],
    ]
    for case in cases:
        # 1. Never raises
        res = score_window(case)
        # 2. Returned verdict is LOW
        assert res["verdict"] == "LOW"
        # 3. Returned risk_score is 0
        assert res["risk_score"] == 0
        # 4. Assessment contains the word 'error' in existing explanation field
        explanations = [
            s["explanation"] for s in res["signals"].values() if "explanation" in s
        ]
        assert len(explanations) > 0
        assert any("error" in exp.lower() for exp in explanations)


def test_all_agents_reacting_together_low_sync_risk():
    # Public shock at t=100. All agents react within 1 tick.
    ticks = [
        {"t": 100, "event": "shock", "shock": {"type": "jump"}, "oracle_price": 100.0, "pool": {"reserve_x": 1000, "reserve_y": 100000, "fee_bps": 0}},
        {"t": 101, "event": "quote", "agent_id": "A1", "price": 100.0, "oracle_price": 100.0, "pool": {"reserve_x": 100, "reserve_y": 10000, "fee_bps": 0}},
        {"t": 101, "event": "quote", "agent_id": "A2", "price": 100.0, "oracle_price": 100.0, "pool": {"reserve_x": 100, "reserve_y": 10000, "fee_bps": 0}},
        {"t": 102, "event": "quote", "agent_id": "A3", "price": 100.0, "oracle_price": 100.0, "pool": {"reserve_x": 100, "reserve_y": 10000, "fee_bps": 0}},
        {"t": 102, "event": "quote", "agent_id": "A4", "price": 100.0, "oracle_price": 100.0, "pool": {"reserve_x": 100, "reserve_y": 10000, "fee_bps": 0}},
    ]
    res = score_window(ticks, group=("A1", "A2"))
    # Sync under shock should NOT be high
    sync_val = res["signals"]["sync_under_shock"]["value"]
    assert sync_val <= 0.30


def test_latency_target_under_50ms():
    # 6 agents in a 100-tick window (15 candidate pairs)
    agents = [f"A{i}" for i in range(6)]
    ticks = _make_sample_ticks(100, agents=agents)

    start = time.perf_counter()
    assessments = list(score_run(ticks, window_size=100))
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    # 15 pairs evaluated
    assert len(assessments) == 15
    # Full window evaluation for all 15 pairs must easily be under 50ms
    assert elapsed_ms < 50.0, f"Scoring 15 pairs took {elapsed_ms}ms, exceeded 50ms target"


def test_cli_execution_jsonl_and_pretty(tmp_path: Path, capsys):
    test_file = tmp_path / "test_run.jsonl"
    ticks = _make_sample_ticks(100)
    test_file.write_text("\n".join(json.dumps(t) for t in ticks), encoding="utf-8")

    # Default JSONL output
    exit_code = _cli_main([str(test_file)])
    assert exit_code == 0
    captured = capsys.readouterr().out
    lines = [line for line in captured.strip().split("\n") if line]
    assert len(lines) >= 1
    # First line must parse as JSON
    parsed = json.loads(lines[0])
    assert parsed["run_id"] == "r_test_01"

    # Pretty output
    exit_code_pretty = _cli_main([str(test_file), "--pretty"])
    assert exit_code_pretty == 0
    captured_pretty = capsys.readouterr().out
    # Pretty output contains indented newlines
    assert "{\n  \"run_id\"" in captured_pretty
