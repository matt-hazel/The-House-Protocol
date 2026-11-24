# weekly forecast dm

import logging

import pandas as pd

from house_protocol.alerts.discord import send_dm
from house_protocol.config import Settings
from house_protocol.forecast import scoring
from house_protocol.forecast.events import EVENTS
from house_protocol.forecast.ledger import load_ledger

logger = logging.getLogger(__name__)


def _open_lines(ledger: pd.DataFrame) -> list[str]:
    # newest live forecast per track

    live = ledger.loc[(ledger["kind"] == "live") & ledger["outcome"].isna()]
    lines = ["Open forecasts:"]

    for track, rows in live.groupby("track"):
        latest = rows.loc[rows["issued_on"] == rows["issued_on"].max()]
        by_model = latest.set_index("model")["probability"]
        resolves = latest["resolves_on"].iloc[0].strftime("%b %d")

        lines.append(EVENTS[track].question)
        lines.append(
            f" {by_model['conditional']:.1%} now, {by_model['climatology']:.1%} base rate "
            f"(resolves {resolves})"
        )

    return lines if len(lines) > 1 else ["Open forecasts: none yet"]


def _score_lines(ledger: pd.DataFrame, kind: str, label: str) -> list[str]:
    card = scoring.scorecard(ledger, kind)

    if card.empty:
        return [f"{label}: nothing resolved yet"]

    lines = [f"{label}:"]

    for (track, model), row in card.iterrows():
        if model == "climatology":
            continue

        lines.append(
            f" {track} {model}: skill {row['skill']:+.2f}, "
            f"about {row['eff_n']:.0f} independent windows"
        )

    return lines


def format_scorecard(ledger: pd.DataFrame) -> str:
    sections = [
        _open_lines(ledger),
        _score_lines(ledger, "live", "Live"),
        _score_lines(ledger, "backtest", "Backtest"),
    ]

    return "Forecast score card\n\n" + "\n\n".join("\n".join(lines) for lines in sections)


def run_scorecard(settings: Settings) -> None:
    if not (settings.discord_bot_token and settings.discord_user_id):
        logger.warning("Discord credentials not set, skip score")
        return

    ledger = load_ledger(settings.data_dir / "forecasts.parquet")

    if ledger.empty:
        logger.info("no forecasts, skip")
        return

    send_dm(settings.discord_user_id, settings.discord_bot_token, format_scorecard(ledger))
