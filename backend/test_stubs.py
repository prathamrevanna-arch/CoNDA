"""
backend/test_stubs.py
---------------------
Tests for the Step-1 development stubs.

Run from the repository root:
    python -m pytest backend/test_stubs.py -v

Tests are deliberately written to pass regardless of the current working
directory, relying only on stdlib and the two stub modules.
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import Iterator

import pytest

# ---------------------------------------------------------------------------
# Ensure the repository root and backend/ are importable regardless of cwd.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent   # …/CoNDA/
_BACKEND   = Path(__file__).resolve().parent           # …/CoNDA/backend/

for _p in (_REPO_ROOT, _BACKEND):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

from sim_stub import run_sim          # noqa: E402
from detector_stub import score_run   # noqa: E402

# ---------------------------------------------------------------------------
# Frozen field sets
# ---------------------------------------------------------------------------
_TICK_FIELDS = frozenset({
    "run_id", "t", "event", "agent_id", "side",
    "price", "quantity", "capital", "pnl",
    "pool", "oracle_price", "shock",
})
_POOL_FIELDS = frozenset({"reserve_x", "reserve_y", "fee_bps"})

_ASSESSMENT_FIELDS = frozenset({
    "run_id", "window_start", "window_end", "group",
    "risk_score", "verdict", "signals",
    "counterfactual", "evidence_hash", "computed_ms",
})
_COUNTERFACTUAL_FIELDS = frozenset({
    "reference_price", "observed_price", "gap_pct",
})

_EVIDENCE_HASH_RE = re.compile(r"^0x[0-9a-f]{64}$")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _collect_ticks(scenario: str = "default", seed: int = 1) -> list[dict]:
    """Collect all ticks without waiting for the 50 ms sleep.

    We monkeypatch time.sleep inside the stub so tests run in < 1 s.
    """
    import time as _time
    original_sleep = _time.sleep
    _time.sleep = lambda _: None   # disable delay for tests
    try:
        ticks = list(run_sim(scenario, seed))
    finally:
        _time.sleep = original_sleep
    return ticks


# ---------------------------------------------------------------------------
# sim_stub tests
# ---------------------------------------------------------------------------

class TestSimStub:

    def test_run_sim_returns_ticks(self):
        """run_sim('default', 1) must produce at least one tick."""
        ticks = _collect_ticks()
        assert len(ticks) > 0, "run_sim produced no ticks"

    def test_at_least_30_ticks(self):
        """Fixture must contain at least 30 MarketTick records."""
        ticks = _collect_ticks()
        assert len(ticks) >= 30, (
            f"Expected >= 30 ticks, got {len(ticks)}"
        )

    def test_every_tick_has_required_fields(self):
        """Every tick dict must contain all MarketTick fields."""
        ticks = _collect_ticks()
        for i, tick in enumerate(ticks):
            missing = _TICK_FIELDS - tick.keys()
            assert not missing, (
                f"Tick #{i} missing fields: {missing}\ntick={tick}"
            )

    def test_pool_field_structure(self):
        """The 'pool' sub-dict must contain reserve_x, reserve_y, fee_bps."""
        ticks = _collect_ticks()
        for i, tick in enumerate(ticks):
            pool = tick.get("pool", {})
            missing = _POOL_FIELDS - pool.keys()
            assert not missing, (
                f"Tick #{i} pool missing fields: {missing}"
            )

    def test_run_sim_yields_dicts_not_strings(self):
        """run_sim must yield Python dicts, not raw JSON strings."""
        ticks = _collect_ticks()
        for i, tick in enumerate(ticks):
            assert isinstance(tick, dict), (
                f"Tick #{i} is {type(tick).__name__}, expected dict"
            )

    def test_run_sim_is_deterministic(self):
        """Calling run_sim twice with the same args produces identical output."""
        ticks_a = _collect_ticks(seed=42)
        ticks_b = _collect_ticks(seed=42)
        assert ticks_a == ticks_b, "run_sim is not deterministic"

    def test_fixture_contains_a1_a2_a3(self):
        """Fixture must include agents A1, A2, and A3."""
        ticks = _collect_ticks()
        agents = {t["agent_id"] for t in ticks}
        for agent in ("A1", "A2", "A3"):
            assert agent in agents, (
                f"Agent {agent!r} not found in fixture. Found: {agents}"
            )

    def test_unknown_scenario_raises_value_error(self):
        """Requesting an unknown scenario must raise ValueError immediately."""
        with pytest.raises(ValueError, match="Unknown scenario"):
            # Exhaust the generator to trigger the error.
            list(run_sim("nonexistent_scenario_xyz", seed=0))

    def test_run_sim_is_synchronous_iterator(self):
        """run_sim must return a synchronous iterator (not a coroutine)."""
        import inspect
        gen = run_sim("default", 1)
        assert not inspect.iscoroutine(gen), (
            "run_sim returned a coroutine; it must be a synchronous generator"
        )
        assert hasattr(gen, "__next__"), (
            "run_sim return value is not an iterator"
        )
        # Clean up without consuming (avoids sleeping).
        gen.close()


# ---------------------------------------------------------------------------
# detector_stub tests
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def ticks_and_assessments():
    """Return (ticks, assessments) for the default fixture (module-scoped)."""
    ticks = _collect_ticks()
    assessments = list(score_run(ticks))
    return ticks, assessments


class TestDetectorStub:

    def test_score_run_produces_assessments(self, ticks_and_assessments):
        """score_run(ticks) must produce at least one RiskAssessment."""
        _, assessments = ticks_and_assessments
        assert len(assessments) > 0, "score_run produced no assessments"

    def test_multiple_assessment_windows(self, ticks_and_assessments):
        """score_run must produce more than one assessment window."""
        _, assessments = ticks_and_assessments
        assert len(assessments) > 1, (
            f"Expected > 1 assessment windows, got {len(assessments)}"
        )

    def test_every_assessment_has_required_fields(self, ticks_and_assessments):
        """Every assessment dict must contain all RiskAssessment fields."""
        _, assessments = ticks_and_assessments
        for i, a in enumerate(assessments):
            missing = _ASSESSMENT_FIELDS - a.keys()
            assert not missing, (
                f"Assessment #{i} missing fields: {missing}\nassessment={a}"
            )

    def test_counterfactual_structure(self, ticks_and_assessments):
        """The 'counterfactual' sub-dict must have the required fields."""
        _, assessments = ticks_and_assessments
        for i, a in enumerate(assessments):
            cf = a.get("counterfactual", {})
            missing = _COUNTERFACTUAL_FIELDS - cf.keys()
            assert not missing, (
                f"Assessment #{i} counterfactual missing fields: {missing}"
            )

    def test_risk_scores_increase_over_run(self, ticks_and_assessments):
        """Risk scores must be non-decreasing across the window sequence."""
        _, assessments = ticks_and_assessments
        scores = [a["risk_score"] for a in assessments]
        for i in range(1, len(scores)):
            assert scores[i] >= scores[i - 1], (
                f"Risk score decreased at window {i}: "
                f"{scores[i - 1]} → {scores[i]}"
            )

    def test_final_risk_score_is_90(self, ticks_and_assessments):
        """The last assessment's risk_score must be exactly 90."""
        _, assessments = ticks_and_assessments
        final = assessments[-1]["risk_score"]
        assert final == 90, f"Expected final risk score 90, got {final}"

    def test_verdict_matches_score(self, ticks_and_assessments):
        """Verdict must match the score thresholds: <40 LOW, 40-69 MEDIUM, >=70 HIGH."""
        _, assessments = ticks_and_assessments
        for i, a in enumerate(assessments):
            score = a["risk_score"]
            verdict = a["verdict"]
            if score < 40:
                expected = "LOW"
            elif score < 70:
                expected = "MEDIUM"
            else:
                expected = "HIGH"
            assert verdict == expected, (
                f"Assessment #{i}: score={score} → expected verdict "
                f"{expected!r}, got {verdict!r}"
            )

    def test_evidence_hash_format(self, ticks_and_assessments):
        """evidence_hash must be 0x followed by exactly 64 hex characters."""
        _, assessments = ticks_and_assessments
        for i, a in enumerate(assessments):
            h = a.get("evidence_hash", "")
            assert _EVIDENCE_HASH_RE.match(h), (
                f"Assessment #{i}: invalid evidence_hash {h!r}. "
                "Expected 0x + 64 hex chars."
            )

    def test_score_run_accepts_generator_input(self):
        """score_run must accept a generator (lazy Iterable), not just a list."""
        ticks = _collect_ticks()

        def tick_gen():
            yield from ticks

        assessments = list(score_run(tick_gen()))
        assert len(assessments) > 0

    def test_score_run_empty_input(self):
        """score_run on an empty iterable must return an empty iterator."""
        assessments = list(score_run([]))
        assert assessments == [], (
            f"Expected [] for empty input, got {assessments}"
        )

    def test_score_run_is_synchronous_iterator(self):
        """score_run must return a synchronous iterator."""
        import inspect
        ticks = _collect_ticks()
        gen = score_run(iter(ticks))
        assert not inspect.iscoroutine(gen), (
            "score_run returned a coroutine; it must be a synchronous generator"
        )
        assert hasattr(gen, "__next__"), (
            "score_run return value is not an iterator"
        )

    def test_risk_score_ramp_covers_low_medium_high(self, ticks_and_assessments):
        """The ramp must pass through LOW, MEDIUM, and HIGH verdicts."""
        _, assessments = ticks_and_assessments
        verdicts = {a["verdict"] for a in assessments}
        assert "LOW" in verdicts,    "No LOW verdict in assessments"
        assert "HIGH" in verdicts,   "No HIGH verdict in assessments"

    def test_score_run_accepts_window_size_and_stride_kwargs(self):
        """score_run must accept window_size and stride kwargs for real detector compatibility."""
        ticks = _collect_ticks()
        assessments = list(score_run(ticks, window_size=100, stride=25))
        assert len(assessments) > 0


# ---------------------------------------------------------------------------
# Integration: stubs work when run from repo root
# ---------------------------------------------------------------------------

class TestImportFromRepoRoot:

    def test_modules_importable_from_repo_root(self):
        """sim_stub and detector_stub must import cleanly from repo root."""
        # Force re-import to verify path handling.
        for mod_name in ("sim_stub", "detector_stub"):
            mod = importlib.import_module(mod_name)
            assert hasattr(mod, "run_sim" if mod_name == "sim_stub" else "score_run"), (
                f"{mod_name} missing expected public function"
            )

    def test_fixture_path_resolves_independent_of_cwd(self, tmp_path, monkeypatch):
        """Fixture must load correctly even if cwd is changed to tmp_path."""
        monkeypatch.chdir(tmp_path)
        ticks = _collect_ticks()
        assert len(ticks) >= 30, (
            "Fixture path resolution failed when cwd was changed"
        )
