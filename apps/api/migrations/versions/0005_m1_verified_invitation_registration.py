"""Admin-only, single-use invitations; immutable verified OIDC activation.

Runtime nex_app never receives direct user INSERT/UPDATE privileges.
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_verified_registration"
down_revision = "0004_m1_admin_directory_rls"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "registration_invitations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(), sa.ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(24), nullable=False, server_default="USER"),
        sa.Column("status", sa.String(24), nullable=False, server_default="PENDING"),
        sa.Column("issued_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("accepted_user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("role = 'USER'", name="registration_invite_role_check"),
        sa.CheckConstraint("status IN ('PENDING','ACCEPTED','REVOKED')", name="registration_invite_status_check"),
        sa.CheckConstraint("email=lower(btrim(email)) AND length(email)>3",
                           name="registration_invite_email_normalized_check"),
    )
    op.create_index("registration_pending_email_uq", "registration_invitations", ["email"],
                    unique=True, postgresql_where=sa.text("status='PENDING'"))
    op.create_index("registration_tenant_created_idx", "registration_invitations",
                    ["tenant_id", "created_at"])
    op.execute("ALTER TABLE registration_invitations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE registration_invitations FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY invite_admin_read ON registration_invitations FOR SELECT TO nex_app
        USING (tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid
          AND current_setting('app.role',true) IN ('ADMIN','SUPER_ADMIN'))
    """)
    op.execute("""
        CREATE POLICY invite_admin_insert ON registration_invitations FOR INSERT TO nex_app
        WITH CHECK (tenant_id=NULLIF(current_setting('app.tenant_id',true),'')::uuid
          AND current_setting('app.role',true) IN ('ADMIN','SUPER_ADMIN')
          AND role='USER' AND status='PENDING'
          AND issued_by::text=current_setting('app.user_id',true)
          AND expires_at>now() AND expires_at<=now()+interval '73 hours')
    """)
    op.execute("CREATE POLICY invite_migration_access ON registration_invitations TO nex_migrator USING (true) WITH CHECK (true)")
    op.execute("GRANT SELECT,INSERT ON registration_invitations TO nex_app")
    op.execute("REVOKE UPDATE,DELETE,TRUNCATE ON registration_invitations FROM nex_app")
    op.execute("""
    CREATE OR REPLACE FUNCTION claim_verified_invitation(
        p_issuer text, p_subject text, p_email text, p_email_verified boolean)
    RETURNS uuid
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = pg_catalog, public
    AS $$
    DECLARE
        v_inv public.registration_invitations%ROWTYPE;
        v_user_id uuid := gen_random_uuid();
    BEGIN
        IF p_email_verified IS DISTINCT FROM true
           OR p_issuer IS NULL OR length(p_issuer) NOT BETWEEN 5 AND 512
           OR p_subject IS NULL OR length(p_subject) NOT BETWEEN 1 AND 512
           OR p_email IS NULL OR length(p_email)>320 OR p_email<>lower(btrim(p_email))
           THEN RETURN NULL;
        END IF;
        IF EXISTS(SELECT 1 FROM public.users
                  WHERE issuer=p_issuer AND subject=p_subject)
           THEN RETURN NULL;
        END IF;
        SELECT * INTO v_inv
          FROM public.registration_invitations
          WHERE email=p_email AND status='PENDING' AND expires_at>clock_timestamp()
          FOR UPDATE;
        IF NOT FOUND THEN RETURN NULL; END IF;
        IF NOT EXISTS(SELECT 1 FROM public.tenants WHERE id=v_inv.tenant_id AND status='active')
           THEN RETURN NULL;
        END IF;
        -- Never upgrade to a privileged role, even if a malformed invitation was inserted.
        IF v_inv.role <> 'USER' THEN RETURN NULL; END IF;
        INSERT INTO public.users(id,issuer,subject,tenant_id,email,role,status)
        VALUES(v_user_id,p_issuer,p_subject,v_inv.tenant_id,p_email,'USER','active');
        UPDATE public.registration_invitations
          SET status='ACCEPTED', accepted_at=clock_timestamp(), accepted_user_id=v_user_id
          WHERE id=v_inv.id AND status='PENDING';
        INSERT INTO public.audit_events(
          id,tenant_id,correlation_id,actor_type,actor_id,
          action,object_type,object_id,outcome,metadata_json)
        VALUES(gen_random_uuid(),v_inv.tenant_id,gen_random_uuid(),'SYSTEM',NULL,
          'ACCOUNT_INVITATION_ACCEPTED','USER',v_user_id::text,'SUCCESS','{}'::jsonb);
        RETURN v_user_id;
    END; $$;
    """)
    op.execute("REVOKE ALL ON FUNCTION claim_verified_invitation(text,text,text,boolean) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION claim_verified_invitation(text,text,text,boolean) TO nex_app")
    op.execute("COMMENT ON FUNCTION claim_verified_invitation(text,text,text,boolean) IS 'Call only after OIDC ID token signature, issuer, audience, nonce and email_verified have been validated. No direct public endpoint.'")

def downgrade():
    raise RuntimeError("Refused: downgrade would destroy account registration evidence.")
