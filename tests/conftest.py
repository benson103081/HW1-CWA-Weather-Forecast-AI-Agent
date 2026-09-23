"""Synthetic fixture matching the downloaded F-D0047-091 structure."""
import pytest

from src.parse import REGIONS


@pytest.fixture
def payload():
    locations = []
    periods = [
        ("2026-09-24T06:00:00+08:00", "2026-09-24T18:00:00+08:00", "25", "31"),
        ("2026-09-24T18:00:00+08:00", "2026-09-25T06:00:00+08:00", "23", "27"),
        ("2026-09-25T06:00:00+08:00", "2026-09-25T18:00:00+08:00", "24", "32"),
    ]
    for region in REGIONS:
        elements = []
        for name, field, index in [("最低溫度", "MinTemperature", 2), ("最高溫度", "MaxTemperature", 3)]:
            times = [{"StartTime": p[0], "EndTime": p[1], "ElementValue": [{field: p[index]}]} for p in periods]
            elements.append({"ElementName": name, "Time": times if index == 2 else list(reversed(times))})
        locations.append({"LocationName": region, "WeatherElement": elements})
    return {"success": "true", "records": {"Locations": [{"Location": locations}]}}


@pytest.fixture
def locations(payload):
    return payload["records"]["Locations"][0]["Location"]
