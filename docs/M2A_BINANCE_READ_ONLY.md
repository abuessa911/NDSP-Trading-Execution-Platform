# M2-A — Binance closed-candle reader (review-only)

**Status: implementation in an isolated review branch; NOT deployed or production-accepted.**
M1 remains a draft. This change does not authorize Binance keys, account data,
trading/order methods, position changes, NDSP changes, or live/paper execution.

## Exact scope

- Public **Spot** `GET https://api.binance.com/api/v3/time` and
  `GET https://api.binance.com/api/v3/klines`.
- Public **USDⓈ-M Futures** `GET https://fapi.binance.com/fapi/v1/time` and
  `GET https://fapi.binance.com/fapi/v1/klines`.
- `BTCUSDT` and other uppercase ASCII symbols; interval **5m** or **15m**.
- Both market types return candlesticks without credentials. A USDⓈ-M Futures
  candle is market data, **not** a futures account or trade authorization.
- Data is held in memory only, as `Decimal` prices and integer UTC epoch
  milliseconds. No persistent job, DB migration, HTTP API route, NCM/NDSP
  runtime, account token, or front-end consumer is activated by this change.

## Guarantees and fail-closed behavior

- Only fixed public Binance origins and paths: never arbitrary base URLs or
  untrusted headers, no proxy inheritance or redirects, GET requests only.
- A server-clock GET precedes each kline GET; do not use the host clock as proof
  that a bar is closed. A candle with `close_time_ms >= server_time_ms` is dropped.
- Reject missing/invalid server time, missing candles, malformed / non-finite
  OHLCV, contradictory price ranges, incorrectly aligned timestamps, duplicate
  candles, non-contiguous time windows, and stale final closed candles (>2 bar
  durations since the close). Never substitute `0`, synthetic prices or last
  successful values for unavailable data.
- 5 second request timeout, no retries, limit 2–200 (default 100), rate limits
  and geography restrictions fail closed with bounded reason codes. Caller must
  schedule requests within exchange weights; this adapter does not poll.
- **This does not** prove real-world data freshness, regional availability,
  enterprise market-data redistributability, futures permission or exchange
  account access until an explicitly authorized read-only smoke check is run.

## Reproducible offline verification

```sh
PYTHONPATH=apps/api uv run --frozen pytest -q apps/api/tests/test_binance_closed_candles.py
uv run --frozen ruff check apps/api/nex_api/binance_closed_candles.py \
  apps/api/tests/test_binance_closed_candles.py scripts/m2a_binance_closed_candles.py
uv run --frozen mypy apps/api/nex_api
```

Optional **manual** public smoke check from a nonproduction environment with
permitted Binance access. No API keys needed:

```sh
PYTHONPATH=apps/api uv run --frozen python scripts/m2a_binance_closed_candles.py \
  --market spot --symbol BTCUSDT --interval 5m --limit 5
PYTHONPATH=apps/api uv run --frozen python scripts/m2a_binance_closed_candles.py \
  --market usdm_futures --symbol BTCUSDT --interval 15m --limit 5
```

`READ_ONLY_OK` means a read-only call supplied valid recent *closed* candles;
`BLOCKED` means do not feed data into a decision/execution system. The output
contains no trading instruction. Do not schedule or enable a production service
from the CLI until separate design, observability, rate-budget and integration
acceptance gates are approved. Binance API terms and local regulatory access
still apply.

## Next acceptance gates

1. M1 administrator security sign-off, separate from four hosted CI successes.
2. Hosted M2-A static+unit checks with **zero external/live API calls in CI**.
3. Authorized manual live **read-only** Spot/Futures checks from intended region;
   confirm data timestamps, symbol trading status and restrictions.
4. Explicit API consumer design with tenant controls and rate-limit budgeting;
   no direct public NEX route without server-side auth and audit.
5. M2-B signed, version-pinned, read-only NDSP adapter; no NDSP writes.

References: [Binance Spot Market Data](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/market-data-endpoints)
 and [USDⓈ-M Futures Market Data](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Kline-Candlestick-Data).
