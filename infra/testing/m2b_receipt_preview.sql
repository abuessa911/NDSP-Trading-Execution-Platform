-- M2-B disposable PostgreSQL proof, NOT a production NEX migration.
-- This file may be applied only to a fresh isolated database named
-- nex_m2b_preview by scripts/m2b_postgres_preview.py.
CREATE SCHEMA m2b_preview;
REVOKE ALL ON SCHEMA m2b_preview FROM PUBLIC;
GRANT USAGE ON SCHEMA m2b_preview TO nex_m2b_preview_app;

CREATE TABLE m2b_preview.decision_receipts (
    tenant_id uuid NOT NULL,
    decision_id uuid NOT NULL,
    decision_version bigint NOT NULL CHECK (decision_version > 0),
    evidence_hash text NOT NULL CHECK (
        evidence_hash ~ '^sha256:[a-f0-9]{64}$'
    ),
    observed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (tenant_id, decision_id, decision_version)
);

REVOKE ALL ON m2b_preview.decision_receipts FROM PUBLIC;
GRANT SELECT, INSERT ON m2b_preview.decision_receipts TO nex_m2b_preview_app;
REVOKE UPDATE, DELETE, TRUNCATE ON m2b_preview.decision_receipts
    FROM nex_m2b_preview_app;
ALTER TABLE m2b_preview.decision_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE m2b_preview.decision_receipts FORCE ROW LEVEL SECURITY;

CREATE POLICY preview_tenant_read
ON m2b_preview.decision_receipts FOR SELECT
TO nex_m2b_preview_app
USING (
    tenant_id = NULLIF(current_setting('m2b.tenant_id', true), '')::uuid
);

CREATE POLICY preview_tenant_append
ON m2b_preview.decision_receipts FOR INSERT
TO nex_m2b_preview_app
WITH CHECK (
    tenant_id = NULLIF(current_setting('m2b.tenant_id', true), '')::uuid
);

CREATE FUNCTION m2b_preview.reject_receipt_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'M2B_RECEIPT_APPEND_ONLY';
END;
$$;

CREATE TRIGGER reject_receipt_update_delete
BEFORE UPDATE OR DELETE ON m2b_preview.decision_receipts
FOR EACH ROW EXECUTE FUNCTION m2b_preview.reject_receipt_mutation();
