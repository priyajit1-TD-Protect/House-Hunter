"""
Load Fraser Institute elementary school ratings into the `schools` table.

Fraser doesn't publish a clean bulk CSV, so this loader takes a SIMPLE CSV that
you assemble (from compareschoolrankings.org) with these columns:

  name,fraser_rating,city,lat,lng,keywords

  - keywords: pipe-separated catchment street/area hints, e.g. "davisville|balliol"
  - lat/lng optional (nearest-school matching works if present)

USAGE:
  python load_schools.py --csv schools.csv

A starter file (schools_starter.csv) is included covering the mapped
neighbourhoods so the pipeline works immediately.

Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY in env.
"""
import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import supabase_client


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="schools CSV path")
    ap.add_argument("--replace", action="store_true",
                    help="delete existing rows before loading")
    args = ap.parse_args()

    sb = supabase_client()
    if args.replace:
        # delete all — Supabase requires a filter, so use a always-true one
        sb.table("schools").delete().neq("id", -1).execute()
        print("[schools] cleared existing rows")

    rows = []
    with open(args.csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            kw = (r.get("keywords") or "").strip()
            keywords = [k.strip().lower() for k in kw.split("|") if k.strip()]
            def num(v):
                v = (v or "").strip()
                return float(v) if v else None
            rows.append({
                "name": (r.get("name") or "").strip(),
                "fraser_rating": num(r.get("fraser_rating")),
                "city": (r.get("city") or "").strip() or None,
                "lat": num(r.get("lat")),
                "lng": num(r.get("lng")),
                "keywords": keywords,
            })

    if rows:
        sb.table("schools").insert(rows).execute()
    print(f"[schools] loaded {len(rows)} schools")


if __name__ == "__main__":
    main()
