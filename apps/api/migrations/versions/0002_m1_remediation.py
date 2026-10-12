"""Direct tenancy and Appendix B audit; preserve legacy evidence, refuse guessed identities."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_m1_remediation"
down_revision = "0001_m1_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    if connection.execute(sa.text("SELECT count(*) FROM users")).scalar():
        raise RuntimeError(
            "M1 upgrade stopped: existing identities require explicitly approved "
            "tenant/email/role mappings. No identity or evidence was changed."
        )
    # No reinterpretation of historical payloads or inventing missing audit fields.
    op.rename_table("audit_events", "audit_events_legacy")
    op.execute("ALTER INDEX audit_events_pkey RENAME TO audit_events_legacy_pkey")
    op.execute("ALTER INDEX audit_events_tenant_created_idx RENAME TO audit_legacy_tenant_idx")
    op.execute("ALTER INDEX audit_events_actor_created_idx RENAME TO audit_legacy_actor_idx")
    op.execute("REVOKE ALL ON audit_events_legacy FROM nex_app")
    # Empty identity projection: no mappings are inferred from membership labels.
    op.drop_table("tenant_memberships")
    for column in (
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("status", sa.String(24), nullable=False, server_default="active"),
    ):
        op.add_column("users", column)
    op.create_check_constraint("users_role_check", "users",
                               "role IN ('USER','OPERATOR','ADMIN','SUPER_ADMIN')")
    op.create_check_constraint("users_status_check", "users", "status IN ('active','disabled')")
    op.create_check_constraint("users_email_check", "users",
                               "length(email) > 3 AND position('@' in email) > 1")
    # Immutable migration snapshot: future ORM changes must not rewrite history.
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"),
                  nullable=False),
        sa.Column("correlation_id", sa.Uuid(), nullable=False),
        sa.Column("actor_type", sa.String(24), nullable=False),
        sa.Column("actor_id", sa.String(512)),
        sa.Column("action", sa.String(96), nullable=False),
        sa.Column("object_type", sa.String(96), nullable=False),
        sa.Column("object_id", sa.String(512)),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("reason_code", sa.String(96)),
        sa.Column("source_ip_hash", sa.String(64)),
        sa.Column("user_agent_hash", sa.String(64)),
        sa.Column("before_hash", sa.String(64)),
        sa.Column("after_hash", sa.String(64)),
        sa.Column("metadata_json", JSONB(), nullable=False,
                  server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint("actor_type IN ('USER','ADMIN','SYSTEM','SERVICE')",
                           name="audit_actor_type_check"),
        sa.CheckConstraint("outcome IN ('SUCCESS','DENIED','FAILED')",
                           name="audit_outcome_check"),
    )
    op.create_index("audit_events_tenant_created_idx", "audit_events", ["tenant_id", "created_at"])
    op.create_index("audit_events_actor_created_idx", "audit_events", ["actor_id", "created_at"])
    op.execute("""
        INSERT INTO tenants(id,name,status)
        VALUES ('00000000-0000-0000-0000-000000000001','NEX security evidence','disabled')
    """)
    # This reserved tenant is not a user tenant. Unattributed pre-auth failures
    # are stored here; runtime tenant audit cannot read it.
    for table in ("tenants", "users", "audit_events"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY user_identity ON users FOR SELECT TO nex_app USING (
            issuer = current_setting('app.issuer',true)
            AND subject = current_setting('app.subject',true)
        )
    """)
    op.execute("""
        CREATE POLICY tenant_context ON tenants FOR SELECT TO nex_app USING (
            id = NULLIF(current_setting('app.tenant_id',true),'')::uuid
        )
    """)
    op.execute("""
        CREATE POLICY audit_read ON audit_events FOR SELECT TO nex_app USING (
            tenant_id = NULLIF(current_setting('app.tenant_id',true),'')::uuid
            AND tenant_id <> '00000000-0000-0000-0000-000000000001'::uuid
            AND current_setting('app.role',true) = 'OPERATOR'
        )
    """)
    op.execute("""
        CREATE POLICY audit_insert ON audit_events FOR INSERT TO nex_app WITH CHECK (
            tenant_id = NULLIF(current_setting('app.tenant_id',true),'')::uuid
        )
    """)
    # Migration owner can provision and maintain identities, but cannot mutate evidence.
    for table in ("tenants", "users", "audit_events"):
        op.execute(f"CREATE POLICY migration_access ON {table} TO nex_migrator "
                   "USING (true) WITH CHECK (true)")
    op.execute("""
        CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION reject_audit_event_mutation()
    """)
    op.execute("""
        CREATE FUNCTION reject_audit_truncate() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN RAISE EXCEPTION 'audit evidence cannot be truncated'; END; $$
    """)
    for table in ("audit_events", "audit_events_legacy"):
        op.execute(f"CREATE TRIGGER audit_no_truncate BEFORE TRUNCATE ON {table} "
                   "FOR EACH STATEMENT EXECUTE FUNCTION reject_audit_truncate()")
    op.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC, nex_app")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM nex_app")
    op.execute("GRANT SELECT ON users, tenants, alembic_version TO nex_app")
    op.execute("GRANT SELECT, INSERT ON audit_events TO nex_app")


def downgrade() -> None:
    raise RuntimeError("Refused: downgrade would destroy Appendix B audit evidence.")