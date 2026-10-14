-- M2-B L2: disposable synthetic-only PostgreSQL proof. NEVER a migration.
-- Permitted only in a fresh localhost database "nex_m2b_preview" via gated test.
-- APP ROLE MUST NOT BE USED FOR PRODUCTION TENANT SECURITY.
CREATE SCHEMA m2b_l2_preview;
REVOKE ALL ON SCHEMA m2b_l2_preview FROM PUBLIC;
GRANT USAGE ON SCHEMA m2b_l2_preview TO m2b_l2_preview_app;

CREATE TABLE m2b_l2_preview.decision_bindings (
    binding_id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL CHECK (tenant_id <> '00000000-0000-0000-0000-000000000000'),
    issuer_id text NOT NULL CHECK (issuer_id ~ '^[a-z0-9-]{1,80}$'),
    source_environment text NOT NULL CHECK (source_environment = 'test'),
    source_decision_id text NOT NULL CHECK (source_decision_id ~ '^CD-[A-Z0-9-]{5,64}$'),
    signed_decision_id uuid NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT m2b_l2_unique_source UNIQUE (
        tenant_id, issuer_id, source_environment, source_decision_id
    ),
    CONSTRAINT m2b_l2_binding_tenant UNIQUE (binding_id, tenant_id)
);

CREATE TABLE m2b_l2_preview.decision_versions (
    binding_id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    decision_version bigint NOT NULL CHECK (decision_version > 0),
    evidence_hash text NOT NULL CHECK (evidence_hash ~ '^sha256:[a-f0-9]{64}$'),
    canonical_payload_hash text NOT NULL CHECK (canonical_payload_hash ~ '^sha256:[a-f0-9]{64}$'),
    signature_hash text NOT NULL CHECK (signature_hash ~ '^sha256:[a-f0-9]{64}$'),
    key_id text NOT NULL CHECK (key_id ~ '^[A-Za-z0-9_.-]{1,80}$'),
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (binding_id, decision_version),
    CONSTRAINT m2b_l2_version_parent FOREIGN KEY (binding_id, tenant_id)
        REFERENCES m2b_l2_preview.decision_bindings(binding_id, tenant_id)
);

REVOKE ALL ON ALL TABLES IN SCHEMA m2b_l2_preview FROM PUBLIC;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA m2b_l2_preview TO m2b_l2_preview_app;
REVOKE UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA m2b_l2_preview
    FROM m2b_l2_preview_app;

ALTER TABLE m2b_l2_preview.decision_bindings ENABLE ROW LEVEL SECURITY;
ALTER TABLE m2b_l2_preview.decision_bindings FORCE ROW LEVEL SECURITY;
ALTER TABLE m2b_l2_preview.decision_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE m2b_l2_preview.decision_versions FORCE ROW LEVEL SECURITY;

CREATE POLICY l2_binding_read ON m2b_l2_preview.decision_bindings
    FOR SELECT TO m2b_l2_preview_app
    USING (tenant_id = NULLIF(current_setting('m2b_l2.tenant_id', true), '')::uuid);
CREATE POLICY l2_binding_insert ON m2b_l2_preview.decision_bindings
    FOR INSERT TO m2b_l2_preview_app
    WITH CHECK (tenant_id = NULLIF(current_setting('m2b_l2.tenant_id', true), '')::uuid);
CREATE POLICY l2_version_read ON m2b_l2_preview.decision_versions
    FOR SELECT TO m2b_l2_preview_app
    USING (tenant_id = NULLIF(current_setting('m2b_l2.tenant_id', true), '')::uuid);
CREATE POLICY l2_version_insert ON m2b_l2_preview.decision_versions
    FOR INSERT TO m2b_l2_preview_app
    WITH CHECK (tenant_id = NULLIF(current_setting('m2b_l2.tenant_id', true), '')::uuid);

CREATE FUNCTION m2b_l2_preview.reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'M2B_L2_APPEND_ONLY';
END;
$$;
CREATE TRIGGER l2_binding_immutable BEFORE UPDATE OR DELETE
    ON m2b_l2_preview.decision_bindings
    FOR EACH ROW EXECUTE FUNCTION m2b_l2_preview.reject_mutation();
CREATE TRIGGER l2_version_immutable BEFORE UPDATE OR DELETE
    ON m2b_l2_preview.decision_versions
    FOR EACH ROW EXECUTE FUNCTION m2b_l2_preview.reject_mutation();
