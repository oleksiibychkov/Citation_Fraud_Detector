-- Stage 2: Graph Analysis + Community/Clique Detection + Theorems

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
