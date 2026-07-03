"""
Scoring engine: 0–100 score per listing, per strategy.

Shared dimensions (income, school, price, size, lifestyle) are computed once.
Transit differs by strategy:
  - Nucleus     -> TTC-only minutes  (target < 40)
  - Big Family  -> incl. GO minutes  (target < 75)

Eligibility (property type) is decided upstream in scraper.py via strategies.py.
Ineligible listings get total_score = 0 and eligible flag False for that strategy.
"""
from supabase import Client
from strategies import STRATEGIES

WEIGHTS = {
    "income":    0.25,
    "school":    0.25,
    "transit":   0.20,
    "price":     0.15,
    "size":      0.10,
    "lifestyle": 0.05,
}

BUDGET_MAX = 1_700_000


def match_neighbourhood(address: str, sb: Client) -> dict | None:
    rows = sb.table("neighbourhoods").select("*").execute().data
    address_lower = address.lower()
    for row in rows:
        for kw in (row.get("keywords") or []):
            if kw in address_lower:
                return row
    return None


def _transit_score(transit_min: int | None, target: int, fallback_est: int) -> tuple[int, int]:
    """Return (transit_score, transit_min_used)."""
    tmin = transit_min if transit_min is not None else fallback_est
    if tmin <= target:
        score = max(0, ((target - tmin) / target) * 100)
    else:
        score = 0
    return round(score), tmin


def score_all_strategies(
    listing: dict,
    sb: Client,
    transit_ttc: int | None,
    transit_go: int | None,
    eligible_nucleus: bool,
    eligible_big_family: bool,
) -> dict:
    """Compute both strategies' scores for one listing and return a flat row
    matching the listing_scores columns."""
    neigh = match_neighbourhood(listing.get("address", ""), sb)

    if neigh:
        income_raw  = neigh.get("avg_income", 0)
        school_raw  = neigh.get("school_rating", 0)
        transit_est = neigh.get("transit_min_union", 99)
        lifestyle_r = neigh.get("lifestyle_score", 5)
    else:
        income_raw, school_raw, transit_est, lifestyle_r = 0, 0, 99, 5

    # ── Shared dimensions ────────────────────────────────────────
    income_score = min(100, (income_raw / 200_000) * 100)
    school_score = min(100, (school_raw / 8.0) * 100)

    price = listing.get("price", 0)
    price_score = max(0, min(100, ((BUDGET_MAX - price) / BUDGET_MAX) * 80 + 20)) if price <= BUDGET_MAX else 0

    sqft = listing.get("sqft") or 0
    size_score = min(100, ((sqft - 1500) / 1000) * 100 + 60) if sqft >= 1500 else (sqft / 1500) * 40

    lifestyle_score = (lifestyle_r / 10) * 100

    def combine(transit_score: float) -> int:
        total = round(
            income_score    * WEIGHTS["income"]    +
            school_score    * WEIGHTS["school"]    +
            transit_score   * WEIGHTS["transit"]   +
            price_score     * WEIGHTS["price"]     +
            size_score      * WEIGHTS["size"]      +
            lifestyle_score * WEIGHTS["lifestyle"]
        )
        return min(total, 100)

    # ── Nucleus (TTC, target 40) ─────────────────────────────────
    n_target = STRATEGIES["nucleus"]["transit_target"]
    n_transit_score, n_transit_min = _transit_score(transit_ttc, n_target, transit_est)
    total_nucleus = combine(n_transit_score) if eligible_nucleus else 0

    # ── Big Family (GO, target 75) ───────────────────────────────
    b_target = STRATEGIES["big_family"]["transit_target"]
    b_transit_score, b_transit_min = _transit_score(transit_go, b_target, transit_est)
    total_big_family = combine(b_transit_score) if eligible_big_family else 0

    return {
        # shared breakdown (same across strategies)
        "income_score":         round(income_score),
        "school_score":         round(school_score),
        "price_score":          round(price_score),
        "size_score":           round(size_score),
        "lifestyle_score":      round(lifestyle_score),
        "neighbourhood_income": income_raw,
        "school_rating":        school_raw,

        # transit measurements
        "transit_min_ttc":      n_transit_min,
        "transit_min_go":       b_transit_min,

        # nucleus
        "total_score_nucleus":     total_nucleus,
        "transit_score_nucleus":   n_transit_score,
        "eligible_nucleus":        eligible_nucleus,

        # big family
        "total_score_big_family":   total_big_family,
        "transit_score_big_family": b_transit_score,
        "eligible_big_family":      eligible_big_family,

        # legacy columns kept for backward compatibility (default to nucleus)
        "total_score":   total_nucleus,
        "transit_score": n_transit_score,
        "transit_min":   n_transit_min,
    }
