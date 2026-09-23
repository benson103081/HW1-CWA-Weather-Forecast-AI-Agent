"""Download the official JSON and inspect field paths without exposing credentials."""

import json
import os
from pathlib import Path
import tempfile

from dotenv import dotenv_values
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw.json"
API_URL = "https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001"


class FetchError(RuntimeError):
    """A safe, user-facing fetch error."""


def get_api_key():
    # Re-read .env on each refresh; an existing environment variable takes priority.
    return (os.getenv("CWA_API_KEY") or dotenv_values(ROOT / ".env").get("CWA_API_KEY") or "").strip()


def fetch_forecast(raw_path=RAW_PATH):
    key = get_api_key()
    if not key:
        raise FetchError("尚未設定 CWA_API_KEY，請在專案 .env 填入中央氣象署 API Key。")
    try:
        response = requests.get(
            API_URL, params={"Authorization": key, "format": "JSON"},
            timeout=(10, 45),
        )
        if response.status_code == 404:
            raise FetchError("中央氣象署 API 回傳 HTTP 404，指定資料集目前無法取得，請稍後重試或確認服務狀態。")
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        # requests exceptions may contain the URL and Authorization query value.
        raise FetchError("中央氣象署 API 連線失敗，請檢查網路、Key 或稍後重試。") from None
    except ValueError:
        raise FetchError("中央氣象署回傳的內容不是有效 JSON，請稍後重試。") from None
    if not isinstance(payload, dict) or not payload or str(payload.get("success", "true")).lower() == "false":
        raise FetchError("中央氣象署回傳無效或失敗的資料，請確認 API Key 與服務狀態。")
    target = Path(raw_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return payload


def field_paths(value, path="$"):
    """Return unique leaf paths; inspect all list entries, not just the first."""
    if isinstance(value, dict):
        for name, child in value.items():
            yield from field_paths(child, f"{path}.{name}")
    elif isinstance(value, list):
        for child in value:
            yield from field_paths(child, f"{path}[]")
    else:
        yield path


def main():
    try:
        payload = fetch_forecast()
    except (FetchError, OSError) as error:
        print(str(error) if isinstance(error, FetchError) else "無法儲存原始資料，請檢查 data 目錄權限。")
        return 1
    print("Saved data/raw.json. JSON field paths:")
    print("\n".join(sorted(set(field_paths(payload)))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
