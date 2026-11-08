import pytest
import requests

from house_protocol.briefing import weather
from house_protocol.config import Settings

SAMPLE = {
    "current": {
        "temperature_2m": 46.6,
        "apparent_temperature": 40.7,
        "weather_code": 3,
        "wind_speed_10m": 8.5,
    },
    "daily": {
        "weather_code": [3, 95],
        "temperature_2m_max": [59.6, 56.1],
        "temperature_2m_min": [45.0, 43.6],
        "precipitation_probability_max": [16, 80],
        "wind_speed_10m_max": [11.7, 17.0],
    },
}


class FakeResponse:
    def __init__(self, payload=None, status=200, error_text="boom"):
        self.payload = payload
        self.status_code = status
        self.error_text = error_text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(self.error_text, response=self)

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        return self.response


def make_settings(**overrides):
    base = {
        "data_dir": ".",
        "log_level": "INFO",
        "fred_api_key": None,
        "discord_bot_token": None,
        "discord_user_id": None,
        "tiingo_api_key": None,
    }
    return Settings(**{**base, **overrides})


def test_describe_known_and_unknown_codes():
    assert weather.describe(3) == "overcast"
    assert weather.describe(12345) == "code 12345"


def test_format_weather_lines():
    text = weather.format_weather(SAMPLE, "Home")

    assert "**Weather, Home**" in text
    assert "Now 47°F (feels 41°F), overcast" in text
    assert "Today: 60°/45°F, overcast, 16% chance of precip, wind up to 12 mph" in text
    assert "Tomorrow: 56°/44°F, thunderstorm, 80% chance of precip" in text


def test_format_weather_flags_severe_forecast():
    assert "Heads up" in weather.format_weather(SAMPLE, "Home")


def test_format_weather_quiet_day_has_no_warning():
    calm = {**SAMPLE, "daily": {**SAMPLE["daily"], "weather_code": [3, 3]}}

    assert "Heads up" not in weather.format_weather(calm, "Home")


def test_high_wind_triggers_warning():
    windy = {
        **SAMPLE,
        "daily": {**SAMPLE["daily"], "weather_code": [3, 3], "wind_speed_10m_max": [11.0, 45.0]},
    }

    assert "Heads up" in weather.format_weather(windy, "Home")


def test_fetch_sends_coordinates_and_units():
    session = FakeSession(FakeResponse(SAMPLE))

    data = weather.fetch_forecast(40.71, -74.01, session)

    _, params = session.calls[0]
    assert data == SAMPLE
    assert params["latitude"] == 40.71
    assert params["temperature_unit"] == "fahrenheit"


def test_fetch_error_does_not_leak_coordinates():
    session = FakeSession(
        FakeResponse(status=500, error_text="500 for url ...latitude=40.71&longitude=-74.01")
    )

    with pytest.raises(RuntimeError) as exc:
        weather.fetch_forecast(40.71, -74.01, session)

    assert "40.71" not in str(exc.value)
    assert "status=500" in str(exc.value)


def test_get_weather_text_none_without_location():
    assert weather.get_weather_text(make_settings()) is None


def test_get_weather_text_with_location():
    session = FakeSession(FakeResponse(SAMPLE))
    settings = make_settings(weather_lat=40.71, weather_lon=-74.01, weather_place="NYC")

    text = weather.get_weather_text(settings, session)

    assert "**Weather, NYC**" in text
