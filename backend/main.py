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
    # Run scrape immediately on boot, then every 6 hours
    asyncio.create_task(scrape_and_upsert())
    scheduler.add_job(scrape_and_upsert, "interval", hours=6, id="scrape")
    scheduler.add_job(notify_high_scores, "interval", hours=6, id="notify")
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
    limit: int = Query(50),
):
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

    # Normalize listing_scores — Supabase may return dict or list
    for r in rows:
        scores = r.get("listing_scores")
        if isinstance(scores, dict):
            r["listing_scores"] = [scores]
        elif not scores:
            r["listing_scores"] = [{}]

    # Filter by min_score
    rows = [
        r for r in rows
        if r["listing_scores"][0].get("total_score", 0) >= min_score
    ]

    def sort_key(r):
        s = r["listing_scores"][0]
        if sort_by == "price_asc":  return r.get("price", 0)
        if sort_by == "price_desc": return -r.get("price", 0)
        if sort_by == "transit":    return s.get("transit_min", 99)
        if sort_by == "school":     return -s.get("school_rating", 0)
        return -s.get("total_score", 0)

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
def get_stats():
    """Aggregate stats for the dashboard header."""
    rows = (
        sb.table("listings")
        .select("price, listing_scores(total_score)")
        .eq("is_active", True)
        .execute()
        .data
    )
    scores = [
        (r.get("listing_scores") or [{}])[0].get("total_score", 0)
        for r in rows
    ]
    prices = [r["price"] for r in rows]

    return {
        "active_count": len(rows),
        "avg_score": round(sum(scores) / len(scores)) if scores else 0,
        "best_score": max(scores) if scores else 0,
        "min_price": min(prices) if prices else 0,
        "max_price": max(prices) if prices else 0,
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
