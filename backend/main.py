import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scraper import scrape_and_upsert
from notifier import notify_high_scores
from db import supabase_client

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run scrape immediately on boot, then every 12 hours
    asyncio.create_task(scrape_and_upsert())
    scheduler.add_job(scrape_and_upsert, "interval", hours=12, id="scrape")
    scheduler.add_job(notify_high_scores, "interval", hours=12, id="notify")
    scheduler.start()
    yield
    scheduler.shutdown()


app = FastAPI(title="GTA House Hunter API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

sb = supabase_client()


@app.get("/api/listings")
def get_listings(
    max_price: int = Query(1_700_000),
    min_score: int = Query(0),
    neighbourhood: str = Query(None),
    sort_by: str = Query("score"),   # score | price_asc | price_desc | transit | school
    strategy: str = Query("nucleus"),  # nucleus | big_family
    limit: int = Query(50),
):
    if strategy not in ("nucleus", "big_family"):
        strategy = "nucleus"

    score_col   = f"total_score_{strategy}"
    elig_col    = f"eligible_{strategy}"
    transit_col = "transit_min_ttc" if strategy == "nucleus" else "transit_min_go"

    query = (
        sb.table("listings")
        .select("*, listing_scores(*)")
        .eq("is_active", True)
        .lte("price", max_price)
        .limit(limit)
    )
    if neighbourhood and neighbourhood != "All":
        query = query.eq("neighbourhood", neighbourhood)

    rows = query.execute().data

    # Normalize listing_scores to a list
    for r in rows:
        scores = r.get("listing_scores")
        if isinstance(scores, dict):
            r["listing_scores"] = [scores]
        elif not scores:
            r["listing_scores"] = [{}]

    def strat_score(r):
        return r["listing_scores"][0].get(score_col, 0) or 0

    def is_eligible(r):
        return bool(r["listing_scores"][0].get(elig_col, False))

    def within_transit(r):
        # Hide-until-measured: require a known transit time within the ceiling.
        # Nucleus TTC <=60, Big Family GO <=75. Unknown (None) is NOT shown.
        t = r["listing_scores"][0].get(transit_col)
        ceiling = 60 if strategy == "nucleus" else 75
        return t is not None and t <= ceiling

    def not_suppressed(r):
        addr = (r.get("address") or "").lower()
        return "brampton" not in addr

    # Only listings eligible for the active strategy, above min_score,
    # within the transit cap, and not in a suppressed city.
    rows = [
        r for r in rows
        if is_eligible(r)
        and strat_score(r) >= min_score
        and within_transit(r)
        and not_suppressed(r)
    ]

    # Expose the active strategy's values as the canonical fields the frontend
    # already reads (total_score, transit_min), so the UI needs no rewiring.
    for r in rows:
        s = r["listing_scores"][0]
        s["total_score"] = strat_score(r)
        s["transit_min"] = s.get(transit_col, 99)
        s["transit_score"] = s.get(f"transit_score_{strategy}", 0)
        s["active_strategy"] = strategy

    def sort_key(r):
        s = r["listing_scores"][0]
        if sort_by == "price_asc":  return r.get("price", 0)
        if sort_by == "price_desc": return -r.get("price", 0)
        if sort_by == "transit":    return s.get("transit_min", 99)
        if sort_by == "school":     return -(s.get("school_rating", 0) or 0)
        return -strat_score(r)

    return sorted(rows, key=sort_key)


@app.get("/api/listings/{listing_id}")
def get_listing(listing_id: str):
    result = (
        sb.table("listings")
        .select("*, listing_scores(*)")
        .eq("id", listing_id)
        .single()
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Listing not found")
    return result.data


@app.get("/api/stats")
def get_stats(strategy: str = Query("nucleus")):
    """Aggregate stats for the dashboard header, for the active strategy."""
    if strategy not in ("nucleus", "big_family"):
        strategy = "nucleus"
    score_col = f"total_score_{strategy}"
    elig_col  = f"eligible_{strategy}"

    rows = (
        sb.table("listings")
        .select(f"price, listing_scores({score_col}, {elig_col})")
        .eq("is_active", True)
        .execute()
        .data
    )

    def score_of(r):
        s = r.get("listing_scores")
        if isinstance(s, list):
            s = s[0] if s else {}
        return (s or {}).get(score_col, 0) or 0

    def eligible(r):
        s = r.get("listing_scores")
        if isinstance(s, list):
            s = s[0] if s else {}
        return bool((s or {}).get(elig_col, False))

    eligible_rows = [r for r in rows if eligible(r)]
    scores = [score_of(r) for r in eligible_rows]
    prices = [r["price"] for r in eligible_rows]

    return {
        "active_count": len(eligible_rows),
        "avg_score": round(sum(scores) / len(scores)) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
        "strategy": strategy,
    }


@app.get("/api/neighbourhoods")
def get_neighbourhoods():
    return sb.table("neighbourhoods").select("*").order("name").execute().data


@app.post("/api/scrape")
async def trigger_scrape():
    """Manual trigger for dev/testing."""
    asyncio.create_task(scrape_and_upsert())
    return {"status": "scrape started"}


@app.get("/health")
def health():
    return {"status": "ok"}
