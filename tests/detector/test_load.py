"""Unit tests for detector/load.py."""

import json
from pathlib import Path
from detector.load import iter_ticks, load_ticks


def test_load_ticks_from_iterable():
    raw_data = [
        {"run_id": "r1", "t": 1, "event": "quote", "price": 100.0},
        {"run_id": "r1", "t": 2, "event": "trade", "price": 100.2},
    ]
    ticks = load_ticks(raw_data)
    assert len(ticks) == 2
    assert ticks[0]["event"] == "quote"
    assert ticks[1]["price"] == 100.2


def test_load_ticks_from_jsonl_file(tmp_path: Path):
    file_path = tmp_path / "test_run.jsonl"
    lines = [
        '{"run_id": "r_01", "t": 10, "event": "quote", "price": 101.5}',
        "",  # Blank line
        "   ",  # Whitespace blank line
        '{"run_id": "r_01", "t": 11, "event": "shock", "shock": {"type": "jump"}}',
        '{"invalid json line...',  # Malformed JSON
        '42',  # Non-dict JSON
        '{"run_id": "r_01", "t": 12, "event": "quote", "price": 101.8}',
    ]
    file_path.write_text("\n".join(lines), encoding="utf-8")

    ticks = load_ticks(file_path)
    assert len(ticks) == 3
    assert ticks[0]["t"] == 10
    assert ticks[1]["event"] == "shock"
    assert ticks[2]["price"] == 101.8


def test_load_ticks_nonexistent_file(tmp_path: Path):
    missing_path = tmp_path / "does_not_exist.jsonl"
    ticks = load_ticks(missing_path)
    assert ticks == []


def test_iter_ticks_streaming(tmp_path: Path):
    file_path = tmp_path / "stream.jsonl"
    file_path.write_text('{"run_id": "r1", "t": 1, "event": "quote"}\n', encoding="utf-8")
    iterator = iter_ticks(file_path)
    item = next(iterator)
    assert item["run_id"] == "r1"
