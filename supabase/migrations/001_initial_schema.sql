-- CFD MVP Schema v1.0
-- 6 tables for Stage 1

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
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_at_least_one_id CHECK (scopus_id IS NOT NULL OR orcid IS NOT NULL)
);

CREATE INDEX IF NOT EXISTS idx_authors_scopus_id ON authors (scopus_id);
CREATE INDEX IF NOT EXISTS idx_authors_orcid ON authors (orcid);
CREATE INDEX IF NOT EXISTS idx_authors_openalex_id ON authors (openalex_id);

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
