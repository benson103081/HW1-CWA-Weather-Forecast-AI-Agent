"""Synthetic fixture following the official F-A0010-001 example, not live weather."""
import pytest

from src.parse import REGIONS


@pytest.fixture
def payload():
    locations = []
    for region in REGIONS:
        locations.append({
            "locationName": region + "地區",
            "weatherElements": {
                "MinT": {"daily": [{"dataDate": "2026-09-24", "temperature": "23"}, {"dataDate": "2026-09-25", "temperature": "24"}]},
                "MaxT": {"daily": [{"dataDate": "2026-09-25", "temperature": "32"}, {"dataDate": "2026-09-24", "temperature": "31"}]},
            },
        })
    return {"cwaopendata": {"resources": {"resource": {"data": {"agrWeatherForecasts": {"weatherForecasts": {"location": locations}}}}}}}


@pytest.fixture
def locations(payload):
    return payload["cwaopendata"]["resources"]["resource"]["data"]["agrWeatherForecasts"]["weatherForecasts"]["location"]
