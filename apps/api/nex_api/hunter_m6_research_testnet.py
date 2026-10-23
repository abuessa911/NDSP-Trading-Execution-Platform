"""Hunter M6 research->Testnet sizing preview (private CLI, zero order writes).

Separates public research market signals from verified Testnet account equity.
Never treats M2 Mainnet read-only equity or M3 research candidates as order permission.
No scheduler, HTTP route, brokerage write, or automatic trading.
"""
from __future__ import annotations
import argparse
import asyncio
from decimal import Decimal
import json
from pathlib import Path
import sys

from nex_api import hunter_live_executor as legacy
from nex_api import hunter_m5_testnet_pilot as m5
from nex_api.binance_closed_candles import fetch_closed_candles, MarketDataUnavailable
from nex_api.strategy_signals import STRATEGIES, StrategyDataError, evaluate

STRATEGY_IDS = frozenset(s.id for s in STRATEGIES)
BLOCKERS = ("USER_RISK_TO_TESTNET_NOT_AUTOMATICALLY_LINKED",
            "FOUR_STRATEGIES_NOT_BROKER_APPROVED",
            "REAL_ORDER_EXECUTION_DISABLED",
            "NDSP_EXECUTION_NOT_VERIFIED")


def config_readiness(config):
    """Report missing user parameters without selecting values on their behalf."""
    if not isinstance(config, dict) or not config:
        return ["PRIVATE_CONFIG_MISSING"]
    reasons = []
    if config.get("mode") != "testnet":
        reasons.append("TESTNET_MODE_REQUIRED")
    if config.get("mainnet_enabled") is True:
        reasons.append("MAINNET_FLAG_FORBIDDEN")
    if config.get("strategy") not in ("UNSELECTED", "ema20_50_long_only"):
        reasons.append("UNKNOWN_LEGACY_STRATEGY")
    for field in ("daily_loss_pct", "trade_risk_pct", "max_exposure_pct", "stop_pct"):
        try:
            if field not in config:
                raise ValueError()
            legacy.pct(config[field])
        except (legacy.Halt, ValueError):
            reasons.append(field.upper() + "_USER_SELECTION_REQUIRED")
    if not reasons:
        if legacy.pct(config["trade_risk_pct"]) > legacy.pct(config["daily_loss_pct"]):
            reasons.append("PER_TRADE_RISK_EXCEEDS_DAILY_LIMIT")
        if legacy.pct(config["stop_pct"]) > Decimal("20"):
            reasons.append("STOP_EXCEEDS_PRIVATE_GUARD")
    if not config.get("symbol"):
        reasons.append("SYMBOL_NOT_CONFIGURED")
    return reasons


def plan_candidates(scans, config, equity=None, opening=None, filters=None):
    """Pure, read-only assessment. Does not create a broker authorization or order intent."""
    if not isinstance(scans, list) or len(scans) != len(STRATEGIES):
        raise ValueError("STRATEGY_SET_INCOMPLETE")
    if {row.get("id") for row in scans if isinstance(row, dict)} != STRATEGY_IDS:
        raise ValueError("STRATEGY_SET_INVALID")
    reasons = config_readiness(config)
    by_symbol = {}
    for row in scans:
        if row.get("signal") not in ("LONG_CANDIDATE", "SHORT_CANDIDATE", "NEUTRAL"):
            raise ValueError("INVALID_STRATEGY_SIGNAL")
        if not row.get("closed_candles_verified"):
            raise ValueError("CLOSED_CANDLE_PROOF_REQUIRED")
        symbol = row["symbol"]
        by_symbol.setdefault(symbol, set()).add(row["signal"])
    for signals in by_symbol.values():
        if "LONG_CANDIDATE" in signals and "SHORT_CANDIDATE" in signals:
            reasons.append("CONFLICTING_SIGNALS")
    if equity is None or opening is None:
        reasons.append("TESTNET_EQUITY_NOT_VERIFIED")
    else:
        try:
            original = legacy.D(opening, positive=True)
            reference = {"date": legacy.day(), "opening": str(original),
                         "daily_pct": config.get("daily_loss_pct", "0")}
            check = legacy.guarded_state(reference, "read-only-preview-only", equity,
                                         legacy.day(), config.get("daily_loss_pct", "0"))
            assert check["opening"] == str(original)
        except (legacy.Halt, AssertionError):
            reasons.append("TESTNET_DAILY_RISK_UNVERIFIED")
    results = []
    for row in scans:
        entry = {"id": row["id"], "symbol": row["symbol"],
                 "interval": row["interval"], "signal": row["signal"],
                 "order_submittable": False, "source": "PUBLIC_CLOSED_CANDLES_RESEARCH"}
        if row["signal"] == "SHORT_CANDIDATE":
            entry["blocker"] = "SHORT_EXECUTION_NOT_IMPLEMENTED"
        elif row["signal"] == "LONG_CANDIDATE":
            entry["blocker"] = "RESEARCH_SIGNAL_REQUIRES_STRATEGY_VALIDATION"
            # No quantity exposed unless a verified Testnet balance, explicit operator
            # risk parameters AND symbol-specific exchange filters are all available.
            if not reasons and isinstance(filters, dict) and row["symbol"] in filters:
                f = filters[row["symbol"]]
                try:
                    entry_price = legacy.D(row["close"], positive=True)
                    stop = entry_price * (1 - legacy.pct(config["stop_pct"]) / 100)
                    quantity = legacy.exposure_plan(
                        equity, opening, config["daily_loss_pct"],
                        config["trade_risk_pct"], config["max_exposure_pct"],
                        entry_price, stop, f["step"], f["minimum"], f["min_notional"])
                    entry["hypothetical_testnet_quantity"] = str(quantity)
                    entry["not_a_trade_instruction"] = True
                except (legacy.Halt, KeyError, TypeError):
                    entry["blocker"] = "TESTNET_SIZING_UNVERIFIED"
        results.append(entry)
    return {"status": "M6_TESTNET_RESEARCH_PLAN_ONLY",
            "mainnet_orders": False, "testnet_orders": False,
            "automatic_trading": False,
            "user_risk_requires_explicit_settings": bool(config_readiness(config)),
            "blockers": sorted(set(BLOCKERS + tuple(reasons))),
            "strategies": results}


async def scan_public():
    """Read exactly the four configured research strategies using closed candles."""
    scans = []
    for item in STRATEGIES:
        # Fail closed on any provider anomaly; no stale/mock fallback.
        batch = await fetch_closed_candles(
            market="usdm_futures", symbol=item.symbol, interval=item.interval,
            limit=80)
        signal = evaluate(item.id, batch)
        candle = batch.candles[-1]
        scans.append({"id": item.id, "symbol": item.symbol,
                      "interval": item.interval, "signal": signal,
                      "close": str(candle.close),
                      "closed_ms": candle.close_time_ms,
                      "closed_candles_verified": True})
    return scans


def cli(argv=None):
    parser = argparse.ArgumentParser(description="Hunter M6: isolated research/Testnet no-order preflight")
    parser.add_argument("--action", choices=("status", "scan", "preflight"),
                        default="status")
    parser.add_argument("--config",
                        default="/etc/hunter-ksa1-execution/config.json")
    parser.add_argument("--safety-config",
                        default="/etc/hunter-ksa1-identity/public-api.env")
    args = parser.parse_args(argv)
    m5.validate_guards(Path(args.safety_config))
    config_path = Path(args.config)
    config = {}
    if config_path.exists():
        m5.private_file(config_path)
        config = legacy.load_json(config_path)
    if args.action == "status":
        report = {
            "status": "M6_PRIVATE_PREVIEW_READY",
            "config_blockers": config_readiness(config),
            "automatic_trading": False,
            "mainnet_orders": False,
            "testnet_order_writes": False,
            "four_strategies": sorted(STRATEGY_IDS),
            "risk_from_user_ui_attached_to_broker": False,
        }
    else:
        scans = asyncio.run(scan_public())
        if args.action == "scan":
            report = plan_candidates(scans, config)
        else:
            if config_readiness(config):
                report = plan_candidates(scans, config)
                report["status"] = "BLOCKED_TESTNET_PREFLIGHT_CONFIG_REQUIRED"
            else:
                # Testnet credentials never logged, sent to Mainnet or saved to disk.
                key, secret = m5.credentials()
                ex = legacy.Exchange("testnet", key, secret)
                try:
                    equity, _, _ = legacy.account_snapshot(ex, config["symbol"], config.get("leverage", 1), config.get("margin_mode"))
                    # Only symbol-specific filters; no inference across contracts.
                    filters = {}
                    for item in STRATEGIES:
                        if item.symbol == config["symbol"]:
                            step, min_qty, _, min_notional = legacy.symbol_filters(ex, item.symbol)
                            filters[item.symbol] = dict(step=step, minimum=min_qty,
                                                        min_notional=min_notional)
                    report = plan_candidates(scans, config, equity=equity,
                                             opening=None, filters=filters)
                    report["status"] = "M6_TESTNET_PREFLIGHT_READ_ONLY"
                    report["testnet_account_verified"] = True
                    report["daily_equity_baseline_persisted"] = False
                finally:
                    ex.close()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(cli())
    except (legacy.Halt, StrategyDataError, MarketDataUnavailable,
            ValueError, OSError) as e:
        # Never print API error bodies or key material.
        print("STATUS=BLOCKED_" + type(e).__name__, file=sys.stderr)
        sys.exit(2)
