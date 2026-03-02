-- Stage 6: API keys and audit log extensions.

-- API keys table for authentication and rate limiting
CREATE TABLE IF NOT EXISTS api_keys (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    key_hash varchar(64) NOT NULL UNIQUE,
    name varchar(200) NOT NULL,
    role varchar(20) NOT NULL DEFAULT 'reader'
        CHECK (role IN ('reader', 'analyst', 'admin')),
    rate_limit_per_minute integer NOT NULL DEFAULT 60,
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    last_used_at timestamptz
);

CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys (key_hash) WHERE is_active = true;

-- Extend audit_log with user/key tracking
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS user_id varchar(200);
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS api_key_id bigint REFERENCES api_keys(id);

-- RLS policies
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
CREATE POLICY "api_keys_select" ON api_keys FOR SELECT USING (true);
CREATE POLICY "api_keys_update" ON api_keys FOR UPDATE USING (true);
