-- Listings table (core)
CREATE TABLE listings (
  id                TEXT PRIMARY KEY,          -- Realtor.ca MLS number
  address           TEXT NOT NULL,
  neighbourhood     TEXT,
  city              TEXT DEFAULT 'Toronto',
  price             INTEGER NOT NULL,
  beds              INTEGER,
  baths             INTEGER,
  sqft              INTEGER,
  listing_type      TEXT,                      -- 'Detached' | 'Semi-Detached' | 'Townhouse'
  listed_date       DATE,
  realtor_url       TEXT,
  img_url           TEXT,
  lat               NUMERIC(9,6),
  lng               NUMERIC(9,6),
  raw_json          JSONB,
  is_active         BOOLEAN DEFAULT true,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

-- Scores table
CREATE TABLE listing_scores (
  id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id        TEXT REFERENCES listings(id) ON DELETE CASCADE,
  total_score       INTEGER,
  income_score      INTEGER,
  school_score      INTEGER,
  transit_score     INTEGER,
  price_score       INTEGER,
  size_score        INTEGER,
  lifestyle_score   INTEGER,
  neighbourhood_income  INTEGER,
  school_rating     NUMERIC(3,1),
  transit_min       INTEGER,
  scored_at         TIMESTAMPTZ DEFAULT now()
);

-- Neighbourhood reference data
CREATE TABLE neighbourhoods (
  id                SERIAL PRIMARY KEY,
  name              TEXT UNIQUE NOT NULL,
  avg_income        INTEGER,
  school_rating     NUMERIC(3,1),
  transit_min_union INTEGER,
  lifestyle_score   INTEGER,
  keywords          TEXT[]
);

-- Alerts log
CREATE TABLE alert_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id  TEXT REFERENCES listings(id),
  score       INTEGER,
  sent_at     TIMESTAMPTZ DEFAULT now(),
  channel     TEXT
);

-- Indexes
CREATE INDEX idx_listings_price ON listings(price);
CREATE INDEX idx_listings_active ON listings(is_active);
CREATE INDEX idx_scores_total ON listing_scores(total_score DESC);
CREATE INDEX idx_scores_listing ON listing_scores(listing_id);

-- Seed neighbourhood data
INSERT INTO neighbourhoods (name, avg_income, school_rating, transit_min_union, lifestyle_score, keywords) VALUES
  ('Davisville Village',  230000, 8.4, 18,  9, ARRAY['davisville', 'balliol', 'merton', 'soudan']),
  ('Mount Pleasant East', 215000, 8.1, 20,  8, ARRAY['mount pleasant', 'broadway', 'belsize']),
  ('High Park North',     205000, 8.3, 28, 10, ARRAY['high park', 'glenlake', 'indian road']),
  ('High Park–Swansea',   200000, 8.0, 30, 10, ARRAY['swansea', 'windermere', 'clendenan']),
  ('Roncesvalles',        185000, 7.8, 27,  8, ARRAY['roncesvalles', 'sorauren', 'fermanagh']),
  ('South Riverdale',     165000, 7.6, 24,  7, ARRAY['riverdale', 'broadview', 'withrow', 'langley']),
  ('Leaside South',       260000, 8.6, 33,  9, ARRAY['leaside', 'bessborough', 'moore', 'bayview']),
  ('Greenwood-Coxwell',   155000, 7.4, 26,  7, ARRAY['greenwood', 'coxwell', 'dingwall', 'fulton']);
