-- Stage 4: Views and indexes for reporting and dashboard

-- Anti-ranking view: latest fraud score per author, sorted descending
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

-- Index for faster snapshot lookups by author
CREATE INDEX IF NOT EXISTS idx_snapshots_author_date
    ON snapshots (author_id, snapshot_date DESC);

-- Index for faster evidence lookups
CREATE INDEX IF NOT EXISTS idx_report_evidence_author
    ON report_evidence (author_id, created_at DESC);

-- Index for faster connection map queries
CREATE INDEX IF NOT EXISTS idx_author_connections_source
    ON author_connections (source_author_id);
CREATE INDEX IF NOT EXISTS idx_author_connections_target
    ON author_connections (target_author_id);

-- Index for watchlist active queries
CREATE INDEX IF NOT EXISTS idx_watchlist_active
    ON watchlist (is_active) WHERE is_active = true;
