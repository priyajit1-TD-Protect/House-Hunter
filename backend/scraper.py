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
from scoring import score_listing

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
SCRAPER_API_ENDPOINT = "https://async.scraperapi.com/jobs"

# Freehold property types to keep
FREEHOLD_TYPES = {
    "detached", "semi-detached", "townhouse", "row / townhouse",
    "att/row/twnhouse", "detached-condominium", "link"
}

BASE_PAYLOAD = {
    "CultureId": "1",
    "ApplicationId": "1",
    "PropertySearchTypeId": "1",   # Residential
    "PriceMin": "900000",
    "PriceMax": "1700000",
    "BedRange": "3-0",
    "BathRange": "2-0",
    "LongitudeMin": "-79.65",
    "LongitudeMax": "-79.10",
    "LatitudeMin": "43.58",
    "LatitudeMax": "43.85",
    "SortBy": "6",
    "RecordsPerPage": "50",
    "CurrentPage": "1",
    "PropertyTypeGroupID": "1",
    "TransactionTypeId": "2",      # For Sale
    # BuildingTypeId 1=House, 16=Att/Row/Twnhouse, 17=Semi-Detached
    # We fetch all and filter client-side to avoid missing types
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
    """Extract price — Realtor.ca puts it in Property.Price (e.g. '$1,299,000')
    or Property.PriceUnformatted (e.g. '1299000')."""
    prop = item.get("Property", {})

    # PriceUnformatted is the clean integer string
    raw = prop.get("PriceUnformatted")
    if raw not in (None, "", "0"):
        try:
            return int(str(raw).replace(",", "").replace("$", "").strip())
        except Exception:
            pass

    # Price is formatted like "$1,299,000"
    price_str = prop.get("Price", "")
    if price_str:
        import re
        digits = re.sub(r"[^\d]", "", price_str)
        if digits:
            return int(digits)

    return 0


def is_freehold(item: dict) -> bool:
    """Return True if this is a freehold property type."""
    building = item.get("Building", {})
    prop_type = (building.get("Type") or "").lower().strip()
    sub_type = (building.get("SubType") or "").lower().strip()
    ownership = (item.get("Land", {}).get("Ownership") or "").lower()

    # Exclude condo/strata
    if "condo" in ownership or "strata" in ownership:
        return False
    if "condo" in prop_type or "apartment" in prop_type:
        return False

    # Accept known freehold types
    for ft in FREEHOLD_TYPES:
        if ft in prop_type or ft in sub_type:
            return True

    # Also accept by BuildingTypeId: 1=House, 16=Row/Townhouse, 17=Semi-detached
    building_type_id = str(item.get("Building", {}).get("BuildingTypeId", ""))
    if building_type_id in ("1", "16", "17", "25"):
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
        for page in range(1, 4):
            results = await scrape_page_via_scraperapi(client, page)
            all_results.extend(results)
            if len(results) < 50:
                break
            await asyncio.sleep(2)

    print(f"[scraper] total raw: {len(all_results)} listings")

    # Filter to freehold only
    freehold = [item for item in all_results if is_freehold(item)]
    print(f"[scraper] freehold after filter: {len(freehold)} listings")

    # Diagnostic: log the first listing's price-related fields
    if all_results:
        first = all_results[0]
        prop = first.get("Property", {})
        print(f"[scraper] DIAG Property keys: {list(prop.keys())}")
        print(f"[scraper] DIAG Price={prop.get('Price')!r} PriceUnformatted={prop.get('PriceUnformatted')!r}")
        bld = first.get("Building", {})
        print(f"[scraper] DIAG Building keys: {list(bld.keys())}")
        print(f"[scraper] DIAG Type={bld.get('Type')!r} Bedrooms={bld.get('Bedrooms')!r} Baths={bld.get('BathroomTotal')!r}")

    if not freehold:
        print("[scraper] No freehold results.")
        return

    upserted = 0
    skipped_price = 0
    for item in freehold:
        try:
            mls_id = item.get("MlsNumber", "")
            if not mls_id:
                continue

            price = parse_price(item)
            if price == 0:
                skipped_price += 1
                print(f"[scraper] skipping {mls_id} — price=0, Property keys: {list(item.get('Property', {}).keys())}")
                continue

            address = item.get("Property", {}).get("Address", {}).get("AddressText", "")
            beds = parse_int_field(item.get("Building", {}).get("Bedrooms"))
            baths = parse_int_field(item.get("Building", {}).get("BathroomTotal"))
            sqft = extract_sqft(item)
            prop_type = item.get("Building", {}).get("Type", "")
            lat = float(item.get("Property", {}).get("Address", {}).get("Latitude", 0) or 0)
            lng = float(item.get("Property", {}).get("Address", {}).get("Longitude", 0) or 0)
            photo = (item.get("Property", {}).get("Photo") or [{}])[0].get("LowResPath", "")
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

            score_result = score_listing(listing_row, sb)
            sb.table("listing_scores").upsert(
                {"listing_id": mls_id, **score_result},
                on_conflict="listing_id"
            ).execute()
            upserted += 1

        except Exception as e:
            print(f"[scraper] error on {item.get('MlsNumber')}: {e}")

    # Mark stale listings inactive
    active_ids = [item.get("MlsNumber") for item in freehold if item.get("MlsNumber")]
    if active_ids:
        sb.table("listings").update({"is_active": False}).not_.in_("id", active_ids).execute()

    print(f"[scraper] done — upserted {upserted}, skipped {skipped_price} (price=0)")
