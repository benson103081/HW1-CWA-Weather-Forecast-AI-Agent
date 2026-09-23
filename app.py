"""Taiwan county weekly weather forecast dashboard."""
from datetime import datetime
import sqlite3

import folium
import streamlit as st
from streamlit_folium import st_folium

from src.db import get_forecasts, init_db, list_dates, upsert_forecasts
from src.fetch import FetchError, fetch_forecast, get_api_key
from src.parse import ParseError, REGIONS, TAIWAN, parse_forecast
from src.locations import COORDINATES


def main():
    st.set_page_config(page_title="台灣一週天氣預報", page_icon="🌤️", layout="wide")
    st.title("🌤️ 台灣一週天氣預報")
    st.caption("中央氣象署 F-D0047-091｜22 縣市一週預報（含離島）｜溫度單位 °C")
    try:
        init_db()
    except (sqlite3.Error, OSError):
        st.error("無法開啟天氣資料庫，請檢查 data 目錄權限。")
        st.stop()

    if not get_api_key():
        st.warning("尚未設定 CWA_API_KEY。請在專案 .env 填入 Key 後按「更新資料」。")
    if st.button("更新資料", type="primary"):
        try:
            with st.spinner("正在取得最新預報…"):
                rows = parse_forecast(fetch_forecast())
                count = upsert_forecasts(rows)
            st.success(f"已更新 {count} 筆縣市日期預報。")
        except (FetchError, ParseError) as error:
            st.error(str(error))
        except (sqlite3.Error, OSError):
            st.error("資料儲存失敗，請檢查 data 目錄權限與磁碟空間。")

    try:
        days = list_dates()
    except sqlite3.Error:
        st.error("無法讀取天氣資料庫，請確認資料庫格式與權限。")
        st.stop()
    if not days:
        st.info("目前沒有天氣資料。設定 Key 後，請按「更新資料」下載最新預報。")
        st.stop()

    today = datetime.now(TAIWAN).date().isoformat()
    default_day = next((i for i, day in enumerate(days) if day >= today), len(days) - 1)
    selected = st.selectbox("預報日期", days, index=default_day)
    if selected < today:
        st.warning("此日期為歷史預報，請更新資料以取得最新預報。")
    try:
        rows = get_forecasts(selected)
    except sqlite3.Error:
        st.error("無法讀取所選日期的預報，請稍後重試。")
        st.stop()
    if not rows:
        st.info("所選日期沒有資料，請重新選擇日期或更新資料。")
        st.stop()

    by_region = {row["region"]: row for row in rows}
    st.caption("依臺灣時間的時段開始日期彙整最低／最高溫；夜間預報跨至翌日，首末日可能只有部分時段。")
    left, right = st.columns([3, 2])
    with left:
        weather_map = folium.Map(location=[23.75, 121.0], zoom_start=7, tiles="OpenStreetMap")
        weather_map.fit_bounds(list(COORDINATES.values()), padding=(25, 25))
        for region, coordinates in COORDINATES.items():
            row = by_region.get(region)
            description = f"最低 {row['min_temp']:g} °C · 最高 {row['max_temp']:g} °C" if row else "尚無溫度資料"
            folium.Marker(
                coordinates, tooltip=region,
                popup=folium.Popup(f"<b>{region}</b><br>{selected}<br>{description}", max_width=260),
                icon=folium.Icon(color="blue" if row else "gray", icon="cloud"),
            ).add_to(weather_map)
        st_folium(weather_map, height=540, use_container_width=True, returned_objects=[], key="weather-map")
        st.caption("點擊標記查看溫度。標記採用 CWA 縣市代表座標，非測站位置；可縮放查看離島與鄰近縣市。")
    with right:
        st.subheader("各縣市溫度")
        st.dataframe([
            {"縣市": region, "最低溫 (°C)": by_region[region]["min_temp"], "最高溫 (°C)": by_region[region]["max_temp"]}
            for region in REGIONS if region in by_region
        ], hide_index=True, width="stretch", height=540)
        st.caption(f"資料寫入時間（UTC）：{max(row['updated_at'] for row in rows)}")
        st.caption("本頁顯示 SQLite 已儲存資料；按「更新資料」取得最新預報。")


if __name__ == "__main__":
    main()
