"""
Schema validator for CoNDA JSONL simulation outputs.

Validates records against the frozen MarketTick schema specification.
Detects malformed JSON, missing or unexpected fields, invalid types, and invalid nested structures.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any, Dict, List, Optional, Set, Union


class ValidationError(ValueError):
    """Raised when a JSONL line or record violates the frozen schema."""

    def __init__(self, message: str, line_num: Optional[int] = None) -> None:
        self.line_num = line_num
        prefix = f"Line {line_num}: " if line_num is not None else ""
        super().__init__(f"{prefix}{message}")


# Strict allowed keys in frozen MarketTick schema
FROZEN_RECORD_KEYS: Set[str] = {
    "run_id",
    "t",
    "event",
    "agent_id",
    "side",
    "price",
    "quantity",
    "capital",
    "pnl",
    "pool",
    "oracle_price",
    "shock",
}

ALLOWED_EVENTS: Set[str] = {"quote", "trade", "shock", "meta"}
ALLOWED_SIDES: Set[str] = {"bid", "ask"}
POOL_KEYS: Set[str] = {"reserve_x", "reserve_y", "fee_bps"}
SHOCK_KEYS: Set[str] = {"type", "magnitude"}


def _is_number(val: Any) -> bool:
    """Return True if val is int or float, but NOT bool."""
    return isinstance(val, (int, float)) and not isinstance(val, bool)


def validate_record(record: Dict[str, Any], line_num: Optional[int] = None) -> None:
    """
    Validate a single parsed record against the frozen schema.

    Raises
    ------
    ValidationError
        If any schema rule is violated.
    """
    if not isinstance(record, dict):
        raise ValidationError("Record must be a JSON object", line_num)

    rec_keys = set(record.keys())
    missing = FROZEN_RECORD_KEYS - rec_keys
    if missing:
        raise ValidationError(f"Missing required fields: {sorted(missing)}", line_num)

    extra = rec_keys - FROZEN_RECORD_KEYS
    if extra:
        raise ValidationError(f"Unexpected extra fields: {sorted(extra)}", line_num)

    # 1. run_id
    run_id = record["run_id"]
    if not isinstance(run_id, str) or not run_id:
        raise ValidationError(
            f"run_id must be a non-empty string, got {type(run_id).__name__}: {run_id!r}",
            line_num,
        )

    # 2. t
    t = record["t"]
    if not isinstance(t, int) or isinstance(t, bool) or t < 0:
        raise ValidationError(
            f"t must be a non-negative integer, got {t!r}", line_num
        )

    # 3. event
    event = record["event"]
    if event not in ALLOWED_EVENTS:
        raise ValidationError(
            f"event must be one of {sorted(ALLOWED_EVENTS)}, got {event!r}",
            line_num,
        )

    # 4. pool
    pool = record["pool"]
    if not isinstance(pool, dict):
        raise ValidationError(f"pool must be an object, got {type(pool).__name__}", line_num)
    pool_keys = set(pool.keys())
    if pool_keys != POOL_KEYS:
        raise ValidationError(
            f"pool fields must be exactly {sorted(POOL_KEYS)}, got {sorted(pool_keys)}",
            line_num,
        )
    if not _is_number(pool["reserve_x"]) or pool["reserve_x"] <= 0:
        raise ValidationError(
            f"pool.reserve_x must be a positive number, got {pool['reserve_x']!r}",
            line_num,
        )
    if not _is_number(pool["reserve_y"]) or pool["reserve_y"] <= 0:
        raise ValidationError(
            f"pool.reserve_y must be a positive number, got {pool['reserve_y']!r}",
            line_num,
        )
    fee_bps = pool["fee_bps"]
    if not isinstance(fee_bps, int) or isinstance(fee_bps, bool) or fee_bps < 0 or fee_bps >= 10000:
        raise ValidationError(
            f"pool.fee_bps must be an integer in [0, 9999], got {fee_bps!r}",
            line_num,
        )

    # 5. oracle_price
    oracle_price = record["oracle_price"]
    if not _is_number(oracle_price) or oracle_price <= 0:
        raise ValidationError(
            f"oracle_price must be a positive number, got {oracle_price!r}",
            line_num,
        )

    # 6. Event-specific checks
    agent_id = record["agent_id"]
    side = record["side"]
    price = record["price"]
    quantity = record["quantity"]
    capital = record["capital"]
    pnl = record["pnl"]
    shock = record["shock"]

    if event in ("shock", "meta"):
        # Agent-specific fields must be None
        for field_name, field_val in [
            ("agent_id", agent_id),
            ("side", side),
            ("price", price),
            ("quantity", quantity),
            ("capital", capital),
            ("pnl", pnl),
        ]:
            if field_val is not None:
                raise ValidationError(
                    f"{field_name} must be null for {event!r} event, got {field_val!r}",
                    line_num,
                )

        if event == "shock":
            if not isinstance(shock, dict):
                raise ValidationError(
                    f"shock must be an object for 'shock' event, got {shock!r}",
                    line_num,
                )
            if set(shock.keys()) != SHOCK_KEYS:
                raise ValidationError(
                    f"shock fields must be exactly {sorted(SHOCK_KEYS)}, got {sorted(shock.keys())}",
                    line_num,
                )
            if not isinstance(shock["type"], str) or not shock["type"]:
                raise ValidationError("shock.type must be a non-empty string", line_num)
            if not _is_number(shock["magnitude"]):
                raise ValidationError("shock.magnitude must be a number", line_num)
        else:  # meta event
            if shock is not None:
                raise ValidationError(
                    f"shock must be null for 'meta' event, got {shock!r}", line_num
                )
    else:
        # event in ("quote", "trade")
        if not isinstance(agent_id, str) or not agent_id:
            raise ValidationError(
                f"agent_id must be a non-empty string for {event!r} event, got {agent_id!r}",
                line_num,
            )
        if side not in ALLOWED_SIDES:
            raise ValidationError(
                f"side must be one of {sorted(ALLOWED_SIDES)} for {event!r} event, got {side!r}",
                line_num,
            )
        if not _is_number(price) or price <= 0:
            raise ValidationError(
                f"price must be a positive number for {event!r} event, got {price!r}",
                line_num,
            )
        if not _is_number(quantity) or quantity < 0:
            raise ValidationError(
                f"quantity must be a non-negative number for {event!r} event, got {quantity!r}",
                line_num,
            )
        if not _is_number(capital):
            raise ValidationError(
                f"capital must be a numeric value for {event!r} event, got {capital!r}",
                line_num,
            )
        if not _is_number(pnl):
            raise ValidationError(
                f"pnl must be a numeric value for {event!r} event, got {pnl!r}",
                line_num,
            )
        if shock is not None:
            raise ValidationError(
                f"shock must be null for {event!r} event, got {shock!r}", line_num
            )


def validate_file(filepath: Union[str, pathlib.Path]) -> int:
    """
    Validate every line of a JSONL file against the frozen schema.

    Parameters
    ----------
    filepath : str or Path
        Path to JSONL file.

    Returns
    -------
    int
        Count of validated records.

    Raises
    ------
    ValidationError
        If file does not exist, is empty, or contains schema violations.
    """
    path = pathlib.Path(filepath)
    if not path.exists():
        raise ValidationError(f"File does not exist: {path}")

    record_count = 0
    with open(path, "r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                rec = json.loads(text)
            except json.JSONDecodeError as err:
                raise ValidationError(f"Malformed JSON: {err}", line_num=line_num) from err

            validate_record(rec, line_num=line_num)
            record_count += 1

    if record_count == 0:
        raise ValidationError("File contains no records (empty file)", line_num=0)

    return record_count


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for JSONL schema validator."""
    parser = argparse.ArgumentParser(
        description="Validate CoNDA JSONL simulation outputs against the frozen schema."
    )
    parser.add_argument("file", help="Path to JSONL file to validate")
    args = parser.parse_args(argv)

    try:
        count = validate_file(args.file)
        print(f"Validation PASSED: {args.file} ({count} records)")
        return 0
    except ValidationError as err:
        sys.stderr.write(f"Validation FAILED: {err}\n")
        return 1
    except Exception as err:
        sys.stderr.write(f"Error reading file: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
