-- Stage 3: Temporal Analysis + Full Schema (15 tables total)

-- Periodic snapshots of author metrics for watchlist tracking
CREATE TABLE IF NOT EXISTS snapshots (
    id                  BIGSERIAL PRIMARY KEY,
    author_id           BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    fraud_score         DOUBLE PRECISION,
    confidence_level    VARCHAR(20),
    indicator_values    JSONB,
    h_index             INTEGER,
    citation_count      INTEGER,
    publication_count   INTEGER,
    algorithm_version   VARCHAR(20) NOT NULL,
    snapshot_date       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_snapshots_author ON snapshots (author_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_date ON snapshots (snapshot_date DESC);

-- Authors under monitoring
CREATE TABLE IF NOT EXISTS watchlist (
    id                      BIGSERIAL PRIMARY KEY,
    author_id               BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    reason                  TEXT,
    sensitivity_overrides   JSONB,
    notes                   TEXT,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(author_id)
);
CREATE INDEX IF NOT EXISTS idx_watchlist_active ON watchlist (is_active) WHERE is_active = TRUE;

-- Peer groups for benchmark comparison
CREATE TABLE IF NOT EXISTS peer_groups (
    id                  BIGSERIAL PRIMARY KEY,
    author_id           BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    peer_author_ids     BIGINT[] NOT NULL,
    discipline          VARCHAR(200),
    matching_criteria   JSONB,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_peer_groups_author ON peer_groups (author_id);

-- Statistical baselines per discipline
CREATE TABLE IF NOT EXISTS discipline_baselines (
    id                          BIGSERIAL PRIMARY KEY,
    discipline                  VARCHAR(200) NOT NULL UNIQUE,
    avg_scr                     DOUBLE PRECISION NOT NULL,
    std_scr                     DOUBLE PRECISION NOT NULL,
    avg_citations_per_paper     DOUBLE PRECISION,
    avg_h_index_growth_rate     DOUBLE PRECISION,
    citation_half_life_years    DOUBLE PRECISION,
    avg_papers_per_year         DOUBLE PRECISION,
    journal_quartile_medians    JSONB,
    sample_size                 INTEGER,
    source                      VARCHAR(200),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Embeddings for sentence similarity (pgvector stub)
-- Note: requires pgvector extension enabled in Supabase
DO $$ BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pgvector extension not available, skipping';
END $$;

CREATE TABLE IF NOT EXISTS embeddings (
    id                  BIGSERIAL PRIMARY KEY,
    publication_id      BIGINT NOT NULL REFERENCES publications(id) ON DELETE CASCADE,
    embedding           BYTEA,
    model_name          VARCHAR(100),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(publication_id, model_name)
);
CREATE INDEX IF NOT EXISTS idx_embeddings_pub ON embeddings (publication_id);

-- Connection map for visualization
CREATE TABLE IF NOT EXISTS author_connections (
    id                  BIGSERIAL PRIMARY KEY,
    source_author_id    BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    target_author_id    BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    connection_type     VARCHAR(50) NOT NULL,
    strength            DOUBLE PRECISION,
    details             JSONB,
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(source_author_id, target_author_id, connection_type)
);
CREATE INDEX IF NOT EXISTS idx_connections_source ON author_connections (source_author_id);
CREATE INDEX IF NOT EXISTS idx_connections_target ON author_connections (target_author_id);

-- Evidence store for reports
CREATE TABLE IF NOT EXISTS report_evidence (
    id                  BIGSERIAL PRIMARY KEY,
    author_id           BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    evidence_type       VARCHAR(50) NOT NULL,
    indicator_type      VARCHAR(30),
    description         TEXT,
    data                JSONB,
    severity            VARCHAR(20),
    algorithm_version   VARCHAR(20) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_evidence_author ON report_evidence (author_id);
CREATE INDEX IF NOT EXISTS idx_evidence_type ON report_evidence (evidence_type);

-- Algorithm version registry
CREATE TABLE IF NOT EXISTS algorithm_versions (
    id                  BIGSERIAL PRIMARY KEY,
    version             VARCHAR(20) NOT NULL UNIQUE,
    release_date        DATE NOT NULL,
    indicator_count     INTEGER,
    thresholds          JSONB,
    weights             JSONB,
    changelog           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Append-only audit trail
CREATE TABLE IF NOT EXISTS audit_log (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action              VARCHAR(50) NOT NULL,
    target_author_id    BIGINT REFERENCES authors(id),
    details             JSONB,
    ip_address          INET
);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_author ON audit_log (target_author_id);

-- RLS policies
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE discipline_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE author_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE algorithm_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;

-- Read-access policies for authenticated users
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON snapshots FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON watchlist FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON peer_groups FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON discipline_baselines FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON embeddings FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON author_connections FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON report_evidence FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON algorithm_versions FOR SELECT TO authenticated USING (true);
CREATE POLICY IF NOT EXISTS "authenticated_read_all" ON audit_log FOR SELECT TO authenticated USING (true);

-- Public read for discipline baselines
CREATE POLICY IF NOT EXISTS "anon_read_baselines" ON discipline_baselines FOR SELECT TO anon USING (true);

-- Seed data: discipline baselines (from published scientometric literature)
INSERT INTO discipline_baselines (discipline, avg_scr, std_scr, avg_citations_per_paper, avg_h_index_growth_rate, citation_half_life_years, avg_papers_per_year, journal_quartile_medians, sample_size, source) VALUES
('Computer Science', 0.12, 0.08, 8.5, 1.2, 5.5, 3.0, '{"Q1": 15.0, "Q2": 8.0, "Q3": 4.0, "Q4": 2.0}', 50000, 'Ioannidis et al. 2019, Waltman & van Eck 2012'),
('Medicine', 0.08, 0.06, 12.0, 1.5, 7.0, 4.5, '{"Q1": 25.0, "Q2": 12.0, "Q3": 6.0, "Q4": 3.0}', 100000, 'Ioannidis et al. 2019'),
('Physics', 0.10, 0.07, 10.0, 1.3, 6.0, 3.5, '{"Q1": 20.0, "Q2": 10.0, "Q3": 5.0, "Q4": 2.5}', 60000, 'Ioannidis et al. 2019'),
('Chemistry', 0.09, 0.06, 11.0, 1.4, 6.5, 4.0, '{"Q1": 22.0, "Q2": 11.0, "Q3": 5.5, "Q4": 2.5}', 55000, 'Ioannidis et al. 2019'),
('Social Sciences', 0.15, 0.10, 6.0, 0.8, 8.0, 2.0, '{"Q1": 10.0, "Q2": 5.0, "Q3": 3.0, "Q4": 1.5}', 40000, 'Ioannidis et al. 2019')
ON CONFLICT (discipline) DO NOTHING;

-- Seed data: algorithm versions
INSERT INTO algorithm_versions (version, release_date, indicator_count, changelog) VALUES
('1.0.0', '2025-01-01', 5, 'MVP: SCR, MCR, CB, TA, HTA'),
('2.0.0', '2025-06-01', 12, 'Graph analysis: RLA, GIC, EIGEN, BETWEENNESS, PAGERANK, COMMUNITY, CLIQUE + Theorems 1-3'),
('3.0.0', '2025-12-01', 15, 'Temporal analysis: CV, SBD, CTX + discipline baselines + enhanced TA/HTA')
ON CONFLICT (version) DO NOTHING;
