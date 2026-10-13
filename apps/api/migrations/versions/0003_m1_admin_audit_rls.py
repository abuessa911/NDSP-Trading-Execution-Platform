"""Allow MFA administrators to read ONLY their tenant's immutable audit records.

The API independently enforces administrator role, fresh provider MFA and
opaque session validation. No write, delete or truncate privileges are changed.
"""
from alembic import op

revision = "0003_m1_admin_audit_rls"
down_revision = "0002_m1_remediation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER POLICY audit_read ON audit_events USING (
            tenant_id = NULLIF(current_setting('app.tenant_id',true),'')::uuid
            AND tenant_id <> '00000000-0000-0000-0000-000000000001'::uuid
            AND current_setting('app.role',true)
                IN ('OPERATOR','ADMIN','SUPER_ADMIN')
        )
    """)


def downgrade() -> None:
    # Revert only this read policy; preserve all original audit evidence.
    op.execute("""
        ALTER POLICY audit_read ON audit_events USING (
            tenant_id = NULLIF(current_setting('app.tenant_id',true),'')::uuid
            AND tenant_id <> '00000000-0000-0000-0000-000000000001'::uuid
            AND current_setting('app.role',true) = 'OPERATOR'
        )
    """)
