-- M2-B L6: test-only issuer-side durable two-phase journal.
-- Disposable localhost PostgreSQL 16 'nex_m2b_preview', never an NDSP migration.
-- Unsigned reservations are NOT exportable; a source-owned validated signature
-- must be appended after reservation. No production authentication is provided.
CREATE SCHEMA m2b_l6_preview;
REVOKE ALL ON SCHEMA m2b_l6_preview FROM PUBLIC;
GRANT USAGE ON SCHEMA m2b_l6_preview TO m2b_l6_preview_app;

CREATE TABLE m2b_l6_preview.source_revisions (
    tenant_id uuid NOT NULL CHECK (
        tenant_id <> '00000000-0000-0000-0000-000000000000'
    ),
    source_decision_id text NOT NULL CHECK (
        source_decision_id ~ '^CD-[A-Z0-9-]{5,64}$'
    ),
    decision_version bigint NOT NULL CHECK (decision_version >= 1),
    operation_id uuid NOT NULL,
    source_snapshot jsonb NOT NULL CHECK (jsonb_typeof(source_snapshot)='object'),
    source_fingerprint text NOT NULL CHECK (
        source_fingerprint ~ '^sha256:[a-f0-9]{64}$'
    ),
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant_id,source_decision_id,decision_version),
    CONSTRAINT l6_operation_unique UNIQUE (tenant_id,operation_id)
);

CREATE TABLE m2b_l6_preview.sealed_artifacts (
    tenant_id uuid NOT NULL,
    source_decision_id text NOT NULL,
    decision_version bigint NOT NULL,
    signed_bytes bytea NOT NULL CHECK (octet_length(signed_bytes) BETWEEN 100 AND 16384),
    signed_hash text NOT NULL CHECK (signed_hash ~ '^sha256:[a-f0-9]{64}$'),
    key_id text NOT NULL CHECK (key_id ~ '^[A-Za-z0-9_.-]{1,80}$'),
    expires_at timestamptz NOT NULL,
    sealed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant_id,source_decision_id,decision_version),
    FOREIGN KEY (tenant_id,source_decision_id,decision_version)
       REFERENCES m2b_l6_preview.source_revisions
       (tenant_id,source_decision_id,decision_version)
);

REVOKE ALL ON ALL TABLES IN SCHEMA m2b_l6_preview FROM PUBLIC;
GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA m2b_l6_preview TO m2b_l6_preview_app;
REVOKE UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA m2b_l6_preview
    FROM m2b_l6_preview_app;
ALTER TABLE m2b_l6_preview.source_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE m2b_l6_preview.source_revisions FORCE ROW LEVEL SECURITY;
ALTER TABLE m2b_l6_preview.sealed_artifacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE m2b_l6_preview.sealed_artifacts FORCE ROW LEVEL SECURITY;

CREATE POLICY l6_revision_read ON m2b_l6_preview.source_revisions FOR SELECT
TO m2b_l6_preview_app
USING (tenant_id = NULLIF(current_setting('m2b_l6.tenant_id',true),'')::uuid);
CREATE POLICY l6_revision_append ON m2b_l6_preview.source_revisions FOR INSERT
TO m2b_l6_preview_app
WITH CHECK (tenant_id = NULLIF(current_setting('m2b_l6.tenant_id',true),'')::uuid);
CREATE POLICY l6_artifact_read ON m2b_l6_preview.sealed_artifacts FOR SELECT
TO m2b_l6_preview_app
USING (tenant_id = NULLIF(current_setting('m2b_l6.tenant_id',true),'')::uuid);
CREATE POLICY l6_artifact_append ON m2b_l6_preview.sealed_artifacts FOR INSERT
TO m2b_l6_preview_app
WITH CHECK (tenant_id = NULLIF(current_setting('m2b_l6.tenant_id',true),'')::uuid);

CREATE FUNCTION m2b_l6_preview.reject_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
 RAISE EXCEPTION 'M2B_L6_APPEND_ONLY';
END;
$$;
CREATE TRIGGER l6_revisions_immutable BEFORE UPDATE OR DELETE
ON m2b_l6_preview.source_revisions FOR EACH ROW
EXECUTE FUNCTION m2b_l6_preview.reject_change();
CREATE TRIGGER l6_sealed_immutable BEFORE UPDATE OR DELETE
ON m2b_l6_preview.sealed_artifacts FOR EACH ROW
EXECUTE FUNCTION m2b_l6_preview.reject_change();
