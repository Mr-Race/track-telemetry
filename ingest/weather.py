"""Session weather enrichment: Open-Meteo's free, keyless historical
archive API (https://open-meteo.com/en/docs/historical-weather-api),
queried with the track's location and the session's start time.
"""

import json
import urllib.parse
import urllib.request
from datetime import timedelta

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# WMO weather interpretation codes; see https://open-meteo.com/en/docs
# for the full table.
WMO_CODES = {
    0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Rime fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
    56: "Freezing drizzle", 57: "Dense freezing drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    66: "Freezing rain", 67: "Heavy freezing rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Violent showers",
    85: "Light snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm", 96: "Thunderstorm, slight hail",
    99: "Thunderstorm, heavy hail",
}

EMPTY = {
    "weather": None, "air_temp_f": None, "humidity_pct": None,
    "wind_mph": None, "precip_in": None, "weather_observed_at": None,
}


def fetch_weather(lat, lon, start_time_utc):
    """Weather at (lat, lon) nearest to start_time_utc (a tz-aware UTC
    datetime), via Open-Meteo's hourly historical archive. Returns a
    dict matching dbo.sessions' weather columns."""
    date_str = start_time_utc.strftime("%Y-%m-%d")
    end_date_str = (start_time_utc + timedelta(days=1)).strftime("%Y-%m-%d")
    params = {
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": date_str,
        "end_date": end_date_str,
        "hourly": "temperature_2m,relative_humidity_2m,precipitation,"
                  "wind_speed_10m,weather_code",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "UTC",
    }
    url = ARCHIVE_URL + "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=15) as resp:
        data = json.loads(resp.read())

    hourly = data["hourly"]
    target = start_time_utc.replace(minute=0, second=0, microsecond=0)
    if start_time_utc.minute >= 30:
        target += timedelta(hours=1)
    idx = hourly["time"].index(target.strftime("%Y-%m-%dT%H:00"))

    return {
        "weather": WMO_CODES.get(hourly["weather_code"][idx]),
        "air_temp_f": hourly["temperature_2m"][idx],
        "humidity_pct": hourly["relative_humidity_2m"][idx],
        "wind_mph": hourly["wind_speed_10m"][idx],
        "precip_in": hourly["precipitation"][idx],
        "weather_observed_at": target.replace(tzinfo=None),
    }
