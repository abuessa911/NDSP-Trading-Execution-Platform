"""Fail-closed Testnet leverage/margin planning. NO ORDER EXECUTION."""
from decimal import Decimal, InvalidOperation, ROUND_DOWN

class RiskRejected(ValueError): pass

def dec(value):
    try:
        v=Decimal(str(value))
        if not v.is_finite(): raise RiskRejected("NON_FINITE")
        return v
    except (InvalidOperation, TypeError, ValueError):
        raise RiskRejected("INVALID_NUMBER") from None

def plan(*, equity, opening_equity, margin_used, leverage, entry_price,
         stop_margin_pct, daily_loss_pct, trade_risk_pct, max_margin_pct,
         fee_rate_each_side, slippage_rate_each_side, funding_buffer_rate=0,
         maintenance_margin_rate=None):
    e,o,used,L,p=map(dec,(equity,opening_equity,margin_used,leverage,entry_price))
    stop,daily,trade,cap=map(dec,(stop_margin_pct,daily_loss_pct,trade_risk_pct,max_margin_pct))
    fee,slip,funding=map(dec,(fee_rate_each_side,slippage_rate_each_side,funding_buffer_rate))
    if min(e,o,p,L)>0 and used>=0 and L==L.to_integral_value() and L<=125: pass
    else: raise RiskRejected("INVALID_ACCOUNT_OR_LEVERAGE")
    if not all(Decimal("0")<x<=Decimal("100") for x in (stop,daily,trade,cap)):
        raise RiskRejected("INVALID_PERCENT")
    if min(fee,slip,funding)<0 or max(fee,slip,funding)>Decimal("0.1"):
        raise RiskRejected("INVALID_COST_BUFFER")
    if maintenance_margin_rate is None:
        raise RiskRejected("EXCHANGE_MAINTENANCE_RATE_REQUIRED")
    mm=dec(maintenance_margin_rate)
    if mm<0 or mm>=Decimal("1")/L:
        raise RiskRejected("LIQUIDATION_BUFFER_UNSAFE")
    remaining_daily=o*daily/100-max(Decimal("0"),o-e)
    if remaining_daily<=0: raise RiskRejected("DAILY_LOSS_LIMIT_REACHED")
    available_margin=e*cap/100-used
    if available_margin<=0: raise RiskRejected("MARGIN_CAP_REACHED")
    # 70% margin loss -> price movement 0.70 / leverage before costs.
    stop_move=stop/(100*L)
    # Require stop before a conservative isolated-margin liquidation approximation.
    liquidation_move=Decimal("1")/L-mm
    if stop_move>=liquidation_move*Decimal("0.85"):
        raise RiskRejected("STOP_TOO_CLOSE_TO_LIQUIDATION")
    cost_per_notional=2*(fee+slip)+funding
    loss_per_margin=stop/100+L*cost_per_notional
    risk_budget=min(e*trade/100,remaining_daily)
    margin=min(available_margin,risk_budget/loss_per_margin)
    if margin<=0: raise RiskRejected("NO_CAPACITY")
    notional=margin*L
    qty=notional/p
    stop_price=p*(1-stop_move)
    return {"leverage":str(L),"margin":str(margin),"notional":str(notional),
            "quantity_unrounded":str(qty),"long_stop_price_unrounded":str(stop_price),
            "estimated_loss_including_costs":str(margin*loss_per_margin),
            "daily_remaining_before_order":str(remaining_daily),
            "note":"RESEARCH_ONLY; exchange filters, position risk, liquidation and fees require live verification"}
