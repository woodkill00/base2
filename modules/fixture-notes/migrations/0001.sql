CREATE TABLE fixture_notes (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX fixture_notes_tenant_idx ON fixture_notes (tenant_id, created_at);
