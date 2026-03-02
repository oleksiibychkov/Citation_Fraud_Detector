-- Stage 5: Expanded Analytics schema changes
-- Adds career_start_year, peer matching indexes, and calibration_runs table.

-- Add career_start_year to authors table
ALTER TABLE authors ADD COLUMN IF NOT EXISTS career_start_year integer;

-- Index for peer matching queries
CREATE INDEX IF NOT EXISTS idx_authors_discipline_pubcount
    ON authors (discipline, publication_count);

CREATE INDEX IF NOT EXISTS idx_authors_career_start
    ON authors (career_start_year)
    WHERE career_start_year IS NOT NULL;

-- Peer groups table
CREATE TABLE IF NOT EXISTS peer_groups (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    author_id bigint NOT NULL REFERENCES authors(id),
    peer_author_ids bigint[] NOT NULL DEFAULT '{}',
    discipline text NOT NULL,
    matching_criteria jsonb DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_peer_groups_author
    ON peer_groups (author_id);

-- Calibration runs table
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

-- RLS policies for new tables
ALTER TABLE peer_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE calibration_runs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "peer_groups_select" ON peer_groups FOR SELECT USING (true);
CREATE POLICY "peer_groups_insert" ON peer_groups FOR INSERT WITH CHECK (true);
CREATE POLICY "peer_groups_update" ON peer_groups FOR UPDATE USING (true);

CREATE POLICY "calibration_runs_select" ON calibration_runs FOR SELECT USING (true);
CREATE POLICY "calibration_runs_insert" ON calibration_runs FOR INSERT WITH CHECK (true);
