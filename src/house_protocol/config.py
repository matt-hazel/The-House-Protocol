import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    log_level: str
    fred_api_key: str | None
    discord_bot_token: str | None
    discord_user_id: str | None
    tiingo_api_key: str | None


def load_settings() -> Settings:
    # builds settings for env

    user_id = os.getenv("DISCORD_USER_ID")

    return Settings(
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        fred_api_key=os.getenv("FRED_API_KEY"),
        discord_bot_token=os.getenv("DISCORD_BOT_TOKEN"),
        discord_user_id=user_id,
        tiingo_api_key=os.getenv("TIINGO_API_KEY"),
    )
