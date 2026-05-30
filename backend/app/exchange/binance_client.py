import json
from functools import lru_cache

import ccxt

from app.core.config import settings
from app.services.symbols import normalize_market_type, normalize_symbol


class BinanceClient:
    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        market_type: str = "spot",
    ):
        self.mode = settings.BINANCE_MODE.lower()
        self.market_type = normalize_market_type(market_type)

        exchange_class = ccxt.binanceusdm if self.market_type == "futures" else ccxt.binance
        options = {"defaultType": "future" if self.market_type == "futures" else "spot"}

        self.exchange = exchange_class({
            "apiKey": api_key or "",
            "secret": api_secret or "",
            "enableRateLimit": True,
            "options": options,
        })

        if self.mode == "testnet":
            self.exchange.set_sandbox_mode(True)

    def load_markets(self) -> dict:
        return self.exchange.load_markets()

    def resolve_exchange_symbol(self, symbol: str) -> str:
        normalized = normalize_symbol(symbol)

        if self.market_type == "spot":
            return normalized

        markets = self.load_markets()
        for market in markets.values():
            market_symbol = normalize_symbol(market.get("symbol", ""))
            if market_symbol == normalized:
                return market.get("symbol") or normalized

        base, quote = normalized.split("/", 1) if "/" in normalized else (normalized, "USDT")
        return f"{base}/{quote}:{quote}"

    def get_ticker_price(self, symbol: str) -> float:
        normalized = normalize_symbol(symbol)

        if self.mode == "dryrun":
            return 100.0

        ticker = self.exchange.fetch_ticker(self.resolve_exchange_symbol(normalized))
        return float(ticker["last"])

    def market_order_by_notional(self, symbol: str, side: str, notional_usdt: float) -> dict:
        normalized = normalize_symbol(symbol)
        side = side.lower()
        price = self.get_ticker_price(normalized)
        amount = round(notional_usdt / price, 8)

        if self.mode == "dryrun":
            return {
                "dryrun": True,
                "market_type": self.market_type,
                "symbol": normalized,
                "side": side,
                "amount": amount,
                "price": price,
                "notional_usdt": notional_usdt,
                "status": "simulated",
            }

        if side not in {"buy", "sell"}:
            raise ValueError("Invalid order side")

        order = self.exchange.create_order(
            self.resolve_exchange_symbol(normalized),
            "market",
            side,
            amount,
        )
        return json.loads(json.dumps(order, default=str))


@lru_cache(maxsize=8)
def get_active_symbols(market_type: str, quote: str = "USDT") -> list[str]:
    selected_market_type = normalize_market_type(market_type)
    selected_quote = quote.upper()

    client = BinanceClient(market_type=selected_market_type)
    markets = client.load_markets()

    symbols: list[str] = []

    for market in markets.values():
        if not market.get("active", True):
            continue

        if market.get("quote") != selected_quote:
            continue

        if selected_market_type == "spot" and not market.get("spot", False):
            continue

        if selected_market_type == "futures" and not (market.get("swap", False) or market.get("future", False)):
            continue

        symbol = normalize_symbol(market.get("symbol", ""))

        if symbol.endswith(f"/{selected_quote}"):
            symbols.append(symbol)

    return sorted(set(symbols))


def is_symbol_supported(symbol: str, market_type: str) -> bool:
    normalized = normalize_symbol(symbol)
    return normalized in set(get_active_symbols(market_type, "USDT"))
