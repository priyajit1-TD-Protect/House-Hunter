-- Neighbourhoods for the Happy Big Family strategy search area:
-- Oakville, Mississauga, Etobicoke, Richmond Hill.
-- transit_min_union here is a rough GO/transit estimate to Union (door-to-door
-- peak) used only as a fallback; the real value comes from Google at scrape time.

INSERT INTO neighbourhoods (name, avg_income, school_rating, transit_min_union, lifestyle_score, keywords)
VALUES
  -- ── Oakville ────────────────────────────────────────────────
  ('Oakville - Old Oakville', 240000, 8.7, 55, 9,
     ARRAY['old oakville', 'reynolds', 'trafalgar', 'oakville']),
  ('Oakville - Glen Abbey',   220000, 8.6, 62, 9,
     ARRAY['glen abbey', 'abbey', 'pilgrims', 'nottinghill']),
  ('Oakville - Bronte',       210000, 8.4, 60, 8,
     ARRAY['bronte', 'lakeshore w', 'jones', 'east']),
  ('Oakville - Joshua Creek', 250000, 8.8, 58, 8,
     ARRAY['joshua creek', 'grand oak', 'river oaks']),

  -- ── Mississauga ─────────────────────────────────────────────
  ('Mississauga - Lorne Park',  260000, 8.9, 45, 9,
     ARRAY['lorne park', 'indian rd', 'watersedge']),
  ('Mississauga - Port Credit', 200000, 8.3, 38, 9,
     ARRAY['port credit', 'mineola', 'high st', 'lakeshore rd']),
  ('Mississauga - Streetsville',185000, 8.1, 55, 8,
     ARRAY['streetsville', 'queen st s', 'britannia']),
  ('Mississauga - Erin Mills',  195000, 8.4, 52, 8,
     ARRAY['erin mills', 'credit valley', 'sawmill']),
  ('Mississauga - Clarkson',    180000, 8.0, 42, 7,
     ARRAY['clarkson', 'southdown', 'meadowwood']),

  -- ── Etobicoke ───────────────────────────────────────────────
  ('Etobicoke - Kingsway',      280000, 8.7, 30, 9,
     ARRAY['kingsway', 'the kingsway', 'montgomery', 'humbertown']),
  ('Etobicoke - Mimico',        175000, 7.8, 25, 8,
     ARRAY['mimico', 'lakeshore blvd', 'royal york']),
  ('Etobicoke - Islington',     210000, 8.2, 32, 8,
     ARRAY['islington', 'islington village', 'burnhamthorpe']),
  ('Etobicoke - Sunnylea',      230000, 8.5, 28, 8,
     ARRAY['sunnylea', 'park lawn', 'berry rd']),
  ('Etobicoke - Long Branch',   165000, 7.6, 30, 7,
     ARRAY['long branch', 'lake promenade', 'thirty first']),

  -- ── Richmond Hill ───────────────────────────────────────────
  ('Richmond Hill - Mill Pond',   240000, 8.8, 60, 8,
     ARRAY['mill pond', 'trench', 'mill st', 'richmond hill']),
  ('Richmond Hill - Bayview Hill', 260000, 9.0, 62, 8,
     ARRAY['bayview hill', 'bayview', 'sixteenth']),
  ('Richmond Hill - Oak Ridges',  210000, 8.3, 70, 8,
     ARRAY['oak ridges', 'yonge st', 'north lake', 'bond lake']),
  ('Richmond Hill - Jefferson',   225000, 8.6, 65, 8,
     ARRAY['jefferson', 'gamble', 'shaftsbury'])
ON CONFLICT (name) DO NOTHING;
