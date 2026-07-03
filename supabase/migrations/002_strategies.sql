-- Add per-strategy scoring columns to listing_scores.
-- Strategy 1: Nucleus Family (detached / semi / freehold townhouse, TTC < 40 min)
-- Strategy 2: Happy Big Family (detached only, transit incl. GO door-to-door < 75 min)

ALTER TABLE listing_scores
  -- Two transit measurements
  ADD COLUMN IF NOT EXISTS transit_min_ttc   INTEGER,   -- TTC-only to Union (Nucleus)
  ADD COLUMN IF NOT EXISTS transit_min_go    INTEGER,   -- incl. GO/rail to Union (Big Family)

  -- Nucleus Family scores
  ADD COLUMN IF NOT EXISTS total_score_nucleus     INTEGER,
  ADD COLUMN IF NOT EXISTS transit_score_nucleus   INTEGER,
  ADD COLUMN IF NOT EXISTS eligible_nucleus        BOOLEAN DEFAULT false,

  -- Happy Big Family scores
  ADD COLUMN IF NOT EXISTS total_score_big_family   INTEGER,
  ADD COLUMN IF NOT EXISTS transit_score_big_family INTEGER,
  ADD COLUMN IF NOT EXISTS eligible_big_family      BOOLEAN DEFAULT false;

-- Indexes for fast sorting per strategy
CREATE INDEX IF NOT EXISTS idx_scores_nucleus   ON listing_scores(total_score_nucleus DESC);
CREATE INDEX IF NOT EXISTS idx_scores_bigfamily ON listing_scores(total_score_big_family DESC);
