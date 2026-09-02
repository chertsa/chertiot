from app.export import iter_rows, stream_csv, stream_json


class FakeStudent:
    def __init__(self, pages: list[list[dict]]) -> None:
        self.pages = pages
        self.calls = 0

    def timeseries(
        self, device_id: str, keys: list[str], start_ts: int, end_ts: int, limit: int = 10000
    ):  # noqa: ANN201
        page = self.pages[self.calls] if self.calls < len(self.pages) else []
        self.calls += 1
        return {keys[0]: page}


def test_iter_rows_pages_and_orders_oldest_first() -> None:
    pages = [
        [{"ts": 3000, "value": "c"}, {"ts": 2000, "value": "b"}],
        [{"ts": 1000, "value": "a"}],
        [],
    ]
    rows = list(iter_rows(FakeStudent(pages), "d", ["t"], start_ts=0, end_ts=4000, page_size=2))  # type: ignore[arg-type]
    assert [r[0] for r in rows] == [2000, 3000, 1000]  # oldest-first within each page window
    assert len(rows) == 3 and all(r[1] == "t" for r in rows)


def test_streams() -> None:
    rows = [(1, "t", "1.5"), (2, "t", "2.5")]
    csv_out = "".join(stream_csv(iter(rows)))
    assert csv_out.splitlines()[0] == "ts_ms,key,value" and "2,t,2.5" in csv_out
    import json

    parsed = json.loads("".join(stream_json(iter(rows))))
    assert parsed == [{"ts": 1, "key": "t", "value": "1.5"}, {"ts": 2, "key": "t", "value": "2.5"}]
