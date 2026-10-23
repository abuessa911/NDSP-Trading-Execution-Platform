"""Background DEMO worker. Starts only accounts with an explicit one-hour lease."""
from __future__ import annotations

import asyncio
import logging
from types import SimpleNamespace
from uuid import UUID

from sqlalchemy import select, text

from nex_api import hunter_live_executor as engine
from nex_api.models import Tenant, User
from nex_api.routes.testnet_execution import credentials, service, threaded
from nex_api.routes.trading_control import connection_key, redis_store

log = logging.getLogger("hunter.testnet_automation")


async def owner_allowed(app, authority):
    """Recheck DB role/status under the original owner's RLS context."""
    factory = app.state.session_factory
    if factory is None:
        raise engine.Halt("TESTNET_AUTHORIZATION_UNAVAILABLE")
    tenant_id, user_id = map(UUID, authority["scope"].split(":"))
    async with factory() as session:
        postgres = session.get_bind().dialect.name == "postgresql"
        if postgres:
            await session.execute(text(
                "SELECT set_config('app.issuer', :issuer, true), "
                "set_config('app.subject', :subject, true)"),
                {"issuer": authority["issuer"], "subject": authority["subject"]})
        user = (await session.execute(select(User).where(
            User.id == user_id, User.tenant_id == tenant_id,
            User.issuer == authority["issuer"], User.subject == authority["subject"]
        ))).scalar_one_or_none()
        if user is None:
            return False
        if postgres:
            await session.execute(text(
                "SELECT set_config('app.user_id', :uid, true), "
                "set_config('app.tenant_id', :tenant, true), "
                "set_config('app.role', :role, true)"),
                {"uid": str(user.id), "tenant": str(user.tenant_id), "role": user.role})
        tenant = await session.get(Tenant, tenant_id)
        return (user.status == "active" and user.role in {"OPERATOR", "ADMIN", "SUPER_ADMIN"}
                and tenant is not None and tenant.status == "active")


async def tick(app, authority):
    request = SimpleNamespace(app=app)
    allowed = await owner_allowed(app, authority)
    tenant, subject = map(UUID, authority["scope"].split(":"))
    user = SimpleNamespace(tenant_id=tenant, id=subject)
    with service(request).session(authority["scope"]) as account:
        if account.automation()["state"] not in {"RUNNING", "STOPPING"}:
            return account.automation()
        try:
            key, secret = await credentials(request, user)
            ttl = await redis_store(request).ttl(connection_key(user))
        except Exception:
            return account.pause_automation("TESTNET_CREDENTIALS_UNAVAILABLE")
        return await threaded(account.automation_cycle, key, secret,
                              credentials_ttl=ttl, owner_allowed=allowed)


async def cycle(app):
    service_instance = app.state.testnet_execution
    accounts = await asyncio.to_thread(service_instance.automation_accounts)
    for authority in accounts:
        try:
            await tick(app, authority)
        except asyncio.CancelledError:
            raise
        except engine.Halt as error:
            if str(error) == "TESTNET_OPERATION_IN_PROGRESS":
                continue
            with service_instance.session(authority["scope"]) as account:
                account.pause_automation("TESTNET_AUTHORIZATION_UNAVAILABLE")
        except Exception:
            # Never log a signed URL, exception body, credentials or scope.
            log.warning("testnet_automation_cycle_unavailable")
            try:
                with service_instance.session(authority["scope"]) as account:
                    account.pause_automation("TESTNET_AUTOMATION_CHECK_FAILED")
            except engine.Halt:
                pass


async def worker(app):
    while True:
        try:
            await cycle(app)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.warning("testnet_automation_worker_unavailable")
        await asyncio.sleep(30)
