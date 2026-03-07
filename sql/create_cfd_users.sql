-- Create cfd_users table for dashboard authentication
CREATE TABLE IF NOT EXISTS cfd_users (
    id BIGSERIAL PRIMARY KEY,
    surname TEXT NOT NULL,
    orcid TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast ORCID lookup
CREATE INDEX IF NOT EXISTS idx_cfd_users_orcid ON cfd_users (orcid);
