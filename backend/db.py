"""
backend/db.py
-------------
SQLite persistence layer for CoNDA.

Tables:  runs | assessments | cases

All public functions open a short-lived connection per call so the module is
safe to use from any thread (including asyncio worker threads).

Database location:  <repo_root>/data/conda.db   (created automatically).

No ORM.  Plain sqlite3 only.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR  = _REPO_ROOT / "data"
_DB_PATH   = _DATA_DIR / "conda.db"


def _db_path() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DB_PATH


def _connect() -> sqlite3.Connection:
    """Open a short-lived, WAL-mode connection."""
    conn = sqlite3.connect(str(_db_path()), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
_DDL = """
CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,
    scenario     TEXT NOT NULL,
    seed         INTEGER NOT NULL,
    state        TEXT NOT NULL DEFAULT 'running',
    current_tick INTEGER NOT NULL DEFAULT 0,
    total_ticks  INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS assessments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         TEXT NOT NULL,
    window_start   INTEGER NOT NULL,
    window_end     INTEGER NOT NULL,
    grp            TEXT NOT NULL,
    risk_score     INTEGER NOT NULL,
    verdict        TEXT NOT NULL,
    signals        TEXT NOT NULL,
    counterfactual TEXT NOT NULL,
    evidence_hash  TEXT NOT NULL,
    computed_ms    REAL NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS cases (
    case_id        TEXT PRIMARY KEY,
    run_id         TEXT NOT NULL,
    grp            TEXT NOT NULL,
    risk_score     INTEGER NOT NULL,
    evidence_hash  TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'OPEN',
    opened_tx      TEXT,
    challenge_tx   TEXT,
    resolved_tx    TEXT,
    opened_at_tick INTEGER NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(run_id)
);
"""


def initialize_db() -> None:
    """Create tables if they do not already exist."""
    with _connect() as conn:
        conn.executescript(_DDL)
    logger.debug("DB initialized at %s", _db_path())


# ---------------------------------------------------------------------------
# runs
# ---------------------------------------------------------------------------

def create_run(run_id: str, scenario: str, seed: int) -> str:
    """Insert a new run row and return its run_id."""
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO runs (run_id, scenario, seed, state, "
            "current_tick, total_ticks, created_at) "
            "VALUES (?, ?, ?, 'running', 0, 0, ?)",
            (run_id, scenario, seed, now),
        )
    return run_id


def update_run_status(run_id: str, state: str) -> None:
    """Update run state. state in {'running', 'done'}."""
    with _connect() as conn:
        conn.execute(
            "UPDATE runs SET state = ? WHERE run_id = ?",
            (state, run_id),
        )


def update_run_tick(
    run_id: str, current_tick: int, total_ticks: int = 0
) -> None:
    """Persist the current tick counter (and optionally total_ticks)."""
    with _connect() as conn:
        if total_ticks:
            conn.execute(
                "UPDATE runs SET current_tick = ?, total_ticks = ? "
                "WHERE run_id = ?",
                (current_tick, total_ticks, run_id),
            )
        else:
            conn.execute(
                "UPDATE runs SET current_tick = ? WHERE run_id = ?",
                (current_tick, run_id),
            )


def get_run(run_id: str) -> Optional[dict]:
    """Return a run as a dict, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# assessments
# ---------------------------------------------------------------------------

def save_assessment(assessment: dict) -> int:
    """Persist a RiskAssessment dict; return the new rowid."""
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO assessments "
            "(run_id, window_start, window_end, grp, risk_score, verdict, "
            "signals, counterfactual, evidence_hash, computed_ms) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                assessment["run_id"],
                assessment["window_start"],
                assessment["window_end"],
                json.dumps(assessment["group"]),
                assessment["risk_score"],
                assessment["verdict"],
                json.dumps(assessment["signals"]),
                json.dumps(assessment["counterfactual"]),
                assessment["evidence_hash"],
                assessment["computed_ms"],
            ),
        )
        return cur.lastrowid


def get_latest_assessment(run_id: str) -> Optional[dict]:
    """Return the most recent assessment row for *run_id*, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM assessments WHERE run_id = ? "
            "ORDER BY id DESC LIMIT 1",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["group"]          = json.loads(d.pop("grp"))
    d["signals"]        = json.loads(d["signals"])
    d["counterfactual"] = json.loads(d["counterfactual"])
    return d


def list_assessments(run_id: str) -> list:
    """Return all assessments for a run in insertion order."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM assessments WHERE run_id = ? ORDER BY id ASC",
            (run_id,),
        ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["group"]          = json.loads(d.pop("grp"))
        d["signals"]        = json.loads(d["signals"])
        d["counterfactual"] = json.loads(d["counterfactual"])
        result.append(d)
    return result


# ---------------------------------------------------------------------------
# cases
# ---------------------------------------------------------------------------

def create_case(
    run_id: str,
    group: list,
    risk_score: int,
    evidence_hash: str,
    opened_at_tick: int,
    opened_tx: Optional[str] = None,
    case_id: Optional[str] = None,
) -> dict:
    """Insert a new OPEN case and return its full dict."""
    if case_id is None:
        case_id = str(uuid.uuid4())
    with _connect() as conn:
        conn.execute(
            "INSERT INTO cases "
            "(case_id, run_id, grp, risk_score, evidence_hash, status, "
            " opened_tx, challenge_tx, resolved_tx, opened_at_tick) "
            "VALUES (?, ?, ?, ?, ?, 'OPEN', ?, NULL, NULL, ?)",
            (
                case_id,
                run_id,
                json.dumps(sorted(group)),
                risk_score,
                evidence_hash,
                opened_tx,
                opened_at_tick,
            ),
        )
    return {
        "case_id":        case_id,
        "run_id":         run_id,
        "group":          group,
        "risk_score":     risk_score,
        "evidence_hash":  evidence_hash,
        "status":         "OPEN",
        "opened_tx":      opened_tx,
        "challenge_tx":   None,
        "resolved_tx":    None,
        "opened_at_tick": opened_at_tick,
    }


def get_case(case_id: str) -> Optional[dict]:
    """Return a single case by case_id, or None."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM cases WHERE case_id = ?", (case_id,)
        ).fetchone()
    if not row:
        return None
    d = dict(row)
    d["group"] = json.loads(d.pop("grp"))
    return d


def update_case(case_id: str, **kwargs: Any) -> None:
    """Update columns on a case.  Allowed keys: status, opened_tx,
    challenge_tx, resolved_tx."""
    allowed = {"status", "opened_tx", "challenge_tx", "resolved_tx"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [case_id]
    with _connect() as conn:
        conn.execute(
            f"UPDATE cases SET {set_clause} WHERE case_id = ?", values
        )


def list_cases(run_id: Optional[str] = None) -> list:
    """Return all cases (optionally filtered by run_id)."""
    with _connect() as conn:
        if run_id:
            rows = conn.execute(
                "SELECT * FROM cases WHERE run_id = ? ORDER BY rowid ASC",
                (run_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM cases ORDER BY rowid ASC"
            ).fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["group"] = json.loads(d.pop("grp"))
        result.append(d)
    return result


def case_exists_for_run_group(run_id: str, group: list) -> bool:
    """True if an OPEN case already exists for this run + agent group."""
    grp_json = json.dumps(sorted(group))
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM cases "
            "WHERE run_id = ? AND grp = ? AND status = 'OPEN'",
            (run_id, grp_json),
        ).fetchone()
    return row is not None
