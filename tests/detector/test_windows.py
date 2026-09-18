"""Unit tests for detector/windows.py."""

from detector.windows import slice_windows, extract_agents, extract_run_id


def test_empty_ticks():
    windows = list(slice_windows([]))
    assert windows == []


def test_fewer_than_window_size():
    ticks = [
        {"run_id": "r_test", "t": i, "agent_id": f"A{i % 2}", "event": "quote"}
        for i in range(40)
    ]
    windows = list(slice_windows(ticks, window_size=100, stride=25))
    assert len(windows) == 1
    w = windows[0]
    assert w.run_id == "r_test"
    assert w.window_start == 0
    assert w.window_end == 39
    assert len(w.ticks) == 40
    assert w.agents == ["A0", "A1"]


def test_standard_window_size_and_stride():
    # 250 ticks, each with a unique t (1000..1249).
    # Under t-based windowing with window_size=100, stride=25:
    # 250 unique t values -> starts at t-indices 0,25,50,...,150 = 7 windows
    #   Window 0:  t=[1000,1099], t-idx 0..99
    #   Window 1:  t=[1025,1124], t-idx 25..124
    #   ...
    #   Window 6:  t=[1150,1249], t-idx 150..249
    ticks = [
        {"run_id": "r_long", "t": 1000 + i, "agent_id": "A1" if i % 2 == 0 else "A2", "event": "quote"}
        for i in range(250)
    ]
    windows = list(slice_windows(ticks, window_size=100, stride=25))
    assert len(windows) == 7

    # First window: t-values 1000..1099
    assert windows[0].start_idx == 0
    assert windows[0].end_idx == 99
    assert windows[0].window_start == 1000
    assert windows[0].window_end == 1099
    assert len(windows[0].ticks) == 100

    # Second window: t-values 1025..1124
    assert windows[1].start_idx == 25
    assert windows[1].end_idx == 124
    assert windows[1].window_start == 1025
    assert windows[1].window_end == 1124

    # Last window: t-indices 150..249
    assert windows[-1].start_idx == 150
    assert windows[-1].end_idx == 249


def test_extract_agents_ignores_null_and_duplicates():
    ticks = [
        {"agent_id": "A3"},
        {"agent_id": "A1"},
        {"agent_id": None},
        {},
        {"agent_id": "A3"},
        {"agent_id": "A2"},
    ]
    agents = extract_agents(ticks)
    assert agents == ["A1", "A2", "A3"]
