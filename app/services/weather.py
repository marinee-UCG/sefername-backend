"""Weather at a noon position, from Open-Meteo (https://open-meteo.com, data CC BY 4.0).

Model data, not a measurement: the app labels it so. Only a rounded position and the time are sent,
from the server, never who the user is. The free API is for non-commercial use: a paid Open-Meteo plan
is needed once the app earns money. Any failure gives empty values; a noon report never fails because of it.
"""
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
TIMEOUT_SECONDS = 5
# The free API covers about the last three months; older noon reports go without weather
OLDEST_DAYS = 80
# Knots at which each Beaufort force begins (force 1 from 1 kn ... force 12 from 64 kn)
BEAUFORT_KNOTS = (1, 4, 7, 11, 17, 22, 28, 34, 41, 48, 56, 64)


@dataclass
class Weather:
    wind_bft: int | None = None
    wind_dir_deg: int | None = None
    wave_m: float | None = None


def beaufort(knots: float) -> int:
    return sum(1 for limit in BEAUFORT_KNOTS if knots >= limit)


def _hour_value(url: str, lat: float, lon: float, at: datetime, fields: list[str]) -> dict:
    """The hourly values nearest to `at` (UTC) for one point; {} when there are none or the call fails."""
    day = at.date().isoformat()
    query = urlencode({
        # ~11 km: enough for the weather grid, and no exact position leaves the server
        "latitude": round(lat, 1),
        "longitude": round(lon, 1),
        "hourly": ",".join(fields),
        "wind_speed_unit": "kn",
        "timezone": "UTC",
        "start_date": day,
        "end_date": day,
    })
    request = Request(f"{url}?{query}", headers={"User-Agent": "Sefername/1.0"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            hourly = json.load(response).get("hourly", {})
    except (URLError, TimeoutError, ValueError, OSError):
        return {}
    hour = round(at.hour + at.minute / 60)
    index = min(hour, 23)
    return {field: (hourly.get(field) or [None] * 24)[index] for field in fields}


def noon_weather(lat: float, lon: float, at: datetime) -> Weather:
    """Wind (Beaufort and direction) and wave height at a position and time. Empty values on any problem."""
    at = at.astimezone(UTC)
    if at < datetime.now(UTC) - timedelta(days=OLDEST_DAYS):
        return Weather()
    wind = _hour_value(FORECAST_URL, lat, lon, at, ["wind_speed_10m", "wind_direction_10m"])
    # Over land or in a closed sea the marine model has no value: the wave height stays empty
    sea = _hour_value(MARINE_URL, lat, lon, at, ["wave_height"])
    speed, direction, wave = wind.get("wind_speed_10m"), wind.get("wind_direction_10m"), sea.get("wave_height")
    return Weather(
        wind_bft=beaufort(speed) if speed is not None else None,
        wind_dir_deg=round(direction) if direction is not None else None,
        wave_m=round(wave, 1) if wave is not None else None,
    )
