"""Parse F-A0010-001 regional daily temperatures (join by date)."""

from datetime import date
import math

REGIONS = ("北部", "中部", "南部", "東北部", "東部", "東南部")


class ParseError(ValueError):
    """The dataset is missing or has invalid forecast values."""


def as_list(value):
    return value if isinstance(value, list) else [value]


def temperatures(element):
    result = {}
    for daily in as_list(element["daily"]):
        day = date.fromisoformat(daily["dataDate"]).isoformat()
        raw = daily["temperature"]
        if isinstance(raw, bool):
            raise ValueError("boolean temperature")
        value = float(raw)
        if not math.isfinite(value) or not -50 <= value <= 60 or day in result:
            raise ValueError("invalid or duplicate temperature")
        result[day] = value
    return result


def parse_forecast(payload):
    """Reject malformed/incomplete snapshots rather than silently store partial data."""
    try:
        resources = as_list(payload["cwaopendata"]["resources"]["resource"])
        rows = {}
        for resource in resources:
            forecasts = resource.get("data", {}).get("agrWeatherForecasts")
            if forecasts is None:
                continue
            for location in as_list(forecasts["weatherForecasts"]["location"]):
                region = location["locationName"].removesuffix("地區")
                if region not in REGIONS:
                    continue
                elements = location["weatherElements"]
                lows = temperatures(elements["MinT"])
                highs = temperatures(elements["MaxT"])
                if lows.keys() != highs.keys():
                    raise ValueError("unmatched dates")
                for day, low in lows.items():
                    if low > highs[day] or (region, day) in rows:
                        raise ValueError("inverted range or duplicate record")
                    rows[region, day] = {"region": region, "date": day, "min_temp": low, "max_temp": highs[day]}
        if not rows:
            raise ValueError("empty forecast")
        dates = {day for _, day in rows}
        if any({region for region, day in rows if day == target} != set(REGIONS) for target in dates):
            raise ValueError("incomplete regional coverage")
        return sorted(rows.values(), key=lambda row: (row["date"], REGIONS.index(row["region"])))
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError):
        raise ParseError("預報資料缺漏或格式異常，請稍後重新更新。") from None
