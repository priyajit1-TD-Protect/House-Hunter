-- Ensure listings.updated_at refreshes on every update/upsert (DEFAULT now()
-- only fires on INSERT). The scraper's stale-marker uses updated_at to avoid
-- deactivating listings touched during the current run.

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_listings_updated_at ON listings;
CREATE TRIGGER trg_listings_updated_at
  BEFORE UPDATE ON listings
  FOR EACH ROW
  EXECUTE FUNCTION set_updated_at();
