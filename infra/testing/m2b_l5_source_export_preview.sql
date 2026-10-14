-- M2-B L5 isolated, disposable PostgreSQL-only source issuance receipt proof.
-- NOT an Alembic migration, NDSP CDS migration, or production auth gateway.
-- Requires a FRESH, localhost-only nex_m2b_preview CI database + fixture role.
CREATE SCHEMA m2b_l5_preview;
REVOKE ALL ON SCHEMA m2b_l5_preview FROM PUBLIC;
GRANT USAGE ON SCHEMA m2b_l5_preview TO m2b_l5_preview_app;

CREATE TABLE m2b_l5_preview.source_issuance_events (
    tenant_id uuid NOT NULL
      CHECK (tenant_id <> '00000000-0000-0000-0000-000000000000'),
    source_decision_id text NOT NULL
      CHECK (source_decision_id ~ '^CD-[A-Z0-9-]{5,64}$'),
    decision_version bigint NOT NULL CHECK (decision_version >= 1),
    issuer_id text NOT NULL CHECK (issuer_id = 'ndsp-l5-synthetic-only'),
    source_environment text NOT NULL CHECK (source_environment = 'test'),
    decision_state text NOT NULL CHECK (decision_state = 'Published'),
    visibility text NOT NULL CHECK (visibility = 'public'),
    published_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL CHECK (expires_at > published_at),
    signed_bytes bytea NOT NULL CHECK (octet_length(signed_bytes) BETWEEN 100 AND 16384),
    evidence_hash text NOT NULL CHECK (evidence_hash ~ '^sha256:[a-f0-9]{64}$'),
    signed_payload_hash text NOT NULL CHECK (signed_payload_hash ~ '^sha256:[a-f0-9]{64}$'),
    key_id text NOT NULL CHECK (key_id ~ '^[A-Za-z0-9_.-]{1,80}$'),
    appended_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant_id, source_decision_id, decision_version)
);

REVOKE ALL ON m2b_l5_preview.source_issuance_events FROM PUBLIC;
GRANT SELECT, INSERT ON m2b_l5_preview.source_issuance_events
    TO m2b_l5_preview_app;
REVOKE UPDATE, DELETE, TRUNCATE ON m2b_l5_preview.source_issuance_events
    FROM m2b_l5_preview_app;

ALTER TABLE m2b_l5_preview.source_issuance_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE m2b_l5_preview.source_issuance_events FORCE ROW LEVEL SECURITY;

CREATE POLICY m2b_l5_tenant_select
    ON m2b_l5_preview.source_issuance_events FOR SELECT
    TO m2b_l5_preview_app
    USING (tenant_id = NULLIF(current_setting('m2b_l5.tenant_id', true), '')::uuid);

CREATE POLICY m2b_l5_tenant_append
    ON m2b_l5_preview.source_issuance_events FOR INSERT
    TO m2b_l5_preview_app
    WITH CHECK (tenant_id = NULLIF(current_setting('m2b_l5.tenant_id', true), '')::uuid);

CREATE FUNCTION m2b_l5_preview.reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'M2B_L5_SOURCE_EVENTS_APPEND_ONLY';
END;
$$;
CREATE TRIGGER reject_l5_update_delete BEFORE UPDATE OR DELETE
    ON m2b_l5_preview.source_issuance_events
    FOR EACH ROW EXECUTE FUNCTION m2b_l5_preview.reject_mutation();
