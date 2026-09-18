"""
JSON Lines logger and writer for CoNDA simulation outputs.

Provides clean, dependency-free utilities to stream or batch-write simulation
records into schema-conformant JSONL files and run metadata JSON files.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Iterable, List, Optional, Union


class JSONLWriter:
    """Context manager and stream writer for JSON Lines simulation records."""

    def __init__(self, filepath: Union[str, pathlib.Path]) -> None:
        self.filepath = pathlib.Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._fh: Optional[Any] = None
        self.count: int = 0

    def open(self) -> "JSONLWriter":
        if self._fh is None:
            self._fh = open(self.filepath, "w", encoding="utf-8")
        return self

    def write_record(self, record: Dict[str, Any]) -> None:
        """Write a single dict record as one JSON line."""
        if self._fh is None:
            self.open()
        line = json.dumps(record, ensure_ascii=False)
        self._fh.write(line + "\n")
        self.count += 1

    def write_records(self, records: Iterable[Dict[str, Any]]) -> int:
        """Write multiple dict records and return count written."""
        for r in records:
            self.write_record(r)
        return self.count

    def close(self) -> None:
        if self._fh is not None:
            self._fh.flush()
            self._fh.close()
            self._fh = None

    def __enter__(self) -> "JSONLWriter":
        return self.open()

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()


def write_jsonl(
    records: Iterable[Dict[str, Any]],
    filepath: Union[str, pathlib.Path],
) -> int:
    """
    Write simulation records to a JSONL file.

    Parameters
    ----------
    records : Iterable[dict]
        Stream or sequence of record dictionaries.
    filepath : str or Path
        Destination .jsonl file path. Parent directories created automatically.

    Returns
    -------
    int
        Total number of records written.
    """
    with JSONLWriter(filepath) as writer:
        return writer.write_records(records)


def write_run_meta(
    meta: Dict[str, Any],
    filepath: Union[str, pathlib.Path],
) -> None:
    """
    Write run metadata JSON file.

    Parameters
    ----------
    meta : dict
        Metadata dictionary adhering to run_meta specification.
    filepath : str or Path
        Destination .json file path.
    """
    dest = pathlib.Path(filepath)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def read_jsonl(filepath: Union[str, pathlib.Path]) -> List[Dict[str, Any]]:
    """
    Read all records from a JSONL file.

    Parameters
    ----------
    filepath : str or Path
        Path to the .jsonl file.

    Returns
    -------
    list of dict
        Parsed records.
    """
    path = pathlib.Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    records: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_num, line in enumerate(fh, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                records.append(json.loads(text))
            except json.JSONDecodeError as err:
                raise ValueError(
                    f"Corrupted JSON on line {line_num} of {path}: {err}"
                ) from err
    return records
