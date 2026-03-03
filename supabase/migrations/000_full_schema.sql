-- ============================================================
-- Citation Fraud Detector — Full Database Schema
-- ============================================================
-- Run this SQL in Supabase SQL Editor to set up the database.
-- This combines all migrations (001-006) into one file.
-- ============================================================

-- ===================== Stage 1: Core Tables ==================

-- Authors
CREATE TABLE IF NOT EXISTS authors (
    id              BIGSERIAL PRIMARY KEY,
    scopus_id       VARCHAR(20) UNIQUE,
    orcid           VARCHAR(25) UNIQUE,
    openalex_id     VARCHAR(50),
    surname         VARCHAR(200) NOT NULL,
    full_name       VARCHAR(500),
    display_name_variants TEXT[],
    institution     VARCHAR(500),
    discipline      VARCHAR(200),
    h_index         INTEGER,
    publication_count INTEGER,
    citation_count  INTEGER,
    source_api      VARCHAR(20) NOT NULL,
    raw_data        JSONB,
    career_start_year INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_at_least_one_id CHECK (scopus_id IS NOT NULL OR orcid IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_authors_scopus_id ON authors (scopus_id);
CREATE INDEX IF NOT EXISTS idx_authors_orcid ON authors (orcid);
CREATE INDEX IF NOT EXISTS idx_authors_openalex_id ON authors (openalex_id);
CREATE INDEX IF NOT EXISTS idx_authors_discipline_pubcount ON authors (discipline, publication_count);
CREATE INDEX IF NOT EXISTS idx_authors_career_start ON authors (career_start_year) WHERE career_start_year IS NOT NULL;

-- Publications
CREATE TABLE IF NOT EXISTS publications (
    id              BIGSERIAL PRIMARY KEY,
    author_id       BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    work_id         VARCHAR(100) NOT NULL,
    doi             VARCHAR(200),
    title           TEXT,
    abstract        TEXT,
    publication_date DATE,
    journal         VARCHAR(500),
    citation_count  INTEGER DEFAULT 0,
    references_list TEXT[],
    source_api      VARCHAR(20) NOT NULL,
    raw_data        JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (author_id, work_id)
);

CREATE INDEX IF NOT EXISTS idx_publications_author_id ON publications (author_id);
CREATE INDEX IF NOT EXISTS idx_publications_work_id ON publications (work_id);
CREATE INDEX IF NOT EXISTS idx_publications_doi ON publications (doi);

-- Citations
CREATE TABLE IF NOT EXISTS citations (
    id                  BIGSERIAL PRIMARY KEY,
    source_work_id      VARCHAR(100) NOT NULL,
    target_work_id      VARCHAR(100) NOT NULL,
    source_author_id    BIGINT REFERENCES authors(id),
    target_author_id    BIGINT REFERENCES authors(id),
    citation_date       DATE,
    is_self_citation    BOOLEAN DEFAULT FALSE,
    source_api          VARCHAR(20) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (source_work_id, target_work_id)
);

CREATE INDEX IF NOT EXISTS idx_citations_source_work ON citations (source_work_id);
CREATE INDEX IF NOT EXISTS idx_citations_target_work ON citations (target_work_id);
CREATE INDEX IF NOT EXISTS idx_citations_source_author ON citations (source_author_id);
CREATE INDEX IF NOT EXISTS idx_citations_target_author ON citations (target_author_id);

-- Indicators
CREATE TABLE IF NOT EXISTS indicators (
    id              BIGSERIAL PRIMARY KEY,
    author_id       BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    indicator_type  VARCHAR(30) NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    details         JSONB,
    algorithm_version VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    calculated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE (author_id, indicator_type, calculated_at)
);

CREATE INDEX IF NOT EXISTS idx_indicators_author_id ON indicators (author_id);
CREATE INDEX IF NOT EXISTS idx_indicators_type ON indicators (indicator_type);

-- Fraud Scores
CREATE TABLE IF NOT EXISTS fraud_scores (
    id                  BIGSERIAL PRIMARY KEY,
    author_id           BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    score               DOUBLE PRECISION NOT NULL CHECK (score >= 0.0 AND score <= 1.0),
    confidence_level    VARCHAR(20) NOT NULL,
    indicator_weights   JSONB NOT NULL,
    indicator_values    JSONB NOT NULL,
    triggered_indicators TEXT[],
    status              VARCHAR(30) NOT NULL DEFAULT 'completed',
    algorithm_version   VARCHAR(20) NOT NULL DEFAULT '1.0.0',
    calculated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fraud_scores_author_id ON fraud_scores (author_id);
CREATE INDEX IF NOT EXISTS idx_fraud_scores_score ON fraud_scores (score DESC);

-- API Cache
CREATE TABLE IF NOT EXISTS api_cache (
    id              BIGSERIAL PRIMARY KEY,
    cache_key       VARCHAR(64) NOT NULL UNIQUE,
    endpoint        VARCHAR(500) NOT NULL,
    params          JSONB,
    response_data   JSONB NOT NULL,
    source_api      VARCHAR(20) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_api_cache_key ON api_cache (cache_key);
CREATE INDEX IF NOT EXISTS idx_api_cache_expires ON api_cache (expires_at);

-- ===================== Stage 2: Graph Analysis ==================

-- Community detection results
CREATE TABLE IF NOT EXISTS communities (
    id                  BIGSERIAL PRIMARY KEY,
    community_id        INTEGER NOT NULL,
    author_id           BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    modularity          DOUBLE PRECISION,
    internal_density    DOUBLE PRECISION,
    external_density    DOUBLE PRECISION,
    is_suspicious       BOOLEAN DEFAULT FALSE,
    algorithm_version   VARCHAR(20) NOT NULL DEFAULT '2.0.0',
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_communities_author ON communities (author_id);
CREATE INDEX IF NOT EXISTS idx_communities_community ON communities (community_id);

-- Detected k-cliques
CREATE TABLE IF NOT EXISTS cliques (
    id                  BIGSERIAL PRIMARY KEY,
    clique_size         INTEGER NOT NULL CHECK (clique_size >= 3),
    member_author_ids   BIGINT[] NOT NULL,
    citation_density    DOUBLE PRECISION,
    probability         DOUBLE PRECISION,
    severity            VARCHAR(20) NOT NULL,
    algorithm_version   VARCHAR(20) NOT NULL DEFAULT '2.0.0',
    detected_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_cliques_severity ON cliques (severity);
CREATE INDEX IF NOT EXISTS idx_cliques_size ON cliques (clique_size);

-- Theorem hierarchy results
CREATE TABLE IF NOT EXISTS theorem_results (
    id                  BIGSERIAL PRIMARY KEY,
    author_id           BIGINT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    theorem_number      INTEGER NOT NULL CHECK (theorem_number IN (1, 2, 3)),
    passed              BOOLEAN NOT NULL,
    details             JSONB,
    algorithm_version   VARCHAR(20) NOT NULL DEFAULT '2.0.0',
    calculated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_theorem_results_author ON theorem_results (author_id);

-- ===================== Stage 3: Temporal + Monitoring ==================

-- Periodic snapshots of author metrics
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
CREATE INDEX IF NOT EXISTS idx_snapshots_author_date ON snapshots (author_id, snapshot_date DESC);

-- Watchlist
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

-- Peer groups
CREATE TABLE IF NOT EXISTS peer_groups (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id bigint NOT NULL REFERENCES authors(id),
    peer_author_ids bigint[] NOT NULL DEFAULT '{}',
    discipline text NOT NULL,
    matching_criteria jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_peer_groups_author ON peer_groups (author_id);

-- Discipline baselines
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

-- Embeddings (pgvector optional)
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

-- Author connections
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

-- Evidence store
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
CREATE INDEX IF NOT EXISTS idx_report_evidence_author ON report_evidence (author_id, created_at DESC);

-- Algorithm versions
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

-- Audit log
CREATE TABLE IF NOT EXISTS audit_log (
    id                  BIGSERIAL PRIMARY KEY,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    action              VARCHAR(50) NOT NULL,
    target_author_id    BIGINT REFERENCES authors(id),
    details             JSONB,
    ip_address          INET,
    user_id             VARCHAR(200),
    api_key_id          BIGINT
);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_author ON audit_log (target_author_id);

-- ===================== Stage 5: Calibration ==================

CREATE TABLE IF NOT EXISTS calibration_runs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    optimized_weights jsonb NOT NULL,
    precision_score float NOT NULL DEFAULT 0.0,
    recall_score float NOT NULL DEFAULT 0.0,
    f1_score float NOT NULL DEFAULT 0.0,
    false_positive_rate float NOT NULL DEFAULT 0.0,
    samples_used integer NOT NULL DEFAULT 0,
    converged boolean NOT NULL DEFAULT false,
    algorithm_version text NOT NULL,
    details jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- ===================== Stage 6: API Keys ==================

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

-- ===================== Stage 4: Views ==================

CREATE OR REPLACE VIEW anti_ranking AS
SELECT DISTINCT ON (fs.author_id)
    fs.author_id,
    a.surname,
    a.full_name,
    a.discipline,
    a.institution,
    fs.score,
    fs.confidence_level,
    fs.triggered_indicators,
    fs.algorithm_version,
    fs.calculated_at
FROM fraud_scores fs
JOIN authors a ON a.id = fs.author_id
ORDER BY fs.author_id, fs.calculated_at DESC;

-- ===================== RLS Policies ==================
-- Allow anon key full access (API handles auth via X-API-Key header)

ALTER TABLE authors ENABLE ROW LEVEL SECURITY;
ALTER TABLE publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE citations ENABLE ROW LEVEL SECURITY;
ALTER TABLE indicators ENABLE ROW LEVEL SECURITY;
ALTER TABLE fraud_scores ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE communities ENABLE ROW LEVEL SECURITY;
ALTER TABLE cliques ENABLE ROW LEVEL SECURITY;
ALTER TABLE theorem_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE peer_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE discipline_baselines ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE author_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE report_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE algorithm_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Allow anon role full CRUD (the API authenticates via its own X-API-Key system)
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'authors', 'publications', 'citations', 'indicators', 'fraud_scores',
            'api_cache', 'communities', 'cliques', 'theorem_results', 'snapshots',
            'watchlist', 'peer_groups', 'discipline_baselines', 'embeddings',
            'author_connections', 'report_evidence', 'algorithm_versions',
            'audit_log', 'calibration_runs', 'api_keys'
        ])
    LOOP
        EXECUTE format('CREATE POLICY "anon_full_%s" ON %I FOR ALL TO anon USING (true) WITH CHECK (true)', tbl, tbl);
    END LOOP;
END $$;

-- ===================== Seed Data ==================

-- Discipline baselines
INSERT INTO discipline_baselines (discipline, avg_scr, std_scr, avg_citations_per_paper, avg_h_index_growth_rate, citation_half_life_years, avg_papers_per_year, journal_quartile_medians, sample_size, source) VALUES
('Computer Science', 0.12, 0.08, 8.5, 1.2, 5.5, 3.0, '{"Q1": 15.0, "Q2": 8.0, "Q3": 4.0, "Q4": 2.0}', 50000, 'Ioannidis et al. 2019, Waltman & van Eck 2012'),
('Medicine', 0.08, 0.06, 12.0, 1.5, 7.0, 4.5, '{"Q1": 25.0, "Q2": 12.0, "Q3": 6.0, "Q4": 3.0}', 100000, 'Ioannidis et al. 2019'),
('Physics', 0.10, 0.07, 10.0, 1.3, 6.0, 3.5, '{"Q1": 20.0, "Q2": 10.0, "Q3": 5.0, "Q4": 2.5}', 60000, 'Ioannidis et al. 2019'),
('Chemistry', 0.09, 0.06, 11.0, 1.4, 6.5, 4.0, '{"Q1": 22.0, "Q2": 11.0, "Q3": 5.5, "Q4": 2.5}', 55000, 'Ioannidis et al. 2019'),
('Social Sciences', 0.15, 0.10, 6.0, 0.8, 8.0, 2.0, '{"Q1": 10.0, "Q2": 5.0, "Q3": 3.0, "Q4": 1.5}', 40000, 'Ioannidis et al. 2019')
ON CONFLICT (discipline) DO NOTHING;

-- Algorithm versions
INSERT INTO algorithm_versions (version, release_date, indicator_count, changelog) VALUES
('1.0.0', '2025-01-01', 5, 'MVP: SCR, MCR, CB, TA, HTA'),
('2.0.0', '2025-06-01', 12, 'Graph analysis: RLA, GIC, EIGEN, BETWEENNESS, PAGERANK, COMMUNITY, CLIQUE + Theorems 1-3'),
('3.0.0', '2025-12-01', 15, 'Temporal analysis: CV, SBD, CTX + discipline baselines + enhanced TA/HTA'),
('4.0.0', '2026-01-15', 20, 'Stage 5: ANA, CC, SSD, PB, CPC + peer benchmarking + calibration'),
('5.0.0', '2026-02-15', 22, 'Stage 9: JSCR, COERCE + CRIS integration + notifications + incremental updates')
ON CONFLICT (version) DO NOTHING;
