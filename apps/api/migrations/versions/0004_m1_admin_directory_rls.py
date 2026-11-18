"""Only server-authorized administrators can list users from their own tenant.

Preserve issuer+subject identity access, immutable audit and all restrictions
on changing or deleting user records.
"""
from alembic import op

revision = "0004_m1_admin_directory_rls"
down_revision = "0003_m1_admin_audit_rls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE POLICY admin_tenant_user_list ON users FOR SELECT TO nex_app USING (
            tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
            AND current_setting('app.role', true) IN ('ADMIN', 'SUPER_ADMIN')
        )
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS admin_tenant_user_list ON users")
