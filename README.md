# The House Protocol

A self-hosted early-warning and briefing system that runs on my homelab. It watches markets, the news and the weather, and sends me what matters on Discord. The name and the idea come from Mr. House in Fallout: a system that keeps a model of the world and acts on it.

It doesn't predict prices and it doesn't give trade signals. The goal is to flag changing conditions early, show where news outlets disagree, and publish probabilistic forecasts with a public record of how well they did.

## What it does today

- **Market data:** daily prices for 27 tickers (Tiingo) and six macro and credit-stress series (FRED), stored as Parquet with idempotent upserts.
- **Alerts:** watch and alert tiers for VIX, yield curve, credit spreads, drawdown, unusual price moves and geopolitical tension. Z-score baselines exclude the day being scored. Cooldowns and de-duplication stop repeat pings, and a signal is only recorded as sent once Discord confirms it.
- **Evening market digest** on Discord after the day's data lands.
- **Morning briefing** at 7:30 am: local weather, a world-conditions section, top stories, and headlines from eight outlets across the US and abroad, each labelled with its political lean so the framing is visible.
- **Story clustering:** headlines are grouped by story across outlets (TF-IDF cosine similarity, numpy only), with coverage counts and blindspots where only one side of the spectrum reports a story.
- **Geopolitical tension index:** daily GDELT event data (three years of history) aggregated for Russia/Ukraine, China/Taiwan and the Middle East, scored against same-weekday baselines.
- **Dashboard:** Grafana over a Postgres copy of the data, provisioned from files in the repo (data source and dashboard), reachable over Tailscale on desktop and phone.
- **Forecast ledger:** daily probabilistic forecasts for two events (a 7% SPY drawdown within 21 trading days, a VIX close at or above 25 within 10), logged append-only and scored against base-rate baselines. A weekly Discord scorecard reports what is open and how past forecasts did.
- NYSE-calendar-aware scheduling, running in Docker Compose on a homelab.
- Automated tests and linting (pytest, ruff).

## How it works

```
Tiingo, FRED, RSS feeds, Open-Meteo  ->  Parquet files  ->  rules and analysis  ->  Discord
|
+-> Forecast ledger -> Scoring -> Discord
|
+-> Postgres -> Grafana
```

One scheduler container fetches data on a schedule, analysis modules score it, and results are sent as Discord DMs. Each briefing section has its own fetcher, formatter and tests, so one failing source never blocks the others.

## Design choices

- **Making bias visible instead of removing it.** Headlines are grouped by story across outlets, and syndicated copies (such as AP text run by another outlet) count once. Lean labels are editable config, not facts.
- **No look-ahead.** Baselines exclude the day being scored, and lagged series are handled explicitly.
- **Honest forecasting.** Every forecast is a probability with a fixed resolution rule, written to an append-only ledger. Baselines use only forecasts that had already resolved on the issue date, so the future cannot leak in. Models have to beat a base rate on the Brier score to count, and results are split into live and backtest so history is never passed off as a track record.
- **Questions that aren't trivial.** An early version asked "will SPY be 7% below its high at some point in the next 21 days", which is almost always true when it already is. The scorecard showed implausibly high skill, which exposed that, so forecasts are now only issued on days the event hasn't already happened. The alert rules cover the days it has.
- **Secrets stay in `.env`.** API errors are sanitized so keys and coordinates don't reach the logs.

## Forecasting

Two event tracks, each a yes/no question with a fixed horizon:

| Track | Question | Horizon |
|---|---|---|
| `spy_drawdown` | SPY closes 7% or more below its 52 week high | 21 trading days |
| `vix_stress` | VIX closes at or above 25 | 10 trading days |

Two baseline models issue a forecast each weekday, and later models must beat them:

- **climatology:** how often the event happened in all resolved history.
- **conditional:** the same, but only from days that started in a similar state (for example 2-4% below the high), shrunk toward climatology when that state has little history.

Scoring:

- **Brier score** and **skill** (1 minus the model's Brier score over climatology's, on the same dates). Zero means no better than the base rate.
- **Calibration** by probability bin: when it says about 10%, does it happen about 10% of the time?
- **Effective sample size.** Forecasts on consecutive days share most of their window, so independent evidence is roughly the number of forecasts divided by the horizon. It's reported next to every score.

Backtest rows are rebuilt walk-forward from history and flagged `kind='backtest'`. Live rows are issued by the scheduler and never edited. Changing an event's definition means a new track, not a rewrite.

## Roadmap

- [x] Setup, ingestion, alerts, morning briefing
- [x] Story clustering: top stories, coverage lines, blindspots
- [x] Geopolitical tension index from GDELT
- [x] Dashboard (Grafana over Tailscale, desktop and phone layouts), with Discord kept for alerts
- [ ] Change weather location without editing `.env`: by Discord DM command (`!location Boston`  via Open-Meteo geocoding) and/or from the dashboard
- [x] Forecast ledger with scoring, starting with base-rate forecasts
- [ ] Third forecast track: geopolitical tension
- [ ] Regime detection (HMM, GARCH)
- [ ] Drawdown risk model (LightGBM, walk-forward validation, SHAP)
- [ ] Optional LLM synthesis of what outlets agree and dispute

## Running it

1. Copy `.env.example` to `.env` and fill in: `FRED_API_KEY`, `TIINGO_API_KEY`, `DISCORD_BOT_TOKEN`, `DISCORD_USER_ID`, `POSTGRES_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`, `DATABASE_URL`, and optionally `WEATHER_LAT`, `WEATHER_LON`, `WEATHER_PLACE`.
2. Backfill history once, then start the stack:
   ```
   python -m house_protocol.ingest.backfill prices
   python -m house_protocol.ingest.backfill macro
   python -m house_protocol.ingest.backfill_gdelt --years 3
   docker compose up -d --build
   ```
3. Grafana is at `http://localhost:3000` and the Postgres data source and dashboard load automatically from `dashboard/provisioning`. Log in as `admin` with `GRAFANA_ADMIN_PASSWORD`. On Linux, create the data folder first: `mkdir grafana && sudo chown -R 472:472 grafana`.
4. Build the forecast backtest once (the live job then appends daily at 15:45 New York time):
5. Tests: `pip install -e ".[dev]"` then `pytest`.

### Deploying to a homelab
Clone the repo on the server, copy `.env` and `data/` over with `scp` (they are not in git), and run `docker compose up -d --build`. Run it on only one machine, or every briefing and alert is sent twice.

## Stack

Python 3.12 · pandas · numpy · pyarrow · SQLAlchemy · APScheduler · Postgres · Grafana · Docker Compose · Discord API · pytest · ruff