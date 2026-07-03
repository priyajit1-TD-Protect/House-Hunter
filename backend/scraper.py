"""
Realtor.ca scraper via ScraperAPI async jobs endpoint.
Filters for freehold only: Detached, Semi-Detached, Townhouse (freehold).
"""
import httpx
import asyncio
import os
import json
import urllib.parse
from db import supabase_client
from scoring import score_all_strategies
from strategies import is_eligible_for
from transit import TransitLookup

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
SCRAPER_API_ENDPOINT = "https://async.scraperapi.com/jobs"

# Freehold property types to keep (Detached, Semi-Detached, Townhouse, freehold House)
FREEHOLD_TYPES = {
    "house", "detached", "semi-detached", "semi detached",
    "townhouse", "row / townhouse", "att/row/twnhouse",
    "row/townhouse", "link",
}

BASE_PAYLOAD = {
    "CultureId": "1",
    "ApplicationId": "1",
    "PropertySearchTypeId": "1",   # Residential
    "PriceMin": "1000000",
    "PriceMax": "1700000",
    "BedRange": "3-5",
    "BathRange": "2-4",
    # Wider GTA box: covers Toronto + Oakville, Mississauga, Etobicoke, Richmond Hill.
    # Nucleus naturally stays central (TTC <40 scoring); Big Family uses the full area.
    "LongitudeMin": "-79.85",   # west: Oakville / Mississauga
    "LongitudeMax": "-79.30",   # east
    "LatitudeMin": "43.40",     # south: Oakville lakeshore
    "LatitudeMax": "43.95",     # north: Richmond Hill
    "SortBy": "6",
    "RecordsPerPage": "50",
    "CurrentPage": "1",
    "PropertyTypeGroupID": "1",
    "TransactionTypeId": "2",      # For Sale
}

REALTOR_HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-CA,en;q=0.9",
    "Referer": "https://www.realtor.ca/",
    "Origin": "https://www.realtor.ca",
    "X-Requested-With": "XMLHttpRequest",
}


def build_realtor_url(listing: dict) -> str:
    relative = listing.get("RelativeDetailsURL", "")
    return f"https://www.realtor.ca{relative}" if relative else "https://www.realtor.ca"


def extract_sqft(listing: dict) -> int | None:
    try:
        size_str = listing.get("Building", {}).get("SizeInterior", "")
        if not size_str:
            return None
        val = float(size_str.split()[0].replace(",", ""))
        unit = size_str.split()[1].lower() if len(size_str.split()) > 1 else "sqft"
        return int(val * 10.764) if "m" in unit else int(val)
    except Exception:
        return None


def parse_int_field(value) -> int:
    """Parse fields like '2 + 1' or '3' into integers (sums all parts)."""
    if not value:
        return 0
    try:
        return int(value)
    except (ValueError, TypeError):
        try:
            return sum(int(x.strip()) for x in str(value).split("+"))
        except Exception:
            return 0


def parse_price(item: dict) -> int:
    """Extract price. Realtor.ca 2026 API uses Property.PriceUnformattedValue
    (clean integer) and Property.Price (formatted '$1,600,000')."""
    prop = item.get("Property", {})

    raw = prop.get("PriceUnformattedValue")
    if raw not in (None, "", "0"):
        try:
            return int(str(raw).replace(",", "").replace("$", "").strip())
        except Exception:
            pass

    price_str = prop.get("Price", "")
    if price_str:
        import re
        digits = re.sub(r"[^\d]", "", price_str)
        if digits:
            return int(digits)

    return 0


def is_freehold(item: dict) -> bool:
    """Return True for freehold Detached / Semi-Detached / Townhouse.
    Realtor.ca 2026: ownership is in Property.OwnershipType, type in
    Property.Type and Building.Type."""
    prop = item.get("Property", {})
    building = item.get("Building", {})

    ownership = (prop.get("OwnershipType") or "").lower()
    prop_type = (prop.get("Type") or "").lower().strip()
    building_type = (building.get("Type") or "").lower().strip()

    combined = f"{prop_type} {building_type}"

    # Exclude condo/strata ownership outright
    if "condo" in ownership or "strata" in ownership:
        return False
    if "condo" in combined or "apartment" in combined:
        return False

    # Freehold ownership + a house/townhouse/semi type
    if "freehold" in ownership:
        return True

    # Accept known freehold building types even if ownership blank
    for ft in FREEHOLD_TYPES:
        if ft in combined:
            return True

    return False


def infer_neighbourhood(address: str, sb) -> str | None:
    rows = sb.table("neighbourhoods").select("name, keywords").execute().data
    address_lower = address.lower()
    for row in rows:
        for kw in (row.get("keywords") or []):
            if kw in address_lower:
                return row["name"]
    return None


async def scrape_page_via_scraperapi(client: httpx.AsyncClient, page: int) -> list[dict]:
    payload = {**BASE_PAYLOAD, "CurrentPage": str(page)}
    body = urllib.parse.urlencode(payload)

    job_payload = {
        "apiKey": SCRAPER_API_KEY,
        "url": REALTOR_API,
        "method": "POST",
        "body": body,
        "headers": REALTOR_HEADERS,
        "countryCode": "ca",
        "premium": True,
        "keepHeaders": True,
    }

    try:
        r = await client.post(SCRAPER_API_ENDPOINT, json=job_payload, timeout=30)
        print(f"[scraper] job submit status: {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"[scraper] job submit failed: {r.text[:300]}")
            return []

        job = r.json()
        job_id = job.get("id")
        status_url = job.get("statusUrl")
        print(f"[scraper] job {job_id} submitted, polling...")

        for attempt in range(30):
            await asyncio.sleep(3)
            status_r = await client.get(status_url, timeout=15)
            status_data = status_r.json()
            status = status_data.get("status")
            print(f"[scraper] job {job_id} status: {status} (attempt {attempt+1})")

            if status == "finished":
                response_body = status_data.get("response", {}).get("body", "")
                try:
                    data = json.loads(response_body)
                    results = data.get("Results", [])
                    print(f"[scraper] page {page}: {len(results)} raw listings")
                    return results
                except Exception as e:
                    print(f"[scraper] JSON parse error: {e}")
                    return []
            elif status == "failed":
                print(f"[scraper] job failed")
                return []

        print(f"[scraper] job timed out")
        return []

    except Exception as e:
        print(f"[scraper] ScraperAPI error page {page}: {e}")
        return []


async def scrape_and_upsert():
    """Main scrape job — called on startup and every 6 hours."""
    sb = supabase_client()
    all_results = []

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        # Wider area now spans 4 regions — pull up to 6 pages (300 listings)
        for page in range(1, 7):
            results = await scrape_page_via_scraperapi(client, page)
            all_results.extend(results)
            if len(results) < 50:
                break
            await asyncio.sleep(2)

    print(f"[scraper] total raw: {len(all_results)} listings")

    # Keep anything eligible for EITHER strategy (the union). Per-strategy
    # eligibility is computed below and stored so the API can filter.
    def eligible_either(item):
        prop = item.get("Property", {})
        building = item.get("Building", {})
        ptype = prop.get("Type", "")
        btype = building.get("Type", "")
        own = prop.get("OwnershipType", "")
        return (
            is_eligible_for(ptype, btype, own, "nucleus")
            or is_eligible_for(ptype, btype, own, "big_family")
        )

    candidates = [item for item in all_results if eligible_either(item)]
    print(f"[scraper] eligible (either strategy): {len(candidates)} listings")

    if not candidates:
        print("[scraper] No eligible results.")
        return

    upserted = 0
    skipped_price = 0

    # Transit lookups (Google Distance Matrix). Cache both TTC + GO values so we
    # don't re-charge for listings already scored.
    transit = TransitLookup()
    existing_scores = (
        sb.table("listing_scores")
        .select("listing_id, transit_min_ttc, transit_min_go")
        .execute()
        .data
    )
    cached_ttc = {
        r["listing_id"]: r["transit_min_ttc"]
        for r in existing_scores
        if r.get("transit_min_ttc") is not None and r["transit_min_ttc"] < 99
    }
    cached_go = {
        r["listing_id"]: r["transit_min_go"]
        for r in existing_scores
        if r.get("transit_min_go") is not None and r["transit_min_go"] < 99
    }

    for item in candidates:
        try:
            mls_id = item.get("MlsNumber", "")
            if not mls_id:
                continue

            price = parse_price(item)
            if price == 0:
                skipped_price += 1
                continue

            prop = item.get("Property", {})
            building = item.get("Building", {})
            address = prop.get("Address", {}).get("AddressText", "")
            beds = parse_int_field(building.get("Bedrooms"))
            baths = parse_int_field(building.get("BathroomTotal"))
            sqft = extract_sqft(item)
            prop_type = prop.get("Type", "") or building.get("Type", "")
            building_type = building.get("Type", "")
            ownership = prop.get("OwnershipType", "")
            lat = float(prop.get("Address", {}).get("Latitude", 0) or 0)
            lng = float(prop.get("Address", {}).get("Longitude", 0) or 0)
            photo = (prop.get("Photo") or [{}])[0].get("LowResPath", "")
            realtor_url = build_realtor_url(item)
            listed_str = item.get("InsertedDateUtc", "")[:10] if item.get("InsertedDateUtc") else None
            neighbourhood = infer_neighbourhood(address, sb)

            listing_row = {
                "id": mls_id,
                "address": address,
                "neighbourhood": neighbourhood,
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
            sb.table("listings").upsert(listing_row).execute()

            # Per-strategy eligibility
            elig_nucleus = is_eligible_for(prop_type, building_type, ownership, "nucleus")
            elig_big = is_eligible_for(prop_type, building_type, ownership, "big_family")

            # Two transit measurements (cached where possible)
            transit_ttc = cached_ttc.get(mls_id)
            if transit_ttc is None:
                transit_ttc = transit.get_transit_minutes(lat, lng)

            transit_go = cached_go.get(mls_id)
            if transit_go is None:
                transit_go = transit.get_go_transit_minutes(lat, lng)

            score_result = score_all_strategies(
                listing_row, sb,
                transit_ttc=transit_ttc,
                transit_go=transit_go,
                eligible_nucleus=elig_nucleus,
                eligible_big_family=elig_big,
            )
            sb.table("listing_scores").upsert(
                {"listing_id": mls_id, **score_result},
                on_conflict="listing_id"
            ).execute()
            upserted += 1

        except Exception as e:
            print(f"[scraper] error on {item.get('MlsNumber')}: {e}")

    # Mark stale listings inactive
    active_ids = [item.get("MlsNumber") for item in candidates if item.get("MlsNumber")]
    if active_ids:
        sb.table("listings").update({"is_active": False}).not_.in_("id", active_ids).execute()

    print(f"[scraper] done — upserted {upserted}, skipped {skipped_price} (price=0), "
          f"transit API calls: {transit.calls_made}")
