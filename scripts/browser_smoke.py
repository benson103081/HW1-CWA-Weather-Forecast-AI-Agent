"""Run against a live local app: refresh, switch dates, click popup, screenshot."""
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1150})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:8501/")
        page.get_by_role("button", name="更新資料", exact=True).click()
        expect(page.get_by_test_id("stAlert")).to_contain_text("已更新", timeout=60000)
        page.get_by_role("combobox").click()
        options = page.get_by_role("option")
        expect(options).not_to_have_count(0)
        assert options.count() >= 2
        target = options.nth(1).inner_text()
        options.nth(1).click()
        expect(page.get_by_role("combobox")).to_have_value(target)
        frame = page.frame_locator('iframe[title="streamlit_folium.st_folium"]')
        markers = frame.locator(".leaflet-marker-pane .awesome-marker")
        expect(markers).to_have_count(22, timeout=45000)
        markers.nth(12).click()
        popup = frame.locator(".leaflet-popup-content")
        expect(popup).to_contain_text(target)
        expect(popup).to_contain_text("最低")
        expect(popup).to_contain_text("最高")
        expect(page.get_by_test_id("stDataFrame")).to_be_visible()
        expect(frame.locator(".leaflet-tile-loaded").first).to_be_visible(timeout=30000)
        page.get_by_test_id("stMain").evaluate("element => element.scrollTop = 0")
        page.mouse.move(1500, 100)
        # Let Leaflet finish popup panning/fade before capturing the presentation.
        page.wait_for_timeout(1000)
        page.screenshot(path=str(ROOT / "docs/screenshots/forecast.png"), full_page=True)
        assert not errors, errors
        print(f"PASS: live refresh, date {target}, 22 markers, temperature popup, screenshot")
        browser.close()


if __name__ == "__main__":
    main()
