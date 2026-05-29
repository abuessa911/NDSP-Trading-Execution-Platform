import json
import ccxt
from app.core.config import settings


class BinanceClient:
    def __init__(self, api_key: str | None = None, api_secret: str | None = None):
        self.mode = settings.BINANCE_MODE.lower()

        self.exchange = ccxt.binance({
            "apiKey": api_key or "",
            "secret": api_secret or "",
            "enableRateLimit": True,
            "options": {
                "defaultType": "spot",
            },
        })

        if self.mode == "testnet":
            self.exchange.set_sandbox_mode(True)

    def get_ticker_price(self, symbol: str) -> float:
        if self.mode == "dryrun":
            # سعر تجريبي فقط. عند testnet/live سيتم جلب السعر الحقيقي.
            return 100.0

        ticker = self.exchange.fetch_ticker(symbol)
        return float(ticker["last"])

    def market_order_by_notional(self, symbol: str, side: str, notional_usdt: float) -> dict:
        side = side.lower()
        price = self.get_ticker_price(symbol)
        amount = round(notional_usdt / price, 8)

        if self.mode == "dryrun":
            return {
                "dryrun": True,
                "symbol": symbol,
                "side": side,
                "amount": amount,
                "price": price,
                "notional_usdt": notional_usdt,
                "status": "simulated",
            }

        if side == "buy":
            order = self.exchange.create_market_buy_order(symbol, amount)
        elif side == "sell":
            order = self.exchange.create_market_sell_order(symbol, amount)
        else:
            raise ValueError("Invalid order side")

        return json.loads(json.dumps(order, default=str))
