from copy import deepcopy

import pytest

from src.parse import ParseError, REGIONS, parse_forecast


def test_counties_aggregate_matching_periods_by_start_date(payload):
    rows = parse_forecast(payload)
    assert len(rows) == 44
    assert rows[0] == {"region": REGIONS[0], "date": "2026-09-24", "min_temp": 23.0, "max_temp": 31.0}
    assert rows[22]["min_temp"] == 24
    assert rows[22]["max_temp"] == 32


@pytest.mark.parametrize("value", [None, "", "NaN", "inf", "-99", "abc", True, "40"])
def test_invalid_temperatures(payload, locations, value):
    locations[0]["WeatherElement"][0]["Time"][0]["ElementValue"][0]["MinTemperature"] = value
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_missing_period(payload, locations):
    locations[0]["WeatherElement"][1]["Time"].pop()
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_missing_county(payload, locations):
    locations.pop()
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_duplicate_county(payload, locations):
    locations.append(deepcopy(locations[0]))
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_duplicate_period(payload, locations):
    times = locations[0]["WeatherElement"][0]["Time"]
    times.append(deepcopy(times[0]))
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_missing_both_temperature_periods(payload, locations):
    for element in locations[0]["WeatherElement"]:
        element["Time"] = [p for p in element["Time"] if p["StartTime"] != "2026-09-24T18:00:00+08:00"]
    with pytest.raises(ParseError):
        parse_forecast(payload)


@pytest.mark.parametrize("value", ["invalid", "2026-09-24T06:00:00", "2026-09-25T18:00:00+08:00"])
def test_invalid_period(payload, locations, value):
    locations[0]["WeatherElement"][0]["Time"][0]["StartTime"] = value
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_utc_period_is_grouped_using_taiwan_date(payload, locations):
    for location in locations:
        for element in location["WeatherElement"]:
            for period in element["Time"]:
                if period["StartTime"] == "2026-09-24T06:00:00+08:00":
                    period["StartTime"] = "2026-09-23T22:00:00+00:00"
    assert parse_forecast(payload)[0]["date"] == "2026-09-24"


@pytest.mark.parametrize("payload", [{}, None, {"records": {}}, {"success": "false"}])
def test_bad_structure(payload):
    with pytest.raises(ParseError):
        parse_forecast(payload)
