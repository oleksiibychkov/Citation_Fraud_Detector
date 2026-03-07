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

-- Analysis log — tracks who analyzed which author
CREATE TABLE IF NOT EXISTS analysis_log (
    id BIGSERIAL PRIMARY KEY,
    user_orcid TEXT NOT NULL,
    user_surname TEXT NOT NULL DEFAULT '',
    author_name TEXT NOT NULL,
    scopus_id TEXT,
    author_orcid TEXT,
    fraud_score DOUBLE PRECISION,
    confidence_level TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_analysis_log_user ON analysis_log (user_orcid);
CREATE INDEX IF NOT EXISTS idx_analysis_log_created ON analysis_log (created_at DESC);
