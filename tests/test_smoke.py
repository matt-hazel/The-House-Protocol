from pathlib import Path

from house_protocol.config import load_settings

ENV_VARS = [
    "DATA_DIR",
    "LOG_LEVEL",
    "FRED_API_KEY",
    "DISCORD_BOT_TOKEN",
    "DISCORD_USER_ID",
    "TIINGO_API_KEY",
]


def test_load_settings_default(monkeypatch):
    for var in ENV_VARS:
        monkeypatch.delenv(var, raising=False)

    settings = load_settings()

    assert settings.data_dir == Path("data")
    assert settings.log_level == "INFO"
    assert settings.fred_api_key is None
    assert settings.discord_bot_token is None
    assert settings.discord_user_id is None
    assert settings.tiingo_api_key is None


def test_load_settings_with_env(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("FRED_API_KEY", "fred-key")
    monkeypatch.setenv("DISCORD_USER_ID", "12345")
    monkeypatch.setenv("TIINGO_API_KEY", "tiingo-key")

    settings = load_settings()

    assert settings.data_dir == tmp_path
    assert settings.log_level == "DEBUG"
    assert settings.fred_api_key == "fred-key"
    assert settings.discord_user_id == "12345"
    assert settings.tiingo_api_key == "tiingo-key"
