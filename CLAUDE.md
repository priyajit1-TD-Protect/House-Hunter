# GTA House Hunter — Full Stack Spec
> Next.js 14 (App Router) · Python FastAPI · Supabase · Realtor.ca scraper · TD Brand

---

## 1. The Story (what this actually does)

Sachi is hunting for a home in Toronto with tight criteria:
- Neighbourhood avg household income > $200K
- Elementary school Fraser score > 8
- Peak transit to Union Station < 40 min
- 1,500+ sqft · 3+ bed · 2+ bath
- Budget ≤ $1.7M
- Nice-to-have: tree canopy, rec facilities

The app:
1. Scrapes Realtor.ca every 6 hours for qualifying listings
2. Scores each listing (0–100) against the criteria above
3. Shows a filterable, sortable dashboard with deep listing cards
4. Links directly to the live Realtor.ca listing
5. Sends an email/push alert when a new listing scores > 75

---

## 2. Tech Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 14 (App Router, TypeScript) |
| Styling | Tailwind CSS + TD brand tokens |
| State | React hooks + SWR for data fetching |
| Backend API | Python FastAPI |
| Database | Supabase (Postgres + Realtime) |
| Scraper | Python httpx + APScheduler (runs inside FastAPI) |
| Scoring | Python service (scoring.py) |
| Notifications | Resend (email) or Supabase Edge Functions |
| Hosting | Vercel (frontend) + Railway (FastAPI) |

---

## 3. Folder Structure

```
gta-house-hunter/
├── CLAUDE.md                  ← you are here
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx           ← dashboard (listing cards, filters)
│   │   ├── api/
│   │   │   └── listings/
│   │   │       └── route.ts   ← proxy to FastAPI
│   │   └── listing/
│   │       └── [id]/
│   │           └── page.tsx   ← detail view
│   ├── components/
│   │   ├── ListingCard.tsx
│   │   ├── ScoreBar.tsx
│   │   ├── FilterBar.tsx
│   │   ├── InsightBanner.tsx
│   │   ├── StatsHeader.tsx
│   │   └── ScoreBreakdown.tsx
│   ├── lib/
│   │   ├── supabase.ts        ← Supabase browser client
│   │   └── types.ts           ← shared types
│   ├── hooks/
│   │   └── useListings.ts     ← SWR hook
│   ├── styles/
│   │   └── globals.css
│   ├── tailwind.config.ts     ← TD tokens registered here
│   └── .env.local
├── backend/
│   ├── main.py                ← FastAPI app + scheduler startup
│   ├── scraper.py             ← Realtor.ca scraper
│   ├── scoring.py             ← scoring engine
│   ├── notifier.py            ← email alerts via Resend
│   ├── models.py              ← Pydantic models
│   ├── db.py                  ← Supabase client
│   └── .env
└── supabase/
    └── migrations/
        └── 001_init.sql
```

---

## 4. Database Schema (`supabase/migrations/001_init.sql`)

```sql
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
  realtor_url       TEXT,                      -- direct link to realtor.ca listing
  img_url           TEXT,
  lat               NUMERIC(9,6),
  lng               NUMERIC(9,6),
  raw_json          JSONB,                     -- full Realtor.ca API response
  is_active         BOOLEAN DEFAULT true,
  created_at        TIMESTAMPTZ DEFAULT now(),
  updated_at        TIMESTAMPTZ DEFAULT now()
);

-- Scores table (separate so we can re-score without touching listing data)
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
  lifestyle_score   INTEGER,     -- 1-10: parks, canopy, rec
  keywords          TEXT[]       -- address keywords to match
);

-- Alerts log
CREATE TABLE alert_log (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  listing_id  TEXT REFERENCES listings(id),
  score       INTEGER,
  sent_at     TIMESTAMPTZ DEFAULT now(),
  channel     TEXT   -- 'email' | 'push'
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
```

---

## 5. Backend (`backend/`)

### `backend/scraper.py`

```python
"""
Realtor.ca internal API scraper.
Realtor.ca fires a POST to api2.realtor.ca from the browser — we replicate it.
No official API key needed; mimic the browser request exactly.
"""
import httpx
import asyncio
from datetime import date
from db import supabase_client
from scoring import score_listing

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.realtor.ca/",
    "Origin": "https://www.realtor.ca",
}

# GTA bounding box — covers Toronto proper + inner suburbs
SEARCH_PAYLOAD = {
    "CultureId": "1",
    "ApplicationId": "1",
    "PropertySearchTypeId": "1",   # Residential
    "PriceMin": "900000",
    "PriceMax": "1700000",
    "BedRange": "3-0",             # 3+ beds
    "BathRange": "2-0",            # 2+ baths
    "LongitudeMin": "-79.55",
    "LongitudeMax": "-79.20",
    "LatitudeMin": "43.62",
    "LatitudeMax": "43.78",
    "SortBy": "6",                 # Most recent
    "SortOrder": "descending",
    "RecordsPerPage": "50",
    "CurrentPage": "1",
    "PropertyTypeGroupID": "1",
}

def build_realtor_url(listing: dict) -> str:
    relative = listing.get("RelativeDetailsURL", "")
    return f"https://www.realtor.ca{relative}" if relative else "https://www.realtor.ca"

def extract_sqft(listing: dict) -> int | None:
    """Pull sqft from Building.SizeInterior if present."""
    try:
        size_str = listing["Building"]["SizeInterior"]
        # e.g. "1650 sqft" or "153.29 m2"
        val = float(size_str.split()[0].replace(",", ""))
        unit = size_str.split()[1].lower() if len(size_str.split()) > 1 else "sqft"
        return int(val * 10.764) if "m" in unit else int(val)
    except Exception:
        return None

async def scrape_and_upsert():
    """Main scrape job — call this from the scheduler."""
    sb = supabase_client()
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(REALTOR_API, data=SEARCH_PAYLOAD, headers=HEADERS)
        r.raise_for_status()
        results = r.json().get("Results", [])

    print(f"[scraper] fetched {len(results)} listings from Realtor.ca")

    for item in results:
        try:
            mls_id = item.get("MlsNumber", "")
            if not mls_id:
                continue

            price = int(item.get("Property", {}).get("PriceUnformatted", 0))
            address_obj = item.get("Property", {}).get("Address", {})
            address = address_obj.get("AddressText", "")
            beds = int(item.get("Building", {}).get("Bedrooms", 0) or 0)
            baths_raw = item.get("Building", {}).get("BathroomTotal", "0")
            baths = int(baths_raw) if baths_raw else 0
            sqft = extract_sqft(item)
            prop_type = item.get("Building", {}).get("Type", "")
            lat = float(item.get("Property", {}).get("Address", {}).get("Latitude", 0) or 0)
            lng = float(item.get("Property", {}).get("Address", {}).get("Longitude", 0) or 0)
            photo = (item.get("Property", {}).get("Photo") or [{}])[0].get("LowResPath", "")
            realtor_url = build_realtor_url(item)
            listed_str = item.get("InsertedDateUtc", "")[:10] if item.get("InsertedDateUtc") else None

            listing_row = {
                "id": mls_id,
                "address": address,
                "price": price,
                "beds": beds,
                "baths": baths,
                "sqft": sqft,
                "listing_type": prop_type,
                "listed_date": listed_str,
                "realtor_url": realtor_url,
                "img_url": photo,
                "lat": lat if lat else None,
                "lng": lng if lng else None,
                "raw_json": item,
                "is_active": True,
            }

            # Upsert listing
            sb.table("listings").upsert(listing_row).execute()

            # Score and upsert score
            score_result = score_listing(listing_row, sb)
            score_row = {"listing_id": mls_id, **score_result}
            sb.table("listing_scores").upsert(score_row, on_conflict="listing_id").execute()

        except Exception as e:
            print(f"[scraper] error on {item.get('MlsNumber')}: {e}")

    print("[scraper] done")
```

---

### `backend/scoring.py`

```python
"""
Scoring engine: 0–100 score per listing.
Weights: Income 25% · School 25% · Transit 20% · Price 15% · Size 10% · Lifestyle 5%
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

def match_neighbourhood(address: str, sb: Client) -> dict | None:
    """Match address to neighbourhood by keyword array."""
    rows = sb.table("neighbourhoods").select("*").execute().data
    address_lower = address.lower()
    for row in rows:
        for kw in (row.get("keywords") or []):
            if kw in address_lower:
                return row
    return None

def score_listing(listing: dict, sb: Client) -> dict:
    neigh = match_neighbourhood(listing.get("address", ""), sb)

    # ── Per-dimension scores (0–100) ─────────────────────────────
    if neigh:
        income_raw  = neigh.get("avg_income", 0)
        school_raw  = neigh.get("school_rating", 0)
        transit_raw = neigh.get("transit_min_union", 99)
        lifestyle_r = neigh.get("lifestyle_score", 5)
    else:
        income_raw, school_raw, transit_raw, lifestyle_r = 0, 0, 99, 5

    income_score   = min(100, (income_raw / 200_000) * 100)
    school_score   = min(100, (school_raw / 8.0) * 100)
    transit_score  = max(0, ((40 - transit_raw) / 40) * 100) if transit_raw <= 40 else 0
    price          = listing.get("price", 0)
    price_score    = max(0, min(100, ((BUDGET_MAX - price) / BUDGET_MAX) * 80 + 20)) if price <= BUDGET_MAX else 0
    sqft           = listing.get("sqft") or 0
    size_score     = min(100, ((sqft - 1500) / 1000) * 100 + 60) if sqft >= 1500 else (sqft / 1500) * 40
    lifestyle_score = (lifestyle_r / 10) * 100

    total = round(
        income_score   * WEIGHTS["income"]  +
        school_score   * WEIGHTS["school"]  +
        transit_score  * WEIGHTS["transit"] +
        price_score    * WEIGHTS["price"]   +
        size_score     * WEIGHTS["size"]    +
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
```

---

### `backend/main.py`

```python
import os
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from scraper import scrape_and_upsert
from notifier import notify_high_scores
from db import supabase_client

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run immediately on boot, then every 6 hours
    asyncio.create_task(scrape_and_upsert())
    scheduler.add_job(scrape_and_upsert, "interval", hours=6, id="scrape")
    scheduler.add_job(notify_high_scores, "interval", hours=6, id="notify")
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(title="GTA House Hunter API", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

sb = supabase_client()

@app.get("/api/listings")
def get_listings(
    max_price: int = Query(1_700_000),
    min_score: int = Query(0),
    neighbourhood: str = Query(None),
    sort_by: str = Query("score"),        # score | price_asc | price_desc | transit | school
    limit: int = Query(50),
):
    # Join listings + scores in one query
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

    # Filter by min_score (can't do in Supabase join filter easily)
    rows = [r for r in rows if (r.get("listing_scores") or [{}])[0].get("total_score", 0) >= min_score]

    # Sort
    def sort_key(r):
        s = (r.get("listing_scores") or [{}])[0]
        if sort_by == "price_asc":  return r.get("price", 0)
        if sort_by == "price_desc": return -r.get("price", 0)
        if sort_by == "transit":    return s.get("transit_min", 99)
        if sort_by == "school":     return -s.get("school_rating", 0)
        return -s.get("total_score", 0)   # default: score desc

    return sorted(rows, key=sort_key)

@app.post("/api/scrape")
async def trigger_scrape():
    """Manual trigger for testing."""
    asyncio.create_task(scrape_and_upsert())
    return {"status": "scrape started"}

@app.get("/api/neighbourhoods")
def get_neighbourhoods():
    return sb.table("neighbourhoods").select("*").execute().data

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

### `backend/db.py`

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")
    return create_client(url, key)
```

---

### `backend/notifier.py`

```python
"""
Sends email alert via Resend when new listings score >= 75.
Only fires once per listing (checks alert_log).
"""
import os, resend
from db import supabase_client

ALERT_THRESHOLD = 75
ALERT_EMAIL = os.getenv("ALERT_EMAIL", "sachi@example.com")

def notify_high_scores():
    sb = supabase_client()

    # Get high-scoring listings not yet alerted
    alerted_ids = {r["listing_id"] for r in sb.table("alert_log").select("listing_id").execute().data}

    rows = (
        sb.table("listings")
        .select("*, listing_scores(*)")
        .eq("is_active", True)
        .execute().data
    )

    for row in rows:
        score = (row.get("listing_scores") or [{}])[0].get("total_score", 0)
        if score >= ALERT_THRESHOLD and row["id"] not in alerted_ids:
            _send_alert(row, score)
            sb.table("alert_log").insert({"listing_id": row["id"], "score": score, "channel": "email"}).execute()

def _send_alert(listing: dict, score: int):
    resend.api_key = os.getenv("RESEND_API_KEY")
    resend.Emails.send({
        "from": "househunter@yourdomain.com",
        "to": ALERT_EMAIL,
        "subject": f"🏠 New Match: {listing['address']} — Score {score}/100",
        "html": f"""
            <h2>New listing matches your criteria</h2>
            <p><strong>{listing['address']}</strong></p>
            <p>Price: ${listing['price']:,} · Score: {score}/100</p>
            <a href="{listing['realtor_url']}">View on Realtor.ca →</a>
        """,
    })
```

---

### `backend/.env`

```
SUPABASE_URL=https://pwvudqwxijxpiajnrjyi.supabase.co
SUPABASE_SERVICE_KEY=your_service_key_here
RESEND_API_KEY=your_resend_key_here
ALERT_EMAIL=your_email@gmail.com
```

### `backend/requirements.txt`

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
httpx==0.27.0
supabase==2.4.2
apscheduler==3.10.4
python-dotenv==1.0.1
resend==0.7.0
pydantic==2.7.1
```

---

## 6. Frontend (`frontend/`)

### `frontend/lib/types.ts`

```typescript
export interface ListingScore {
  total_score: number;
  income_score: number;
  school_score: number;
  transit_score: number;
  price_score: number;
  size_score: number;
  lifestyle_score: number;
  neighbourhood_income: number;
  school_rating: number;
  transit_min: number;
}

export interface Listing {
  id: string;
  address: string;
  neighbourhood: string;
  price: number;
  beds: number;
  baths: number;
  sqft: number;
  listing_type: string;
  listed_date: string;
  realtor_url: string;
  img_url: string;
  is_active: boolean;
  listing_scores: ListingScore[];
}
```

---

### `frontend/lib/supabase.ts`

```typescript
import { createBrowserClient } from "@supabase/ssr";

export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
);
```

---

### `frontend/hooks/useListings.ts`

```typescript
import useSWR from "swr";
import { Listing } from "@/lib/types";

const fetcher = (url: string) => fetch(url).then(r => r.json());

export function useListings(params: {
  maxPrice?: number;
  minScore?: number;
  neighbourhood?: string;
  sortBy?: string;
}) {
  const qs = new URLSearchParams({
    max_price: String(params.maxPrice ?? 1700000),
    min_score: String(params.minScore ?? 0),
    sort_by: params.sortBy ?? "score",
    ...(params.neighbourhood && params.neighbourhood !== "All"
      ? { neighbourhood: params.neighbourhood }
      : {}),
  });

  const { data, error, isLoading, mutate } = useSWR<Listing[]>(
    `/api/listings?${qs}`,
    fetcher,
    { refreshInterval: 30_000 }   // auto-refresh every 30s
  );

  return { listings: data ?? [], error, isLoading, mutate };
}
```

---

### `frontend/app/api/listings/route.ts`

```typescript
// Proxy to FastAPI — keeps backend URL secret from the browser
import { NextRequest, NextResponse } from "next/server";

const API = process.env.FASTAPI_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  const res = await fetch(`${API}/api/listings?${qs}`, { next: { revalidate: 60 } });
  const data = await res.json();
  return NextResponse.json(data);
}
```

---

### `frontend/tailwind.config.ts` — TD tokens

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        td: {
          premiumGreen: "#002B1A",
          digitalGreen: "#008A00",
          gold:         "#CFBD91",
          grey:         "#EFEDEE",
          greenGrey:    "#708573",
          darkGrey:     "#515B52",
          nearBlack:    "#1C1C1C",
          insightBg:    "#F0F7F0",
          lightGreen:   "#C8E6C9",
          lightRed:     "#FFEBEE",
        },
      },
      fontFamily: {
        display: ["Arial Black", "Arial", "sans-serif"],
        body:    ["Arial", "Calibri", "sans-serif"],
      },
    },
  },
  plugins: [],
};
export default config;
```

---

### Key components to build

**`ListingCard.tsx`**
- Listing image with score badge overlay (top-left) and tier pill (top-right: STRONG MATCH / GOOD FIT / REVIEW)
- Address, type, price (large), bed/bath/sqft chips
- Neighbourhood signal row: 🏫 School X/10 · 🚇 X min to Union · 💰 $XXXk income
- Tag pills (Renovated, Parking, etc.)
- Expandable score breakdown with mini bars (one per dimension)
- Footer: [View on Realtor.ca ↗] button + Listed date

**`FilterBar.tsx`**
- Neighbourhood dropdown
- Sort dropdown (Score · Price ↑ · Price ↓ · Transit · School)
- Max price slider ($900K–$1.7M)
- Min score slider (0–100)
- Active listing count

**`StatsHeader.tsx`** — TD dark green header bar
- Title + subtitle (criteria summary)
- Stat tiles: Active Listings / Avg Score / Best Score / Price Range
- Last synced timestamp + Live indicator
- [Trigger Scrape] button (dev only) → POST /api/scrape

**`InsightBanner.tsx`**
- Always shows top match with quick stats

**`ScoreBreakdown.tsx`**
- Collapsible section inside each card
- 6 dimension bars (Income / School / Transit / Price / Size / Lifestyle)
- Label + weight % + value + colored fill bar

---

## 7. Key Environment Variables

### `frontend/.env.local`
```
NEXT_PUBLIC_SUPABASE_URL=https://pwvudqwxijxpiajnrjyi.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
FASTAPI_URL=http://localhost:8000
```

---

## 8. Bootstrap Commands

```bash
# 1. Create Next.js app
npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir
cd frontend && npm install swr @supabase/ssr

# 2. Python backend
cd ../backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 3. Run Supabase migration
# Paste supabase/migrations/001_init.sql into Supabase SQL editor

# 4. Dev
# Terminal 1: cd frontend && npm run dev
# Terminal 2: cd backend && uvicorn main:app --reload --port 8000
```

---

## 9. Build Order (weekend plan)

### Saturday morning
- [ ] Run bootstrap commands
- [ ] Apply SQL migration in Supabase
- [ ] Verify `scraper.py` hits Realtor.ca and upserts rows
- [ ] Verify `scoring.py` scores rows correctly
- [ ] `GET /api/listings` returns joined data

### Saturday afternoon
- [ ] Build `StatsHeader`, `FilterBar`, `ListingCard` (static mock data)
- [ ] Wire `useListings` hook → real FastAPI data
- [ ] Score breakdown expand/collapse working

### Sunday
- [ ] `InsightBanner` with top match
- [ ] Sort + filter working end-to-end
- [ ] Email alert via Resend on score ≥ 75
- [ ] Deploy: Vercel (frontend) + Railway (FastAPI)
- [ ] Set up Railway cron environment so scraper fires every 6h in prod

---

## 10. Realtor.ca API Notes

The endpoint `https://api2.realtor.ca/Listing.svc/PropertySearch_Post` is the undocumented internal API Realtor.ca's own site uses. It returns JSON with full listing data including `RelativeDetailsURL` — append to `https://www.realtor.ca` for the direct listing link.

Key response fields:
- `MlsNumber` → use as primary key
- `Property.PriceUnformatted` → integer price
- `Property.Address.AddressText` → full address string
- `RelativeDetailsURL` → path for direct link
- `Building.Bedrooms`, `Building.BathroomTotal`, `Building.SizeInterior`
- `Property.Photo[0].LowResPath` → thumbnail URL

Pagination: increment `CurrentPage`. Run pages 1–3 to capture 150 listings (plenty for GTA midtown).

If Realtor.ca blocks the request (they occasionally update headers), check browser DevTools Network tab on realtor.ca → filter for `PropertySearch_Post` → copy the exact request headers and form body.
