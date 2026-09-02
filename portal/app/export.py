"""Telemetry export (M3.4): stream a student's own device data as CSV or JSON.

Scoped by construction: every read uses the student's impersonated TB session. Range-limited to
31 days and row-capped; rate-limited per user."""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator
from typing import TYPE_CHECKING

from app.tb_client import TbClient

if TYPE_CHECKING:
    pass

MAX_RANGE_MS = 31 * 24 * 3600 * 1000
MAX_ROWS = 500_000
PAGE = 10_000


def iter_rows(
    student: TbClient,
    device_id: str,
    keys: list[str],
    start_ts: int,
    end_ts: int,
    page_size: int = PAGE,
) -> Iterator[tuple[int, str, str]]:
    """(ts, key, value) tuples, oldest-first per page, paged through TB's descending windows."""
    emitted = 0
    for key in keys:
        cursor_end = end_ts
        while cursor_end > start_ts:
            page = student.timeseries(device_id, [key], start_ts, cursor_end, limit=page_size).get(
                key, []
            )
            points = [p for p in page if p.get("value") is not None]
            for p in reversed(points):  # TB returns newest-first
                yield (int(p["ts"]), key, str(p["value"]))
                emitted += 1
                if emitted >= MAX_ROWS:
                    return
            if not page or len(page) < page_size:
                break
            oldest = min(int(p["ts"]) for p in page)
            if oldest <= start_ts:
                break
            cursor_end = oldest - 1


def stream_csv(rows: Iterator[tuple[int, str, str]]) -> Iterator[str]:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["ts_ms", "key", "value"])
    yield buf.getvalue()
    for ts, key, value in rows:
        buf.seek(0)
        buf.truncate()
        writer.writerow([ts, key, value])
        yield buf.getvalue()


def stream_json(rows: Iterator[tuple[int, str, str]]) -> Iterator[str]:
    yield "["
    first = True
    for ts, key, value in rows:
        prefix = "" if first else ","
        first = False
        yield prefix + json.dumps({"ts": ts, "key": key, "value": value})
    yield "]"
