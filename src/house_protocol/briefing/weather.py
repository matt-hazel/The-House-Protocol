# Current weather conditions and a two day forecast


import requests

from house_protocol.config import Settings

BASE_URL = "https://api.open-meteo.com/v1/forecast"


WMO_CODES = {
    0: "clear",
    1: "mostly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    56: "freezing drizzle",
    57: "freezing drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    66: "freezing rain",
    67: "freezing rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    77: "snow grains",
    80: "light showers",
    82: "heavy showers",
    85: "snow showers",
    86: "heavy snow showers",
    95: "thunderstorm",
    96: "thunderstorm with hail",
    99: "thunderstorm with hail",
}

SEVERE_CODES = {65, 66, 67, 75, 82, 86, 95, 96, 99}
HIGH_WIND_MPH = 40


def describe(code: int) -> str:
    return WMO_CODES.get(code, f"code {code}")


def fetch_forecast(lat: float, lon: float, session: requests.Session) -> dict:
    # One call returns current conditions for today and tomorrow

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_probability_max,wind_speed,10m_max"
        ),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": 2,
    }

    try:
        resp = session.get(BASE_URL, params=params, timeout=30)
        resp.raise_for_status()

    except requests.RequestException as exc:
        # request url contains home coords

        status = getattr(exc.response, "status_code", None)
        raise RuntimeError(f"Open_Meteo request failed, status={status}") from None

    return resp.json()


def _day_line(label: str, daily: dict, i: int) -> str:
    return (
        f"{label}: {daily['temperature_2m_max'][i]:.0f}°/{daily['temperature_2m_min'][i]:.0f}°F,"
        f"{describe(daily['weather_code'][i])}, "
        f"{daily['precipitation_probability_max'][i]}% chance of precip, "
        f"wind up to {daily['wind_speed_10m_max'][i]:.0f} mph"
    )


def format_weather(data: dict, place: str) -> str:
    current, daily = data["current"], data["daily"]

    lines = [
        f"**Weather, {place}**",
        f"Now {current['temperature_2m']:.0f}°F "
        f"(feels {current['apparent_temperature']:.0f}°F), {describe(current['weather_code'])}",
        _day_line("Today", daily, 0),
        _day_line("Tomorrow", daily, 1),
    ]

    severe = any(code in SEVERE_CODES for code in daily["weather_code"])
    windy = max(daily["wind_speed_10m_max"]) >= HIGH_WIND_MPH

    if severe or windy:
        lines.append("Heads up: rough weather in the forecast.")

    return "\n".join(lines)


def get_weather_text(settings: Settings, session: requests.Session | None = None) -> str | None:
    # Weather section text, or None when no location is configured

    if settings.weather_lat is None or settings.weather_lon is None:
        return None

    session = session or requests.Session()
    data = fetch_forecast(settings.weather_lat, settings.weather_lon, session)

    return format_weather(data, settings.weather_place)
