-- Enrichment pipeline: provenance tracking + data completeness.
-- Every metric records where it came from so we never silently trust a guess.

ALTER TABLE listings
  ADD COLUMN IF NOT EXISTS sqft_source        TEXT DEFAULT 'missing',  -- realtor|housesigma|description|missing
  ADD COLUMN IF NOT EXISTS canopy_pct         NUMERIC(4,1),            -- neighbourhood tree canopy %
  ADD COLUMN IF NOT EXISTS canopy_source      TEXT DEFAULT 'missing',
  ADD COLUMN IF NOT EXISTS income_source      TEXT DEFAULT 'missing',  -- census|table|missing
  ADD COLUMN IF NOT EXISTS school_source      TEXT DEFAULT 'missing',  -- fraser|table|missing
  ADD COLUMN IF NOT EXISTS data_complete      BOOLEAN DEFAULT false,   -- passed completeness gate
  ADD COLUMN IF NOT EXISTS missing_fields     TEXT[] DEFAULT '{}';     -- which criticals are absent

-- Canopy reference by neighbourhood (Toronto Open Data: tree canopy %)
ALTER TABLE neighbourhoods
  ADD COLUMN IF NOT EXISTS canopy_pct NUMERIC(4,1);

-- School reference (Fraser Institute ratings), matched by catchment keywords
CREATE TABLE IF NOT EXISTS schools (
  id            SERIAL PRIMARY KEY,
  name          TEXT NOT NULL,
  fraser_rating NUMERIC(3,1),
  city          TEXT,
  lat           NUMERIC(9,6),
  lng           NUMERIC(9,6),
  keywords      TEXT[]        -- street/area keywords for catchment matching
);

-- Census income reference by Dissemination Area centroid (StatCan)
CREATE TABLE IF NOT EXISTS census_income (
  id            SERIAL PRIMARY KEY,
  da_id         TEXT,         -- Dissemination Area ID
  avg_income    INTEGER,
  lat           NUMERIC(9,6), -- DA centroid
  lng           NUMERIC(9,6)
);

CREATE INDEX IF NOT EXISTS idx_listings_complete ON listings(data_complete);
CREATE INDEX IF NOT EXISTS idx_census_latlng ON census_income(lat, lng);
