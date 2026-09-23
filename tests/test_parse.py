import pytest

from src.parse import ParseError, parse_forecast


def test_parse_six_regions_join_by_date(payload):
    rows = parse_forecast(payload)
    assert len(rows) == 12
    assert rows[0] == {"region": "北部", "date": "2026-09-24", "min_temp": 23.0, "max_temp": 31.0}
    assert rows[6]["max_temp"] == 32


@pytest.mark.parametrize("value", [None, "", "NaN", "inf", "-99", "abc", True, "40"])
def test_invalid_temperatures(payload, locations, value):
    locations[0]["weatherElements"]["MinT"]["daily"][0]["temperature"] = value
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_missing_date(payload, locations):
    locations[0]["weatherElements"]["MaxT"]["daily"].pop()
    with pytest.raises(ParseError):
        parse_forecast(payload)


def test_missing_region(payload, locations):
    locations.pop()
    with pytest.raises(ParseError):
        parse_forecast(payload)


@pytest.mark.parametrize("payload", [{}, None, {"cwaopendata": {}}])
def test_bad_structure(payload):
    with pytest.raises(ParseError):
        parse_forecast(payload)
