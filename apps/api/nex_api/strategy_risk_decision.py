"""Server-authoritative, read-only candidate aggregation; NOT a broker authorization.

Multiple strategies and timeframes can disagree. No candidate, stale data,
unknown risk status, or inconsistent data may ever become a trading permission.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

ALLOWED_SIGNALS = {"LONG_CANDIDATE", "SHORT_CANDIDATE", "NEUTRAL"}
STRATEGY_IDS = frozenset({"trend-ladder", "range-fade", "breakout-scout", "mean-return"})
INTERVALS = frozenset({"5m", "15m", "1h", "4h", "1d"})

@dataclass(frozen=True)
class Candidate:
    symbol: str
    decision: str
    evidence: tuple[str, ...]
    intervals: tuple[str, ...]

def decide(strategies: list[Any], risk: Any) -> dict[str, Any]:
    """Fail closed: output is a diagnostic decision, NEVER an executable order."""
    reasons: list[str] = ["MAINNET_ORDER_ENGINE_NOT_CONNECTED"]
    if not bool(getattr(risk, "configured", False)):
        reasons.append("USER_DAILY_LIMIT_NOT_SET")
    if str(getattr(risk, "state", "")) != "MONITORING":
        reasons.append("RISK_EQUITY_NOT_MONITORING")
    if getattr(risk, "new_entries_blocked", True) is not False:
        reasons.append("RISK_BLOCKED")
    if len(strategies) != 4 or {getattr(s, "id", None) for s in strategies} != STRATEGY_IDS:
        reasons.append("STRATEGY_INVENTORY_INCOMPLETE")
    by_symbol: dict[str, dict[str, list[tuple[str, str]]]] = defaultdict(
        lambda: {"LONG_CANDIDATE": [], "SHORT_CANDIDATE": []}
    )
    active = 0
    stalls = 0
    for row in strategies:
        if (getattr(row, "id", None) not in STRATEGY_IDS
                or getattr(row, "interval", None) not in INTERVALS):
            reasons.append("INVALID_STRATEGY_PROJECTION")
            continue
        state = getattr(row, "status", None)
        if state == "STALLED":
            stalls += 1
        if state != "SCANNING":
            continue
        active += 1
        if (getattr(row, "execution_enabled", True) is not False
                or getattr(row, "ndsp_verified", True) is not False
                or getattr(row, "expires_in_seconds", 0) <= 0
                or getattr(row, "last_candle_closed_ms", None) is None
                or getattr(row, "last_checked_ms", None) is None):
            reasons.append("SCANNER_EVIDENCE_UNVERIFIED")
            continue
        side = getattr(row, "signal", None)
        if side not in ALLOWED_SIGNALS:
            reasons.append("SCANNER_SIGNAL_INVALID")
            continue
        if side == "NEUTRAL":
            continue
        symbol = getattr(row, "symbol", None)
        if not isinstance(symbol, str) or not symbol.endswith("USDT") or len(symbol) > 20:
            reasons.append("INVALID_MARKET_SYMBOL")
            continue
        by_symbol[symbol][side].append((row.id, row.interval))
    if not active:
        reasons.append("NO_SCANNERS_RUNNING")
    if stalls:
        reasons.append("SCANNER_STALLED")
    candidates = []
    for symbol, groups in sorted(by_symbol.items()):
        longs = groups["LONG_CANDIDATE"]
        shorts = groups["SHORT_CANDIDATE"]
        if longs and shorts:
            candidates.append({
                "symbol": symbol, "decision": "CONFLICT",
                "evidence": sorted({x[0] for x in longs + shorts}),
                "intervals": sorted({x[1] for x in longs + shorts}),
            })
            reasons.append("CONFLICTING_STRATEGY_SIGNALS")
        elif longs or shorts:
            signals = longs or shorts
            candidates.append({
                "symbol": symbol,
                "decision": "LONG_RESEARCH" if longs else "SHORT_RESEARCH",
                "evidence": sorted({x[0] for x in signals}),
                "intervals": sorted({x[1] for x in signals}),
            })
    if not candidates:
        reasons.append("NO_ACTIONABLE_CANDIDATE")
    return {
        "stage": "M3_RESEARCH_DECISION_GATE",
        "execution_allowed": False,
        "mainnet_orders_enabled": False,
        "ndsp_execution_verified": False,
        "risk": {
            "state": getattr(risk, "state", "UNAVAILABLE"),
            "daily_loss_pct": getattr(risk, "daily_loss_pct", None),
            "new_entries_blocked": getattr(risk, "new_entries_blocked", True),
            "opening_equity": getattr(risk, "opening_equity", None),
            "current_equity": getattr(risk, "current_equity", None),
        },
        "active_scanners": active,
        "stalled_scanners": stalls,
        "strategies": [
            {
                "id": row.id, "symbol": row.symbol, "interval": row.interval,
                "state": row.status, "signal": row.signal,
            } for row in strategies
        ],
        "candidates": candidates,
        "blockers": sorted(set(reasons)),
    }
