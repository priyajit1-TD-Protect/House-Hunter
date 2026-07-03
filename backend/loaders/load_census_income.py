"""
Load StatCan 2021 census DA-level median household income into the
`census_income` table (da_id, avg_income, lat, lng).

WHY THIS SHAPE: StatCan's DA profile CSV is transposed — each DA has many rows
keyed by "Characteristic", not one row per DA. We pull the income row and join
to DA centroid coordinates from the Geographic Attribute File (GAF).

INPUTS (both free from StatCan, download once):
  1. --profile   DA profile CSV containing income by DA
                 (98-401-X2021006 or the DA-level Census Profile download)
  2. --gaf       Geographic Attribute File CSV with DA representative points
                 (DAuid, DArplat, DArplong)

USAGE:
  python load_census_income.py --profile profile.csv --gaf gaf.csv \
      [--income-label "Median total income of household in 2020 ($)"] \
      [--gta-only]

Requires: SUPABASE_URL and SUPABASE_SERVICE_KEY in env (same as the app).
"""
import argparse
import csv
import os
import sys

# Make the app's db.py importable when run from loaders/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import supabase_client

# GTA census division prefixes (DAuid starts with these) — Toronto, Peel,
# York, Halton, Durham. Used when --gta-only is set to keep the table small.
GTA_CD_PREFIXES = ("3520", "3521", "3519", "3524", "3518")

DEFAULT_INCOME_LABEL = "Median total income of household in 2020 ($)"


def load_centroids(gaf_path: str) -> dict[str, tuple[float, float]]:
    """Map DAuid -> (lat, lng) from the Geographic Attribute File."""
    centroids: dict[str, tuple[float, float]] = {}
    with open(gaf_path, newline="", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        # Column names vary by release; find the right ones case-insensitively
        cols = {c.lower(): c for c in reader.fieldnames or []}
        da_col  = next((cols[c] for c in cols if c in ("dauid", "da_uid", "dauid/aduid")), None)
        lat_col = next((cols[c] for c in cols if "rplat" in c or c == "latitude"), None)
        lng_col = next((cols[c] for c in cols if "rplong" in c or c == "longitude"), None)
        if not (da_col and lat_col and lng_col):
            print(f"[census] GAF columns not found. Available: {reader.fieldnames}")
            return centroids
        for row in reader:
            da = (row.get(da_col) or "").strip()
            try:
                lat = float(row[lat_col]); lng = float(row[lng_col])
            except (ValueError, TypeError, KeyError):
                continue
            if da:
                centroids[da] = (lat, lng)
    print(f"[census] loaded {len(centroids)} DA centroids")
    return centroids


def parse_income(profile_path: str, income_label: str) -> dict[str, int]:
    """Map DAuid -> median household income from the transposed profile CSV."""
    incomes: dict[str, int] = {}
    current_da = None
    with open(profile_path, newline="", encoding="latin-1") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue
            joined = ",".join(row)
            # A DA header line contains e.g. "35204311 [Dissemination area]"
            if "[Dissemination area]" in joined:
                # find the numeric DAuid token
                for cell in row:
                    token = cell.strip().strip('"')
                    digits = token.split()[0] if token else ""
                    if digits.isdigit() and len(digits) >= 8:
                        current_da = digits
                        break
                continue
            # Income characteristic row
            if current_da and income_label.lower() in joined.lower():
                # value is the first numeric-looking cell after the label
                for cell in row:
                    val = cell.strip().strip('"').replace(",", "")
                    if val.isdigit():
                        incomes[current_da] = int(val)
                        break
    print(f"[census] parsed income for {len(incomes)} DAs")
    return incomes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, help="DA profile CSV path")
    ap.add_argument("--gaf", required=True, help="Geographic Attribute File CSV path")
    ap.add_argument("--income-label", default=DEFAULT_INCOME_LABEL)
    ap.add_argument("--gta-only", action="store_true")
    args = ap.parse_args()

    centroids = load_centroids(args.gaf)
    incomes = parse_income(args.profile, args.income_label)

    sb = supabase_client()
    batch, inserted = [], 0
    for da, income in incomes.items():
        if args.gta_only and not da.startswith(GTA_CD_PREFIXES):
            continue
        latlng = centroids.get(da)
        if not latlng:
            continue
        batch.append({
            "da_id": da,
            "avg_income": income,
            "lat": latlng[0],
            "lng": latlng[1],
        })
        if len(batch) >= 500:
            sb.table("census_income").upsert(batch).execute()
            inserted += len(batch)
            batch = []
    if batch:
        sb.table("census_income").upsert(batch).execute()
        inserted += len(batch)

    print(f"[census] inserted {inserted} DA income rows")


if __name__ == "__main__":
    main()
