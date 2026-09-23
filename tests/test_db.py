import sqlite3

import pytest

from src.db import get_forecasts, init_db, list_dates, upsert_forecasts
from src.parse import parse_forecast


def test_upsert_updates_without_duplicates(tmp_path, payload):
    path = tmp_path / "nested" / "weather.db"
    init_db(path)
    init_db(path)
    assert list_dates(path) == []
    rows = parse_forecast(payload)
    assert upsert_forecasts(rows, path) == 12
    before = get_forecasts("2026-09-24", path)
    for row in rows:
        row["max_temp"] = 35
    upsert_forecasts(rows, path)
    after = get_forecasts("2026-09-24", path)
    assert len(after) == 6
    assert all(row["max_temp"] == 35 for row in after)
    assert after[0]["updated_at"] >= before[0]["updated_at"]
    assert list_dates(path) == ["2026-09-24", "2026-09-25"]
    assert get_forecasts("' OR 1=1 --", path) == []


def test_failed_batch_rolls_back(tmp_path, payload):
    path = tmp_path / "weather.db"
    init_db(path)
    rows = parse_forecast(payload)
    rows[1]["min_temp"] = 99
    with pytest.raises(sqlite3.IntegrityError):
        upsert_forecasts(rows, path)
    assert list_dates(path) == []
