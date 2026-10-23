"""Self-registration: verified OIDC identity, private tenant, USER role only."""
from alembic import op
revision = '0006_verified_self_signup'
down_revision = '0005_verified_registration'
branch_labels = None
depends_on = None

def upgrade():
    op.execute('''
    CREATE FUNCTION public.claim_verified_self_signup(p_issuer text, p_subject text,
            p_email text, p_email_verified boolean) RETURNS uuid
    LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
    DECLARE v_user uuid := gen_random_uuid(); v_tenant uuid := gen_random_uuid();
    BEGIN
      IF p_email_verified IS DISTINCT FROM true OR
         p_issuer IS NULL OR length(p_issuer) NOT BETWEEN 5 AND 512 OR
         p_subject IS NULL OR length(p_subject) NOT BETWEEN 1 AND 512 OR
         p_email IS NULL OR length(p_email) NOT BETWEEN 5 AND 254 OR
         p_email<>lower(btrim(p_email)) OR
         p_email !~ '^[a-z0-9][a-z0-9.!#$%&*+/=?^_`{|}~-]*@[a-z0-9][a-z0-9.-]+$'
      THEN RETURN NULL; END IF;
      -- Do not bind one email to two different OIDC subjects or tenants.
      PERFORM pg_advisory_xact_lock(hashtextextended(p_email, 7126));
      IF EXISTS(SELECT 1 FROM public.users WHERE email=p_email OR
                 (issuer=p_issuer AND subject=p_subject)) THEN RETURN NULL; END IF;
      INSERT INTO public.tenants(id,name,status)
        VALUES (v_tenant,'Hunter personal account','active');
      INSERT INTO public.users(id,tenant_id,email,role,status,issuer,subject)
        VALUES(v_user,v_tenant,p_email,'USER','active',p_issuer,p_subject);
      INSERT INTO public.audit_events(id,tenant_id,correlation_id,actor_type,actor_id,
         action,object_type,object_id,outcome,metadata_json)
        VALUES(gen_random_uuid(),v_tenant,gen_random_uuid(),'SYSTEM',NULL,
         'VERIFIED_SELF_REGISTRATION','USER',v_user::text,'SUCCESS','{}'::jsonb);
      RETURN v_user;
    END $$;
    ''')
    op.execute('REVOKE ALL ON FUNCTION public.claim_verified_self_signup(text,text,text,boolean) FROM PUBLIC')
    op.execute('GRANT EXECUTE ON FUNCTION public.claim_verified_self_signup(text,text,text,boolean) TO nex_app')

def downgrade():
    raise RuntimeError('Do not silently disable previously registered accounts.')
