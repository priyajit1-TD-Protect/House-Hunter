# GTA House Hunter

Smart Toronto home search scored by income, schools, and transit.

## Quick Start

### 1. Database

Paste `supabase/migrations/001_init.sql` into the Supabase SQL editor.

### 2. Backend

```bash
cd backend
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_SERVICE_KEY, RESEND_API_KEY, ALERT_EMAIL

python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API starts, immediately triggers a scrape, then runs every 6 hours.

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
# Fill in Supabase anon key

npm install
npm run dev
```

Open http://localhost:3000

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/listings` | Filtered + sorted listings |
| GET | `/api/listings/{id}` | Single listing detail |
| GET | `/api/stats` | Dashboard stats |
| GET | `/api/neighbourhoods` | Neighbourhood reference data |
| POST | `/api/scrape` | Manual scrape trigger (dev) |
| GET | `/health` | Health check |

**Query params for `/api/listings`:**
- `max_price` (default: 1700000)
- `min_score` (default: 0)
- `neighbourhood` (optional)
- `sort_by`: `score` | `price_asc` | `price_desc` | `transit` | `school`
- `limit` (default: 50)

---

## Scoring Weights

| Dimension | Weight | Criteria |
|---|---|---|
| Neighbourhood income | 25% | >$200K target |
| School rating | 25% | Fraser >8 target |
| Transit to Union | 20% | <40 min target |
| Price vs budget | 15% | ≤$1.7M |
| Size | 10% | 1,500+ sqft |
| Lifestyle | 5% | Parks, canopy, rec |

---

## Deploy

- **Frontend** → Vercel: `vercel --prod` from `/frontend`
- **Backend** → Railway: connect the `/backend` directory, set env vars, done
- Set `FRONTEND_URL` in Railway env to your Vercel URL
