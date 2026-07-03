"""
Scoring engine: 0–100 score per listing.
Weights: Income 25% · School 25% · Transit 20% · Price 15% · Size 10% · Lifestyle 5%

Transit uses real Google Distance Matrix minutes when available (passed in via
`transit_min_override`), falling back to the neighbourhood table estimate.
"""
from supabase import Client

WEIGHTS = {
    "income":    0.25,
    "school":    0.25,
    "transit":   0.20,
    "price":     0.15,
    "size":      0.10,
    "lifestyle": 0.05,
}

BUDGET_MAX = 1_700_000
TRANSIT_TARGET_MIN = 40   # criterion: under 40 min to Union


def match_neighbourhood(address: str, sb: Client) -> dict | None:
    """Match address to neighbourhood by keyword array."""
    rows = sb.table("neighbourhoods").select("*").execute().data
    address_lower = address.lower()
    for row in rows:
        for kw in (row.get("keywords") or []):
            if kw in address_lower:
                return row
    return None


def score_listing(listing: dict, sb: Client, transit_min_override: int | None = None) -> dict:
    neigh = match_neighbourhood(listing.get("address", ""), sb)

    if neigh:
        income_raw  = neigh.get("avg_income", 0)
        school_raw  = neigh.get("school_rating", 0)
        transit_est = neigh.get("transit_min_union", 99)
        lifestyle_r = neigh.get("lifestyle_score", 5)
    else:
        income_raw, school_raw, transit_est, lifestyle_r = 0, 0, 99, 5

    # Use real transit time if we have it, else fall back to neighbourhood estimate
    transit_raw = transit_min_override if transit_min_override is not None else transit_est

    # ── Per-dimension scores (0–100) ─────────────────────────────
    income_score = min(100, (income_raw / 200_000) * 100)
    school_score = min(100, (school_raw / 8.0) * 100)

    # Transit: full marks near 0 min, 0 marks at/over 40 min. Over-40 still shown
    # but scores 0 on this dimension (per requirement).
    if transit_raw <= TRANSIT_TARGET_MIN:
        transit_score = max(0, ((TRANSIT_TARGET_MIN - transit_raw) / TRANSIT_TARGET_MIN) * 100)
    else:
        transit_score = 0

    price = listing.get("price", 0)
    price_score = max(0, min(100, ((BUDGET_MAX - price) / BUDGET_MAX) * 80 + 20)) if price <= BUDGET_MAX else 0

    sqft = listing.get("sqft") or 0
    size_score = min(100, ((sqft - 1500) / 1000) * 100 + 60) if sqft >= 1500 else (sqft / 1500) * 40

    lifestyle_score = (lifestyle_r / 10) * 100

    total = round(
        income_score    * WEIGHTS["income"]    +
        school_score    * WEIGHTS["school"]    +
        transit_score   * WEIGHTS["transit"]   +
        price_score     * WEIGHTS["price"]     +
        size_score      * WEIGHTS["size"]      +
        lifestyle_score * WEIGHTS["lifestyle"]
    )

    return {
        "total_score":          min(total, 100),
        "income_score":         round(income_score),
        "school_score":         round(school_score),
        "transit_score":        round(transit_score),
        "price_score":          round(price_score),
        "size_score":           round(size_score),
        "lifestyle_score":      round(lifestyle_score),
        "neighbourhood_income": income_raw,
        "school_rating":        school_raw,
        "transit_min":          transit_raw,
    }
