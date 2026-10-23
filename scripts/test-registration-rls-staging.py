"""Isolated PostgreSQL RLS and single-use verified invite smoke tests."""
import asyncio,secrets
from datetime import UTC,datetime,timedelta
from pathlib import Path
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

settings={}
for row in Path("/etc/hunter-ksa1-backend/db-connections.env").read_text().splitlines():
    key,sep,value=row.partition("=")
    if sep:settings[key]=value

async def main():
    migrant=create_async_engine(settings["MIGRATION_DATABASE_URL"])
    app=create_async_engine(settings["DATABASE_URL"])
    email="verify."+secrets.token_hex(7)+"@nex.example.test"
    try:
        async with migrant.connect() as c:
            adm=(await c.execute(text("SELECT id,tenant_id,issuer,subject FROM users WHERE role='ADMIN' ORDER BY created_at LIMIT 1"))).first()
            if not adm:raise RuntimeError("TEST_ADMIN_NOT_PROVISIONED")
            admin_id,tenant_id,issuer,subject=adm
        async with app.begin() as c:
            for key,val in [("app.issuer",issuer),("app.subject",subject),("app.user_id",str(admin_id)),("app.tenant_id",str(tenant_id)),("app.role","ADMIN")]:
                await c.execute(text("SELECT set_config(:key,:value,true)"),{"key":key,"value":val})
            inv_id=uuid4()
            await c.execute(text("""
                INSERT INTO registration_invitations(id,tenant_id,email,role,status,issued_by,expires_at)
                VALUES(:id,:tenant,:email,'USER','PENDING',:issued, :expiry)
            """),{"id":inv_id,"tenant":tenant_id,"email":email,"issued":admin_id,
                  "expiry":datetime.now(UTC)+timedelta(hours=72)})
            count=(await c.execute(text("SELECT count(*) FROM registration_invitations WHERE id=:id"),{"id":inv_id})).scalar()
            if count!=1:raise RuntimeError("ADMIN_RLS_CANNOT_READ_OWN_INVITE")
        print("ADMIN_INVITATION_INSERT_READ_PASS")
        async with app.begin() as c:
            not_verified=(await c.execute(text("SELECT claim_verified_invitation(:i,:s,:e,false)"),{
                "i":issuer,"s":"test-"+secrets.token_hex(16),"e":email})).scalar()
            if not_verified is not None:raise RuntimeError("UNVERIFIED_EMAIL_ALLOWED")
        print("UNVERIFIED_EMAIL_FAILS_CLOSED_PASS")
        synthetic_subject="m1-invite-"+secrets.token_hex(16)
        async with app.begin() as c:
            activated=(await c.execute(text("SELECT claim_verified_invitation(:i,:s,:e,true)"),{
                "i":issuer,"s":synthetic_subject,"e":email})).scalar()
            if activated is None:raise RuntimeError("VERIFIED_INVITE_NOT_ACCEPTED")
            again=(await c.execute(text("SELECT claim_verified_invitation(:i,:s,:e,true)"),{
                "i":issuer,"s":"a-different-subject","e":email})).scalar()
            if again is not None:raise RuntimeError("INVITATION_REPLAY_ALLOWED")
        async with migrant.connect() as c:
            actual=(await c.execute(text("SELECT role,status FROM users WHERE id=:uid"),{"uid":activated})).first()
            status=(await c.execute(text("SELECT status FROM registration_invitations WHERE id=:id"),{"id":inv_id})).scalar()
            audit=(await c.execute(text("SELECT count(*) FROM audit_events WHERE action='ACCOUNT_INVITATION_ACCEPTED' AND object_id=:id"),{"id":str(activated)})).scalar()
            if actual!=("USER","active") or status!="ACCEPTED" or audit!=1:
                raise RuntimeError("INVITE_ACTIVATION_AUDIT_INVARIANT_FAILED")
        print("VERIFIED_INVITATION_SINGLE_USE_AND_AUDIT_PASS")
    finally:
        await app.dispose()
        await migrant.dispose()

asyncio.run(main())
