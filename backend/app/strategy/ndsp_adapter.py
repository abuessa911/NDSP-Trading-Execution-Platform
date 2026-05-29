from dataclasses import dataclass


@dataclass
class NDSPSignal:
    action: str
    symbol: str
    notional_usdt: float
    reason: str


def get_ndsp_signal(symbol: str) -> NDSPSignal:
    """
    هنا يتم ربط طبقات NDSP لاحقًا.

    النسخة الآمنة الحالية ترجع HOLD دائمًا حتى لا يتم تنفيذ صفقات
    بدون منطقك الحقيقي.
    """
    return NDSPSignal(
        action="HOLD",
        symbol=symbol,
        notional_usdt=0,
        reason="NDSP adapter placeholder returned HOLD",
    )
