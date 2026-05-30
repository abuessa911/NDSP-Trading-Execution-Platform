from __future__ import annotations

SUPPORTED_MARKET_TYPES = {"spot", "futures"}
SPECIAL_ALLOWED_SYMBOLS = {"ALL_SPOT_USDT", "ALL_FUTURES_USDT", "ALL_USDT"}

QUOTE_SUFFIXES = (
    "USDT",
    "FDUSD",
    "USDC",
    "BUSD",
    "TUSD",
    "BTC",
    "ETH",
    "BNB",
    "EUR",
    "TRY",
)


def normalize_market_type(market_type: str | None) -> str:
    value = (market_type or "spot").strip().lower()
    if value not in SUPPORTED_MARKET_TYPES:
        raise ValueError("market_type must be 'spot' or 'futures'")
    return value


def normalize_symbol(symbol: str) -> str:
    value = (symbol or "").strip().upper().replace(" ", "")
    if not value:
        return ""

    if "/" in value:
        base, quote = value.split("/", 1)
        quote = quote.split(":", 1)[0]
        return f"{base}/{quote}"

    for quote in QUOTE_SUFFIXES:
        if value.endswith(quote) and len(value) > len(quote):
            base = value[: -len(quote)]
            return f"{base}/{quote}"

    return value


def compact_symbol(symbol: str) -> str:
    return normalize_symbol(symbol).replace("/", "")


def is_usdt_pair(symbol: str) -> bool:
    return normalize_symbol(symbol).endswith("/USDT")


def parse_allowed_symbols(raw: str) -> list[str]:
    values: list[str] = []
    for item in (raw or "").split(","):
        clean = item.strip().upper().replace(" ", "")
        if not clean:
            continue
        if clean in SPECIAL_ALLOWED_SYMBOLS:
            values.append(clean)
        else:
            values.append(normalize_symbol(clean))
    return values


def serialize_allowed_symbols(raw: str) -> str:
    values = parse_allowed_symbols(raw)
    return ",".join(values) if values else "BTC/USDT,ETH/USDT"
