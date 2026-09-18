"""JSONL Tick Loader for CoNDA Detector.

Reads and validates streaming market ticks from JSONL files or in-memory iterables.
Preserves tick data without relying on ground-truth labels or run_meta.json.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Union

logger = logging.getLogger(__name__)

# Valid market event types defined in the CoNDA system contract
VALID_EVENTS = {"quote", "trade", "shock", "meta"}


def _is_valid_tick_dict(item: Any) -> bool:
    """Basic validation that an object conforms to a market tick structure.

    A valid tick must be a dictionary and should contain at least an 'event'
    or 't' or 'run_id' key. We are permissive to preserve raw data while
    filtering out non-tick garbage.
    """
    if not isinstance(item, dict):
        return False
    # Must have at least one identifying property of a tick
    return "event" in item or "t" in item or "run_id" in item


def iter_ticks(
    source: Union[str, Path, Iterable[Union[str, Dict[str, Any]]]]
) -> Iterator[Dict[str, Any]]:
    """Yield parsed tick dictionaries from a file path, file-like, or iterable.

    Safely skips blank lines, malformed JSON, and non-tick objects without crashing.

    Args:
        source: File path (str or Path) or an iterable of JSON strings / dicts.

    Yields:
        Validated tick dictionary.
    """
    # Case 1: source is a file path
    if isinstance(source, (str, Path)):
        path = Path(source)
        if not path.is_file():
            logger.warning("File not found or not a regular file: %s", source)
            return

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.strip()
                if not line:
                    continue  # Ignore blank lines
                try:
                    tick = json.loads(line)
                    if _is_valid_tick_dict(tick):
                        yield tick
                    else:
                        logger.debug("Line %d is not a valid tick dict, skipping.", line_no)
                except Exception as exc:
                    logger.debug("Malformed JSON on line %d: %s", line_no, exc)
                    continue
        return

    # Case 2: source is an iterable (list, generator, etc.)
    if isinstance(source, Iterable):
        for idx, item in enumerate(source):
            if isinstance(item, dict):
                if _is_valid_tick_dict(item):
                    yield dict(item)  # Return shallow copy to preserve original
                else:
                    logger.debug("Item %d is not a valid tick dict, skipping.", idx)
            elif isinstance(item, (str, bytes)):
                line = item.decode("utf-8", errors="replace") if isinstance(item, bytes) else item
                line = line.strip()
                if not line:
                    continue
                try:
                    tick = json.loads(line)
                    if _is_valid_tick_dict(tick):
                        yield tick
                except Exception as exc:
                    logger.debug("Malformed JSON at item %d: %s", idx, exc)
                    continue
            else:
                logger.debug("Unsupported item type at index %d: %s", idx, type(item))
                continue


def load_ticks(
    source: Union[str, Path, Iterable[Union[str, Dict[str, Any]]]]
) -> List[Dict[str, Any]]:
    """Load all valid ticks from a file path or iterable into a list.

    Args:
        source: File path (str or Path) or an iterable of JSON strings / dicts.

    Returns:
        List of parsed tick dictionaries.
    """
    return list(iter_ticks(source))
