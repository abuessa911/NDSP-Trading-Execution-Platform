import json
from sqlalchemy.orm import Session
from app.models.models import User, TradeLog
from app.services.crypto_service import decrypt_text
from app.services.risk import validate_trade
from app.exchange.binance_client import BinanceClient
from app.services.symbols import normalize_market_type, normalize_symbol
from app.services.notifications import send_telegram, send_email
from app.core.config import settings



def calculate_protective_prices(user, side: str, entry_price: float) -> tuple[float, float]:
    """
    يحسب أسعار Stop Loss و Take Profit كمرحلة آمنة أولى.
    لا يرسل أوامر حماية فعلية إلى Binance في هذه المرحلة.
    """
    if not user.settings or entry_price <= 0:
        return 0.0, 0.0

    stop_loss_pct = float(getattr(user.settings, "stop_loss_pct", 0) or 0)
    take_profit_pct = float(getattr(user.settings, "take_profit_pct", 0) or 0)

    side = side.upper()

    stop_loss_price = 0.0
    take_profit_price = 0.0

    if side == "BUY":
        if stop_loss_pct > 0:
            stop_loss_price = entry_price * (1 - stop_loss_pct / 100)
        if take_profit_pct > 0:
            take_profit_price = entry_price * (1 + take_profit_pct / 100)

    elif side == "SELL":
        if stop_loss_pct > 0:
            stop_loss_price = entry_price * (1 + stop_loss_pct / 100)
        if take_profit_pct > 0:
            take_profit_price = entry_price * (1 - take_profit_pct / 100)

    return round(stop_loss_price, 8), round(take_profit_price, 8)



async def place_protective_orders_testnet(exchange, symbol: str, side: str, amount: float, stop_loss_price: float, take_profit_price: float) -> dict:
    """
    محاولة آمنة لوضع أوامر حماية على Binance Testnet فقط.
    لا تعمل في live.
    ملاحظة: Spot OCO قد يفشل حسب دعم testnet/الزوج/الرصيد. الفشل يتم تسجيله ولا يوقف الصفقة الأصلية.
    """
    result = {
        "attempted": False,
        "stop_loss_order": None,
        "take_profit_order": None,
        "errors": []
    }

    if settings.BINANCE_MODE != "testnet":
        result["errors"].append("Protective orders are allowed only in testnet in this phase")
        return result

    if amount <= 0:
        result["errors"].append("Amount is zero")
        return result

    side = side.upper()
    protective_side = "SELL" if side == "BUY" else "BUY"

    result["attempted"] = True

    # Take Profit: limit order
    if take_profit_price and take_profit_price > 0:
        try:
            tp = await exchange.create_order(
                symbol=symbol,
                type="limit",
                side=protective_side.lower(),
                amount=amount,
                price=take_profit_price,
                params={"timeInForce": "GTC"},
            )
            result["take_profit_order"] = tp
        except Exception as exc:
            result["errors"].append(f"take_profit_failed: {repr(exc)}")

    # Stop Loss: stop-limit style if supported by exchange/testnet
    if stop_loss_price and stop_loss_price > 0:
        try:
            if protective_side == "SELL":
                stop_limit_price = stop_loss_price * 0.999
            else:
                stop_limit_price = stop_loss_price * 1.001

            sl = await exchange.create_order(
                symbol=symbol,
                type="stop_loss_limit",
                side=protective_side.lower(),
                amount=amount,
                price=round(stop_limit_price, 8),
                params={
                    "stopPrice": stop_loss_price,
                    "timeInForce": "GTC",
                },
            )
            result["stop_loss_order"] = sl
        except Exception as exc:
            result["errors"].append(f"stop_loss_failed: {repr(exc)}")

    return result


async def execute_signal(
    db: Session,
    user: User,
    symbol: str,
    side: str,
    notional_usdt: float,
    reason: str,
) -> TradeLog:
    symbol = normalize_symbol(symbol)
    side = side.upper()
    market_type = normalize_market_type(getattr(user.settings, "market_type", "spot") if user.settings else "spot")

    ok, risk_reason = validate_trade(db, user, symbol, side, notional_usdt)

    if not ok:
        trade = TradeLog(
            user_id=user.id,
            symbol=symbol,
            side=side,
            amount=0,
            price=0,
            notional_usdt=notional_usdt,
            status="rejected",
            mode=settings.BINANCE_MODE,
            reason=risk_reason,
            exchange_response="",
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        return trade

    api_key = None
    api_secret = None

    if settings.BINANCE_MODE in ["testnet", "live"]:
        if not user.api_key:
            raise ValueError("Binance API key is missing")

        api_key = decrypt_text(user.api_key.api_key_encrypted)
        api_secret = decrypt_text(user.api_key.api_secret_encrypted)

    client = BinanceClient(api_key=api_key, api_secret=api_secret, market_type=market_type)
    response = client.market_order_by_notional(symbol, side, notional_usdt)

    amount = float(response.get("amount", 0) or 0)
    price = float(response.get("price", 0) or 0)
    status = response.get("status", "submitted")

    stop_loss_price, take_profit_price = calculate_protective_prices(
        user=user,
        side=side,
        entry_price=price,
    )

    protective_orders_status = "preview"
    protective_orders_result = None

    if stop_loss_price > 0 or take_profit_price > 0:
        protective_orders_status = "preview_calculated"

        if settings.BINANCE_MODE == "testnet" and status in ["closed", "filled"]:
            protective_orders_result = await place_protective_orders_testnet(
                exchange=client.exchange,
                symbol=symbol,
                side=side,
                amount=amount,
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
            )

            if protective_orders_result and protective_orders_result.get("attempted"):
                if protective_orders_result.get("errors"):
                    protective_orders_status = "testnet_failed"
                else:
                    protective_orders_status = "testnet_submitted"

    trade = TradeLog(
        user_id=user.id,
        symbol=symbol,
        side=side.upper(),
        amount=amount,
        price=price,
        notional_usdt=notional_usdt,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
        protective_orders_status=protective_orders_status,
        status=status,
        mode=settings.BINANCE_MODE,
        reason=reason,
        exchange_response=json.dumps({
            "entry_order": response,
            "protective_orders": protective_orders_result,
        }, ensure_ascii=False),
    )

    db.add(trade)
    db.commit()
    db.refresh(trade)

    message = (
        f"🚨 NDSP Trading Bot\n\n"
        f"User: {user.email}\n"
        f"Mode: {settings.BINANCE_MODE}\n"
        f"Symbol: {symbol}\n"
        f"Side: {side.upper()}\n"
        f"Notional: {notional_usdt} USDT\n"
        f"Amount: {amount}\n"
        f"Price: {price}\n"
        f"Status: {status}\n"
        f"Stop Loss Preview: {stop_loss_price}\n"
        f"Take Profit Preview: {take_profit_price}\n"
        f"Protective Status: {protective_orders_status}\n"
        f"Protective Orders Result: {protective_orders_result}\n"
        f"Reason: {reason}"
    )

    if user.settings and user.settings.telegram_enabled:
        await send_telegram(message)

    if user.settings and user.settings.email_enabled:
        try:
            send_email(user.email, "NDSP Trading Bot Alert", message)
        except Exception:
            pass

    return trade
