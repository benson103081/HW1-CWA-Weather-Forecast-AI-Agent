"""Parse F-D0047-091; aggregate matching periods by Taiwan start date."""
from datetime import datetime, timedelta, timezone
import math

from src.locations import COORDINATES

REGIONS = tuple(COORDINATES)
TAIWAN = timezone(timedelta(hours=8))


class ParseError(ValueError):
    """The dataset is missing or has invalid forecast values."""


def temperatures(element, field):
    result = {}
    for period in element["Time"]:
        start = datetime.fromisoformat(period["StartTime"])
        end = datetime.fromisoformat(period["EndTime"])
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("invalid period")
        interval = (start.astimezone(TAIWAN), end.astimezone(TAIWAN))
        values = period["ElementValue"]
        if len(values) != 1:
            raise ValueError("ambiguous temperature")
        raw = values[0][field]
        if isinstance(raw, bool):
            raise ValueError("boolean temperature")
        value = float(raw)
        if not math.isfinite(value) or not -50 <= value <= 60 or interval in result:
            raise ValueError("invalid or duplicate temperature")
        result[interval] = value
    intervals = sorted(result)
    if any(previous[1] > current[0] for previous, current in zip(intervals, intervals[1:])):
        raise ValueError("overlapping periods")
    return result


def parse_forecast(payload):
    """Reject incomplete snapshots; Min/Max periods join by both endpoints."""
    try:
        if str(payload["success"]).lower() != "true":
            raise ValueError("API failure")
        rows = {}
        seen = set()
        expected_intervals = None
        for group in payload["records"]["Locations"]:
            for location in group["Location"]:
                region = location["LocationName"]
                if region not in REGIONS or region in seen:
                    raise ValueError("unknown or duplicate county")
                seen.add(region)
                elements = {}
                for element in location["WeatherElement"]:
                    name = element["ElementName"]
                    if name in ("最低溫度", "最高溫度"):
                        if name in elements:
                            raise ValueError("duplicate element")
                        elements[name] = element
                lows = temperatures(elements["最低溫度"], "MinTemperature")
                highs = temperatures(elements["最高溫度"], "MaxTemperature")
                if not lows or lows.keys() != highs.keys():
                    raise ValueError("unmatched periods")
                if expected_intervals is not None and set(lows) != expected_intervals:
                    raise ValueError("incomplete county periods")
                expected_intervals = set(lows)
                for interval, low in lows.items():
                    high = highs[interval]
                    if low > high:
                        raise ValueError("inverted range")
                    day = interval[0].date().isoformat()
                    row = rows.setdefault((region, day), {
                        "region": region, "date": day, "min_temp": low, "max_temp": high,
                    })
                    row["min_temp"] = min(row["min_temp"], low)
                    row["max_temp"] = max(row["max_temp"], high)
        if seen != set(REGIONS) or not rows:
            raise ValueError("incomplete county coverage")
        return sorted(rows.values(), key=lambda row: (row["date"], REGIONS.index(row["region"])))
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, IndexError):
        raise ParseError("預報資料缺漏或格式異常，請稍後重新更新。") from None
