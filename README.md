# The House Protocol

A self-hosted early-warning and briefing system that runs on my homelab. It watches markets, the news and the weather, and sends me what matters on Discord. The name and the idea come from Mr. House in Fallout: a system that keeps a model of the world and acts on it.

It doesn't predict prices and it doesn't give trade signals. The goal is to flag changing conditions early, show where news outlets disagree, and eventually publish probabilistic forecasts with a public record of how well they did.

## What it does today

- **Market data:** daily prices for 27 tickers (Tiingo) and six macro and credit-stress series (FRED), stored as Parquet with idempotent upserts.
- **Alerts:** watch and alert tiers for VIX, yield curve, credit spreads, drawdown and unusual price moves. Z-score baselines exclude the day being scored. Cooldowns and de-duplication stop repeat pings, and a signal is only recorded as sent once Discord confirms it.
- **Evening market digest** on Discord after the day's data lands.
- **Morning briefing** at 7:30 am: local weather, plus headlines from eight outlets across the US and abroad, each labelled with its political lean so the framing is visible.
- NYSE-calendar-aware scheduling, running in Docker Compose.
- Automated tests and linting (pytest, ruff).

## How it works

```
Tiingo, FRED, RSS feeds, Open-Meteo  ->  Parquet files  ->  rules and analysis  ->  Discord
```

One scheduler container fetches data on a schedule, analysis modules score it, and results are sent as Discord DMs. Each briefing section has its own fetcher, formatter and tests, so one failing source never blocks the others.

## Design choices

- **Making bias visible instead of removing it.** Headlines are grouped by story across outlets, and syndicated copies (such as AP text run by another outlet) count once. Lean labels are editable config, not facts.
- **No look-ahead.** Baselines exclude the day being scored, and lagged series are handled explicitly.
- **Honest forecasting.** Forecasts are logged with a probability and a resolution rule, then scored (Brier score, calibration). Models have to beat simple baselines to count.
- **Secrets stay in `.env`.** API errors are sanitized so keys and coordinates don't reach the logs.

## Roadmap

- [x] Setup, ingestion, alerts, morning briefing
- [x] Story clustering: top stories, coverage lines, blindspots (in progress)
- [x] Geopolitical tension index from GDELT
- [x] Dashboard (Grafana over Tailscale, desktop and phone layouts), with Discord kept for alerts
- [ ] Forecast ledger with scoring, starting with base-rate forecasts
- [ ] Regime detection (HMM, GARCH)
- [ ] Drawdown risk model (LightGBM, walk-forward validation, SHAP)
- [ ] Optional LLM synthesis of what outlets agree and dispute

## Running it

1. Copy `.env.example` to `.env` and fill in: `FRED_API_KEY`, `TIINGO_API_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_USER_ID`, and optionally `WEATHER_LAT`, `WEATHER_LON`, `WEATHER_PLACE`.
2. Backfill history once, then start the scheduler:
   ```
   python -m house_protocol.ingest.backfill prices
   python -m house_protocol.ingest.backfill macro
   docker compose up -d --build
   ```
3. Tests: `pip install -e ".[dev]"` then `pytest`.

## Stack

Python 3.12 · pandas · numpy · pyarrow · APScheduler · Docker Compose · Discord API · pytest · ruff
