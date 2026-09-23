# HW1-CWA-Weather-Forecast-AI-Agent

Python + 中央氣象署 CWA API + SQLite + Streamlit 的台灣一週農業氣象預報 Web App。提供日期選單、六地區地圖標記與每日最低／最高溫表格。

## 安裝（Python 3.12）

在 PowerShell 中執行：

```powershell
cd HW1-CWA-Weather-Forecast-AI-Agent
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS / Linux 使用 `python3 -m venv .venv`，將下列 `.venv\Scripts\python.exe` 改為 `.venv/bin/python`。

## 設定 API Key

至 [中央氣象署開放資料平臺](https://opendata.cwa.gov.tw/) 註冊並取得授權碼。
若尚未有 `.env`，複製 `.env.example` 為 `.env`，填入：

```dotenv
CWA_API_KEY=你的中央氣象署授權碼
```

使用 `python-dotenv` 讀取專案根目錄 `.env`，已設定的環境變數 `CWA_API_KEY` 優先。每次按更新按鈕會重新讀取 `.env`。請勿將金鑰寫入程式碼、README、截圖或 Git；`.env` 已被忽略。

## 下載與檢查 JSON

```powershell
.\.venv\Scripts\python.exe -m src.fetch
```

成功時儲存 `data/raw.json` 並列印所有不同的 JSON 葉節點路徑。失敗時顯示安全訊息並以非零代碼結束，保留既有原始檔。命令不會列印授權 URL 或金鑰。

指定端點：`https://opendata.cwa.gov.tw/fileapi/v1/opendataapi/F-A0010-001`，查詢參數為 `Authorization` 與 `format=JSON`。

[官方資料集與範例](https://opendata.cwa.gov.tw/dataset/forecast/F-A0010-001) 的對應結構如下；以下路徑依官方範例推導，尚待成功下載的 JSON 驗證：

```text
$.cwaopendata.resources.resource.data.agrWeatherForecasts.weatherForecasts.location[].locationName
$.cwaopendata.resources.resource.data.agrWeatherForecasts.weatherForecasts.location[].weatherElements.MinT.daily[].dataDate
$.cwaopendata.resources.resource.data.agrWeatherForecasts.weatherForecasts.location[].weatherElements.MinT.daily[].temperature
$.cwaopendata.resources.resource.data.agrWeatherForecasts.weatherForecasts.location[].weatherElements.MaxT.daily[].dataDate
$.cwaopendata.resources.resource.data.agrWeatherForecasts.weatherForecasts.location[].weatherElements.MaxT.daily[].temperature
```

解析器將「北部地區」等名稱轉為北部、中部、南部、東北部、東部、東南部，依日期配對 MinT 與 MaxT，不依陣列順序配對。遇到缺漏地區、日期不匹配、非法溫度、重複日期或最低溫大於最高溫，拒絕整批寫入並顯示提示。`resource` 與 `daily` 支援單一物件或陣列。

## 執行 Web App

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

開啟 <http://localhost:8501>，按「更新資料」下載 API、儲存原始 JSON、解析並 upsert 到 `data/weather.db`。選擇日期後可查看右側表格，點擊地圖上的六個標記查看溫度。

首次啟動不會自行呼叫 API；無資料時會提示更新。更新失敗仍保留既有 SQLite 資料。歷史日期顯示提醒，時間戳為本機寫入時間（UTC），不是官方預報發布時間。底圖來自 OpenStreetMap，需要網路連線；標記是地區代表位置，不是測站。

資料表：`forecast(region, date, min_temp, max_temp, updated_at)`。以 `(region, date)` 為主鍵，同地區同日期重新抓取會覆寫溫度與時間戳，整批操作包在同一交易中。歷史預報保留供日期選單查閱。

## 測試與啟動檢查

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false
```

測試使用合成資料與暫存資料庫，不會呼叫真實 API、使用本機 Key 或污染正式資料庫。涵蓋抓取錯誤遮蔽金鑰、解析、upsert、交易回復，以及使用 [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) 驗證缺少 Key、無資料、更新、日期切換與 API 失敗後保留資料。

2026-09-23 驗證結果：25 個 pytest 測試通過，`pip check` 通過；Streamlit 伺服器成功啟動，首頁與 `/_stcore/health` 均回傳 HTTP 200。

**目前限制：** 使用本機授權碼呼叫指定官方 API 持續回傳 HTTP 404，回應為 `{"message":"Resouce not found."}`。因此尚未取得真實 `data/raw.json`，尚未完成真實 API 結構與完整資料流程驗證。測試資料未寫入正式資料庫，也未作為即時天氣展示。服務恢復後請先執行 `python -m src.fetch`，核對欄位，再按「更新資料」驗證六地區預報。地圖 popup 尚未進行瀏覽器實際點擊驗證。

## 專案結構

```text
app.py
src/
  fetch.py        # 安全下載與 JSON 欄位路徑檢查
  parse.py        # 地區、日期、最低溫、最高溫解析
  db.py           # SQLite 建表、upsert、查詢
tests/            # pytest 與 Streamlit AppTest
data/             # raw.json / weather.db，均不提交
docs/screenshots/ # 截圖位置
.env.example      # 設定範本（不含金鑰）
requirements.txt
```

## 截圖位置

實際取得資料後，請將介面截圖放在 `docs/screenshots/forecast.png`，建議包含日期、六地區地圖及溫度表格。目前未附即時預報截圖。

## Git

遠端：<https://github.com/benson103081/HW1-CWA-Weather-Forecast-AI-Agent.git>，主分支為 `main`。

推送前確認 `.env` 未被追蹤：

```powershell
git ls-files -- .env
git check-ignore .env .venv data/raw.json data/weather.db
```

第一個命令應無輸出。`.gitignore` 排除 `.venv`、`.env`、Python 快取、SQLite 資料庫與 `data/raw.json`。
