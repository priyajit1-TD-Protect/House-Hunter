"""
Enrichment pipeline. For each listing, fill missing metrics from the best
available source, recording provenance. Then gate on completeness: listings
still missing a CRITICAL field after all sources are exhausted are dropped
(is_active=False) so they never score wrong or mislead.

Source priority per field:
  sqft   : realtor -> description regex -> housesigma  -> (drop if still missing)
  income : census (lat/lng nearest DA) -> neighbourhood table -> (drop)
  school : fraser (lat/lng / catchment) -> neighbourhood table -> (drop)
  canopy : neighbourhood table (Toronto Open Data) -> estimate -> (optional)

Critical fields (a listing is dropped if any is still missing):
  price, beds, baths, sqft, income, school
Non-critical (nice to have, won't drop):
  canopy
"""
import re
import math
import os
import httpx

CRITICAL_FIELDS = ["price", "beds", "baths", "sqft", "income", "school"]

# ── sqft ─────────────────────────────────────────────────────────

def sqft_from_realtor(item: dict) -> tuple[int | None, str]:
    """Realtor.ca Building.SizeInterior or FloorAreaMeasurements."""
    building = item.get("Building", {})
    size_str = building.get("SizeInterior", "")
    if size_str:
        try:
            val = float(size_str.split()[0].replace(",", ""))
            unit = size_str.split()[1].lower() if len(size_str.split()) > 1 else "sqft"
            return (int(val * 10.764) if "m" in unit else int(val)), "realtor"
        except Exception:
            pass
    # FloorAreaMeasurements is a list of {Type, Measurements}
    fam = building.get("FloorAreaMeasurements") or []
    for m in fam:
        meas = str(m.get("Measurements", ""))
        digits = re.sub(r"[^\d.]", "", meas.split("-")[0])
        if digits:
            try:
                return int(float(digits)), "realtor"
            except Exception:
                continue
    return None, "missing"


def sqft_from_description(item: dict) -> tuple[int | None, str]:
    """Parse sqft out of the public listing remarks / description text.
    e.g. 'approx 2,100 sq ft', '1850 sqft', '2000 square feet'."""
    text = ""
    for key in ("PublicRemarks", "Description"):
        text += " " + str(item.get(key, ""))
    text += " " + str(item.get("Property", {}).get("Address", {}).get("AddressText", ""))
    text = text.lower()

    patterns = [
        r"([\d,]{3,5})\s*(?:sq\.?\s*ft|sqft|square\s*feet|sf)\b",
        r"(?:approx\.?|about|~)\s*([\d,]{3,5})\s*(?:sq|sf)",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            try:
                val = int(m.group(1).replace(",", ""))
                if 400 <= val <= 12000:  # sanity bounds
                    return val, "description"
            except Exception:
                continue
    return None, "missing"


def sqft_from_housesigma(address: str, sb) -> tuple[int | None, str]:
    """Best-effort sqft fill from HouseSigma. NOTE: HouseSigma has no public
    API, uses Cloudflare + auth. This is intentionally best-effort and wrapped
    so any failure is silent. Requires SCRAPER_API_KEY (premium) to have any
    chance of success. Returns (None, 'missing') if unavailable."""
    api_key = os.getenv("SCRAPER_API_KEY", "")
    if not api_key or not address:
        return None, "missing"
    # HouseSigma blocks automated access aggressively; we do a single guarded
    # attempt via the proxy and give up gracefully on anything unexpected.
    try:
        # This is a placeholder for a search-by-address flow. HouseSigma's
        # internal endpoints change often and require a logged-in session, so
        # in practice this will usually return missing. Kept as a hook so the
        # chain is complete and can be upgraded if a stable route is found.
        return None, "missing"
    except Exception:
        return None, "missing"


def resolve_sqft(item: dict, address: str, sb) -> tuple[int | None, str]:
    for fn in (
        lambda: sqft_from_realtor(item),
        lambda: sqft_from_description(item),
        lambda: sqft_from_housesigma(address, sb),
    ):
        val, src = fn()
        if val:
            return val, src
    return None, "missing"


# ── geo helpers ──────────────────────────────────────────────────

def haversine_km(lat1, lng1, lat2, lng2) -> float:
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dlmb/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ── income ───────────────────────────────────────────────────────

def resolve_income(lat, lng, neigh: dict | None, sb) -> tuple[int | None, str]:
    """Nearest census Dissemination Area centroid, else neighbourhood table."""
    if lat and lng:
        rows = sb.table("census_income").select("avg_income, lat, lng").execute().data
        best, best_d = None, 1e9
        for r in rows:
            if r.get("lat") and r.get("lng"):
                d = haversine_km(lat, lng, r["lat"], r["lng"])
                if d < best_d:
                    best, best_d = r, d
        # Only trust a DA within ~2 km
        if best and best_d <= 2.0 and best.get("avg_income"):
            return best["avg_income"], "census"
    if neigh and neigh.get("avg_income"):
        return neigh["avg_income"], "table"
    return None, "missing"


# ── school ───────────────────────────────────────────────────────

def resolve_school(lat, lng, address: str, neigh: dict | None, sb) -> tuple[float | None, str]:
    """Nearest Fraser-rated school by lat/lng or catchment keyword,
    else neighbourhood table."""
    schools = sb.table("schools").select("*").execute().data
    addr_l = (address or "").lower()

    # keyword catchment match first
    for s in schools:
        for kw in (s.get("keywords") or []):
            if kw in addr_l and s.get("fraser_rating"):
                return float(s["fraser_rating"]), "fraser"

    # nearest school by distance
    if lat and lng:
        best, best_d = None, 1e9
        for s in schools:
            if s.get("lat") and s.get("lng"):
                d = haversine_km(lat, lng, s["lat"], s["lng"])
                if d < best_d:
                    best, best_d = s, d
        if best and best_d <= 2.5 and best.get("fraser_rating"):
            return float(best["fraser_rating"]), "fraser"

    if neigh and neigh.get("school_rating"):
        return float(neigh["school_rating"]), "table"
    return None, "missing"


# ── canopy (non-critical) ────────────────────────────────────────

def resolve_canopy(neigh: dict | None) -> tuple[float | None, str]:
    if neigh and neigh.get("canopy_pct") is not None:
        return float(neigh["canopy_pct"]), "table"
    return None, "missing"


# ── completeness gate ────────────────────────────────────────────

def check_completeness(fields: dict) -> tuple[bool, list[str]]:
    """fields = {'price':..., 'beds':..., 'baths':..., 'sqft':...,
                 'income':..., 'school':...}. Returns (is_complete, missing)."""
    missing = [f for f in CRITICAL_FIELDS if not fields.get(f)]
    return (len(missing) == 0, missing)
