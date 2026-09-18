"""
Step 3 Integration-Readiness Tests for Member 1.

Covers:
A. Logger (writing, round-trip reading, deterministic format)
B. Validator (validating fixtures, rejecting malformed data, schema enforcement)
C. CLI runner (sim.run and sim.validate execution)
D. Determinism (byte-identical files for identical seeds, seed sensitivity)
E. All three scenarios (competitive, cartel, legit)
F. Import cleanliness (no side effects on import)
"""

import json
import os
import pathlib
import subprocess
import sys
import tempfile

from sim import run_sim
from sim.logger import JSONLWriter, read_jsonl, write_jsonl, write_run_meta
from sim.run import run_cli
from sim.validate import (
    ValidationError,
    main as validate_main,
    validate_file,
    validate_record,
)


def test_logger_write_and_read():
    """Test logger writes clean JSONL and reads back accurately."""
    sample_records = [
        {
            "run_id": "r_test_01",
            "t": 0,
            "event": "meta",
            "agent_id": None,
            "side": None,
            "price": None,
            "quantity": None,
            "capital": None,
            "pnl": None,
            "pool": {"reserve_x": 1000.0, "reserve_y": 100000.0, "fee_bps": 30},
            "oracle_price": 100.0,
            "shock": None,
        },
        {
            "run_id": "r_test_01",
            "t": 1,
            "event": "quote",
            "agent_id": "agent_1",
            "side": "bid",
            "price": 100.0,
            "quantity": 10.0,
            "capital": 50000.0,
            "pnl": 0.0,
            "pool": {"reserve_x": 1000.0, "reserve_y": 100000.0, "fee_bps": 30},
            "oracle_price": 100.0,
            "shock": None,
        },
    ]

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = pathlib.Path(tmpdir) / "sub" / "test.jsonl"
        written = write_jsonl(sample_records, out_path)
        assert written == 2
        assert out_path.exists()

        # Read back
        loaded = read_jsonl(out_path)
        assert loaded == sample_records

        # Ensure no empty or extra lines
        with open(out_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        for line in lines:
            assert line.endswith("\n")
            json.loads(line)  # Must be strictly parseable per line

    print("PASS  test_logger_write_and_read")


def test_logger_write_meta():
    """Test writing run_meta.json."""
    meta_dict = {
        "run_id": "r_comp_01",
        "scenario": "competitive",
        "seed": 42,
        "ticks": 100,
        "agents": [{"agent_id": "c1", "agent_class": "competitive"}],
        "shocks": [{"t": 40, "type": "oracle_jump", "magnitude": 0.05}],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        meta_path = pathlib.Path(tmpdir) / "run_meta.json"
        write_run_meta(meta_dict, meta_path)
        assert meta_path.exists()
        with open(meta_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == meta_dict

    print("PASS  test_logger_write_meta")


def test_validator_fixtures_and_runs():
    """Verify validator accepts all 3 fixtures and all 3 sample runs."""
    fixture_files = [
        "fixtures/run_competitive.jsonl",
        "fixtures/run_cartel.jsonl",
        "fixtures/run_legit.jsonl",
    ]
    for fp in fixture_files:
        assert pathlib.Path(fp).exists(), f"Missing fixture file: {fp}"
        count = validate_file(fp)
        assert count > 0, f"Fixture {fp} was empty"

    sample_runs = [
        "runs/competitive_seed42.jsonl",
        "runs/cartel_seed42.jsonl",
        "runs/legit_seed42.jsonl",
    ]
    for sp in sample_runs:
        assert pathlib.Path(sp).exists(), f"Missing sample run: {sp}"
        count = validate_file(sp)
        assert count > 0, f"Sample run {sp} was empty"

    print("PASS  test_validator_fixtures_and_runs")


def test_validator_reject_malformed():
    """Verify validator catches and rejects malformed records."""
    valid_base = {
        "run_id": "r_01",
        "t": 1,
        "event": "trade",
        "agent_id": "A1",
        "side": "bid",
        "price": 100.0,
        "quantity": 5.0,
        "capital": 50000.0,
        "pnl": 0.0,
        "pool": {"reserve_x": 1000.0, "reserve_y": 100000.0, "fee_bps": 30},
        "oracle_price": 100.0,
        "shock": None,
    }

    # 1. Missing required key
    bad1 = dict(valid_base)
    del bad1["oracle_price"]
    try:
        validate_record(bad1, 1)
        assert False, "Should fail on missing oracle_price"
    except ValidationError:
        pass

    # 2. Unexpected extra key
    bad2 = dict(valid_base)
    bad2["detector_score"] = 0.99
    try:
        validate_record(bad2, 1)
        assert False, "Should fail on unexpected field"
    except ValidationError:
        pass

    # 3. Invalid event
    bad3 = dict(valid_base)
    bad3["event"] = "collusion_detected"
    try:
        validate_record(bad3, 1)
        assert False, "Should fail on invalid event"
    except ValidationError:
        pass

    # 4. Invalid side
    bad4 = dict(valid_base)
    bad4["side"] = "hold"
    try:
        validate_record(bad4, 1)
        assert False, "Should fail on invalid side"
    except ValidationError:
        pass

    # 5. Type violation (bool for integer tick)
    bad5 = dict(valid_base)
    bad5["t"] = True
    try:
        validate_record(bad5, 1)
        assert False, "Should fail when bool is used for tick"
    except ValidationError:
        pass

    # 6. Negative pool reserves
    bad6 = dict(valid_base)
    bad6["pool"] = {"reserve_x": -10.0, "reserve_y": 1000.0, "fee_bps": 30}
    try:
        validate_record(bad6, 1)
        assert False, "Should fail on negative pool reserves"
    except ValidationError:
        pass

    # 7. Non-null agent fields on shock event
    bad7 = dict(valid_base)
    bad7["event"] = "shock"
    bad7["shock"] = {"type": "oracle_jump", "magnitude": 0.05}
    # agent_id is still "A1"
    try:
        validate_record(bad7, 1)
        assert False, "Should fail when shock record contains agent_id"
    except ValidationError:
        pass

    # 8. Malformed JSON file
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".jsonl") as f:
        f.write("{bad json\n")
        bad_json_path = f.name
    try:
        try:
            validate_file(bad_json_path)
            assert False, "Should fail on malformed JSON"
        except ValidationError:
            pass
    finally:
        os.remove(bad_json_path)

    # 9. Empty file
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".jsonl") as f:
        empty_path = f.name
    try:
        try:
            validate_file(empty_path)
            assert False, "Should fail on empty file"
        except ValidationError:
            pass
    finally:
        os.remove(empty_path)

    print("PASS  test_validator_reject_malformed")


def test_cli_runner_and_validator():
    """Test CLI execution for runner and validator."""
    with tempfile.TemporaryDirectory() as tmpdir:
        out_file = str(pathlib.Path(tmpdir) / "cli_comp.jsonl")
        meta_file = str(pathlib.Path(tmpdir) / "cli_meta.json")

        # 1. Run CLI programmatically
        exit_code = run_cli(["competitive", "--seed", "42", "--output", out_file, "--meta-output", meta_file])
        assert exit_code == 0
        assert os.path.exists(out_file)
        assert os.path.exists(meta_file)

        # 2. Validate using validator CLI entry point
        val_code = validate_main([out_file])
        assert val_code == 0

        # 3. CLI runner with unknown scenario should fail
        fail_code = run_cli(["nonexistent_scenario", "--seed", "42"])
        assert fail_code != 0

        # 4. Validator on non-existent file should fail
        val_fail = validate_main(["nonexistent_file.jsonl"])
        assert val_fail != 0

    print("PASS  test_cli_runner_and_validator")


def test_byte_level_determinism():
    """Verify byte-for-byte reproducibility of JSONL outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = str(pathlib.Path(tmpdir) / "run1.jsonl")
        p2 = str(pathlib.Path(tmpdir) / "run2.jsonl")
        p3 = str(pathlib.Path(tmpdir) / "run3_diff_seed.jsonl")

        write_jsonl(run_sim("cartel", seed=42), p1)
        write_jsonl(run_sim("cartel", seed=42), p2)
        write_jsonl(run_sim("cartel", seed=99), p3)

        with open(p1, "rb") as f1, open(p2, "rb") as f2:
            bytes1 = f1.read()
            bytes2 = f2.read()
        assert bytes1 == bytes2, "Same seed did not produce byte-identical JSONL files"

        with open(p3, "rb") as f3:
            bytes3 = f3.read()
        assert bytes1 != bytes3, "Different seeds unexpectedly produced identical files"

    print("PASS  test_byte_level_determinism")


def test_import_cleanliness():
    """Verify sim and sim.engine import with no side effects or file creation."""
    # Test through fresh subprocess
    cmd = [
        sys.executable,
        "-c",
        "import sys, sim, sim.logger, sim.validate, sim.run; sys.exit(0)",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert res.stdout == ""
    print("PASS  test_import_cleanliness")


if __name__ == "__main__":
    tests = [
        test_logger_write_and_read,
        test_logger_write_meta,
        test_validator_fixtures_and_runs,
        test_validator_reject_malformed,
        test_cli_runner_and_validator,
        test_byte_level_determinism,
        test_import_cleanliness,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as err:
            print(f"FAIL  {test.__name__}: {err}")
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    if failed:
        sys.exit(1)
    else:
        print("All Step 3 tests passed!")
        sys.exit(0)
