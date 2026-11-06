# The House Protocol

A market risk monitor that runs on my homelab. It pulls daily market and macro data, keeps it in Parquet files, and (eventually) scores how stressed things look and sends me a Discord message when something changes.

It's an early-warning tool. It doesn't predict prices and it doesn't give buy or sell signals.

## Status

Early. Right now it does the boring but necessary part:

- Pulls daily prices for 27 tickers (broad ETFs, sectors, some large caps, agriculture, nuclear) from Tiingo
- Pulls six macro and stress series from FRED (VIX, yield curve, credit spreads, rates)
- Stores everything as Parquet, and reruns don't create duplicates
- Runs on a schedule inside Docker and skips weekends and NYSE holidays

Still to come: Discord alerts, GDELT news data, regime detection, a drawdown risk model, and a Grafana dashboard.

## How it works

```
Tiingo / FRED  ->  ingest  ->  Parquet files in data/  ->  (features, models, alerts later)
                      ^
                 APScheduler
```

The scheduler checks for new daily prices every 30 minutes in the evening (New York time) and stops once the day's data is in. Macro series are checked twice a day on weekdays. Each run refetches a short window and upserts it, so running it twice gives the same result as running it once.

## Setup

You need Python 3.12 and a free API key from [Tiingo](https://www.tiingo.com) and [FRED](https://fred.stlouisfed.org/docs/api/api_key.html).

```
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
cp .env.example .env          # then fill in your keys
```

`.env` is gitignored. Don't commit it.

## Getting the history

The daily jobs only fetch recent days, so load the full history once:

```
python -m house_protocol.ingest.backfill prices
python -m house_protocol.ingest.backfill macro
```

The price backfill downloads about 40 MB, so don't run it over and over. The free Tiingo plan has a monthly data cap.

## Running it

With Docker:

```
docker compose up -d --build
docker compose logs -f
```

Data is written to `./data`, which is mounted into the container.

## Tests

```
ruff check .
pytest
```

CI runs both on every push. Tests don't touch the network.

## Project layout

```
src/house_protocol/
  config.py        settings from environment variables
  scheduler.py     scheduled jobs
  ingest/          Tiingo, FRED, backfill, ticker lists
  storage/         Parquet read and upsert helpers
tests/
notebooks/         scratch scripts for checking data
data/              gitignored
```

## Notes

- Everything is daily data. No intraday.
- Paid APIs and LLM calls are off the table on purpose. Anything ML-related runs locally.
- One of the credit spread series (`BAMLH0A0HYM2`) only has a few years of history on FRED, so `BAA10Y` is used for older stress periods like 2008.
- When features get built later, macro series will be lagged so nothing uses data that wasn't published yet.
