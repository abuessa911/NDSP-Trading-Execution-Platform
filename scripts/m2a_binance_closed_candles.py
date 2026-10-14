"""Manually invoked public read-only Binance smoke probe (no secrets or trades)."""

import argparse
import asyncio
import json
from decimal import Decimal

from nex_api.binance_closed_candles import MarketDataUnavailable, fetch_closed_candles


def json_default(value: object) -> str:
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError("Unsupported value")


async def main() -> None:
    parser = argparse.ArgumentParser(description="M2-A Binance closed candles, GET-only")
    parser.add_argument("--market", required=True, choices=("spot", "usdm_futures"))
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", choices=("5m", "15m"), default="5m")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    try:
        batch = await fetch_closed_candles(
            market=args.market, symbol=args.symbol, interval=args.interval, limit=args.limit,
        )
    except (MarketDataUnavailable, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason_code": str(exc)}))
        raise SystemExit(2) from None
    latest = batch.candles[-1]
    print(json.dumps({
        "status": "READ_ONLY_OK", "source": batch.source, "market": batch.market,
        "symbol": batch.symbol, "interval": batch.interval,
        "server_time_ms": batch.server_time_ms,
        "closed_candle_count": len(batch.candles),
        "latest_closed": {
            "open_time_ms": latest.open_time_ms, "close_time_ms": latest.close_time_ms,
            "open": latest.open, "high": latest.high,
            "low": latest.low, "close": latest.close, "volume": latest.volume,
        }, "orders_sent": 0,
    }, default=json_default, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
