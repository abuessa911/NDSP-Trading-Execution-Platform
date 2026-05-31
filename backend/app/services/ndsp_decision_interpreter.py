from __future__ import annotations

from typing import Any


def _decision_root(payload: dict[str, Any]) -> dict[str, Any]:
    decision = payload.get("decision")
    if isinstance(decision, dict):
        return decision

    ndsp_decision = payload.get("ndsp_decision")
    if isinstance(ndsp_decision, dict):
        nested = ndsp_decision.get("decision")
        if isinstance(nested, dict):
            return nested
        return ndsp_decision

    return {}


def _nested(payload: dict[str, Any], *path: str) -> Any:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _as_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "y", "allowed"}:
            return True
        if v in {"false", "0", "no", "n", "blocked", "denied"}:
            return False
    return None


def _as_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _no_trade(source_direction: Any, confidence: float | None, reason: str) -> dict[str, Any]:
    return {
        "executable": False,
        "action": "NO_TRADE",
        "source_direction": source_direction,
        "confidence": confidence,
        "reason": reason,
        "ndsp_decision_support": True,
    }


def interpret_ndsp_payload(payload: dict, min_confidence: int = 80) -> dict:
    if not isinstance(payload, dict):
        return _no_trade(None, None, "Invalid payload")

    decision = _decision_root(payload)
    legacy_side = payload.get("side")

    source_direction = decision.get("direction")
    confidence = _as_number(decision.get("confidence"))
    if confidence is None:
        confidence = _as_number(payload.get("confidence"))

    if legacy_side:
        action = str(legacy_side).strip().upper()
        source_direction = source_direction or action
        if action not in {"BUY", "SELL"}:
            return _no_trade(source_direction, confidence, "Invalid legacy side")
    else:
        direction = str(source_direction or "").strip().lower()
        if direction == "bullish":
            action = "BUY"
        elif direction == "bearish":
            action = "SELL"
        elif direction == "neutral":
            return _no_trade(source_direction, confidence, "NDSP direction is neutral")
        else:
            return _no_trade(source_direction, confidence, "Missing or unsupported NDSP decision.direction")

    decision_allowed = _as_bool(decision.get("execution_allowed"))
    if decision_allowed is False:
        return _no_trade(source_direction, confidence, "decision.execution_allowed is false")

    execution_allowed = _as_bool(_nested(payload, "execution", "allowed"))
    if execution_allowed is False:
        return _no_trade(source_direction, confidence, "execution.allowed is false")

    execution_mode = _nested(payload, "execution", "mode")
    if execution_mode and str(execution_mode).strip() != "decision_support_only":
        return _no_trade(source_direction, confidence, "execution.mode is not decision_support_only")

    if confidence is None and not legacy_side:
        return _no_trade(source_direction, confidence, "Missing confidence")

    if confidence is not None and confidence < min_confidence:
        return _no_trade(source_direction, confidence, f"Confidence below {min_confidence}")

    risk_state = _nested(payload, "states", "risk_state")
    if risk_state and str(risk_state).strip().lower() != "normal":
        return _no_trade(source_direction, confidence, "states.risk_state is not normal")

    system_state = _nested(payload, "states", "system_state")
    if system_state and str(system_state).strip().lower() == "safe_mode":
        return _no_trade(source_direction, confidence, "states.system_state is safe_mode")

    market_signal = _nested(payload, "market_alignment", "signal")
    if str(market_signal or "").strip().upper() == "NO_SIGNAL":
        return _no_trade(source_direction, confidence, "market_alignment.signal is NO_SIGNAL")

    quality_label = decision.get("quality_label")
    if str(quality_label or "").strip().lower() == "structurally invalid":
        return _no_trade(source_direction, confidence, "decision.quality_label is Structurally Invalid")

    return {
        "executable": True,
        "action": action,
        "source_direction": source_direction,
        "confidence": confidence,
        "reason": "NDSP decision-support payload accepted",
        "ndsp_decision_support": True,
    }
