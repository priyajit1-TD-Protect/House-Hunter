# Data Loaders

One-time scripts to populate the reference tables the enrichment pipeline reads.
Run locally with your Supabase env vars set (same `.env` as the backend).

## Schools (Fraser Institute ratings)

A starter file covering all mapped neighbourhoods is included — load it now:

```bash
cd backend
python loaders/load_schools.py --csv loaders/schools_starter.csv --replace
```

To expand coverage: build your own CSV with columns
`name,fraser_rating,city,lat,lng,keywords` (keywords pipe-separated), pulling
ratings from https://www.compareschoolrankings.org — then load with the same
command pointing at your file.

## Census income (StatCan 2021, DA-level)

Download two free files from StatCan once:

1. **DA Census Profile** (contains income) — 98-401-X2021006, CSV, Ontario DAs
   https://www12.statcan.gc.ca/census-recensement/2021/dp-pd/prof/details/download-telecharger.cfm
2. **Geographic Attribute File** (DA centroids: DAuid, lat, lng)
   https://open.canada.ca/data/en/dataset/1b3653d7-a48e-4001-8046-e6964bebe286

Then:

```bash
cd backend
python loaders/load_census_income.py \
  --profile /path/to/da_profile.csv \
  --gaf /path/to/gaf.csv \
  --gta-only
```

`--gta-only` keeps just Toronto/Peel/York/Halton/Durham to keep the table small.

## Order

Run **schools** and **census** before the next scrape. The scraper's
completeness gate uses them; without them, only listings inside your mapped
neighbourhood table survive (income/school fall back to that table).
