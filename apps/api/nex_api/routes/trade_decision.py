"""Authenticated cross-strategy/read-only equity projection.

No POST, no broker, no automated orders, no NDSP trust assumption.
"""
from __future__ import annotations
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from nex_api.dependencies import get_provisioned_user
from nex_api.models import User
from nex_api.routes.risk_equity import get_risk_view
from nex_api.routes.strategy_scanner import get_strategies
from nex_api.strategy_risk_decision import decide

router = APIRouter(prefix="/api/v1/trading/execution", tags=["hunter decision gate"],
                   include_in_schema=False)

@router.get("/review")
async def execution_review(request: Request,
       user: Annotated[User, Depends(get_provisioned_user)]):
    # Risk failures propagate as 503/401, never become permission.
    snapshot = await get_risk_view(request, user)
    strategies = await get_strategies(request, user)
    return decide(strategies.strategies, snapshot)
