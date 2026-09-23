import json
from unittest.mock import Mock

import pytest
import requests

from src import fetch


def test_missing_key(monkeypatch, tmp_path):
    monkeypatch.setattr(fetch, "get_api_key", lambda: "")
    with pytest.raises(fetch.FetchError, match="CWA_API_KEY"):
        fetch.fetch_forecast(tmp_path / "raw.json")


def test_fetch_and_save(monkeypatch, tmp_path, payload):
    response = Mock()
    response.json.return_value = payload
    get = Mock(return_value=response)
    monkeypatch.setattr(fetch, "get_api_key", lambda: "test-key")
    monkeypatch.setattr(fetch.requests, "get", get)
    path = tmp_path / "raw.json"
    assert fetch.fetch_forecast(path) == payload
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    assert get.call_args.kwargs["timeout"] == (10, 45)
    assert get.call_args.args[0].endswith("/api/v1/rest/datastore/F-D0047-091")


@pytest.mark.parametrize("failure", [requests.Timeout("secret-key"), requests.HTTPError("secret-key"), ValueError("secret-key")])
def test_errors_hide_credentials_and_keep_cache(monkeypatch, tmp_path, failure):
    monkeypatch.setattr(fetch, "get_api_key", lambda: "secret-key")
    monkeypatch.setattr(fetch.requests, "get", Mock(side_effect=failure))
    path = tmp_path / "raw.json"
    path.write_text("previous", encoding="utf-8")
    with pytest.raises(fetch.FetchError) as error:
        fetch.fetch_forecast(path)
    assert "secret-key" not in str(error.value)
    assert path.read_text(encoding="utf-8") == "previous"


def test_field_paths_include_later_list_fields():
    assert set(fetch.field_paths({"items": [{"a": 1}, {"b": 2}]})) == {"$.items[].a", "$.items[].b"}


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
def test_http_errors_report_status_without_credentials(monkeypatch, tmp_path, status):
    monkeypatch.setattr(fetch, "get_api_key", lambda: "test-key")
    response = requests.Response()
    response.status_code = status
    response.url = "https://example.invalid/?Authorization=test-key"
    monkeypatch.setattr(fetch.requests, "get", Mock(return_value=response))
    with pytest.raises(fetch.FetchError, match=f"HTTP {status}") as error:
        fetch.fetch_forecast(tmp_path / "raw.json")
    assert "test-key" not in str(error.value)
    assert not (tmp_path / "raw.json").exists()


@pytest.mark.parametrize("failure, expected", [
    (requests.Timeout("secret-key"), "逾時"),
    (requests.exceptions.SSLError("secret-key"), "TLS"),
    (requests.ConnectionError("secret-key"), "DNS"),
])
def test_network_errors_are_distinguishable(monkeypatch, tmp_path, failure, expected):
    monkeypatch.setattr(fetch, "get_api_key", lambda: "secret-key")
    monkeypatch.setattr(fetch.requests, "get", Mock(side_effect=failure))
    with pytest.raises(fetch.FetchError, match=expected) as error:
        fetch.fetch_forecast(tmp_path / "raw.json")
    assert "secret-key" not in str(error.value)
