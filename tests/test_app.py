from pathlib import Path

from streamlit.testing.v1 import AppTest

from src import db, fetch
from src.parse import parse_forecast

APP = Path(__file__).resolve().parents[1] / "app.py"


def setup_db(monkeypatch, tmp_path):
    path = tmp_path / "weather.db"
    originals = {name: getattr(db, name) for name in ("init_db", "list_dates", "get_forecasts", "upsert_forecasts")}
    for name, function in originals.items():
        monkeypatch.setattr(db, name, lambda *args, f=function: f(*args, db_path=path))
    return path


def test_no_key_no_data(monkeypatch, tmp_path):
    setup_db(monkeypatch, tmp_path)
    monkeypatch.setattr(fetch, "get_api_key", lambda: "")
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert "CWA_API_KEY" in app.warning[0].value
    assert app.info
    app.button[0].click().run()
    assert not app.exception
    assert "CWA_API_KEY" in app.error[0].value


def test_update_and_retain_data_on_failure(monkeypatch, tmp_path, payload):
    setup_db(monkeypatch, tmp_path)
    monkeypatch.setattr(fetch, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(fetch, "fetch_forecast", lambda: payload)
    app = AppTest.from_file(str(APP)).run()
    app.button[0].click().run()
    assert not app.exception
    assert app.success
    assert len(app.selectbox[0].options) == 2
    assert len(app.dataframe[0].value) == 6
    app.selectbox[0].select("2026-09-25").run()
    assert set(app.dataframe[0].value["最高溫 (°C)"]) == {32.0}

    def fail():
        raise fetch.FetchError("API 暫時無法使用")

    monkeypatch.setattr(fetch, "fetch_forecast", fail)
    app.button[0].click().run()
    assert not app.exception
    assert app.error[0].value == "API 暫時無法使用"
    assert len(app.dataframe[0].value) == 6
