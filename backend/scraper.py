"""
Realtor.ca scraper via ScraperAPI.
Uses ScraperAPI's /scrape structured endpoint for POST requests.
"""
import httpx
import asyncio
import os
import urllib.parse
from db import supabase_client
from scoring import score_listing

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"
SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY", "")
SCRAPER_API_ENDPOINT = "https://async.scraperapi.com/jobs"

BASE_PAYLOAD = {
    "CultureId": "1",
    "ApplicationId": "1",
    "PropertySearchTypeId": "1",
    "PriceMin": "900000",
    "PriceMax": "1700000",
    "BedRange": "3-0",
    "BathRange": "2-0",
    "LongitudeMin": "-79.55",
    "LongitudeMax": "-79.20",
    "LatitudeMin": "43.62",
    "LatitudeMax": "43.78",
    "SortBy": "6",
    "SortOrder": "Descending",
    "RecordsPerPage": "50",
    "CurrentPage": "1",
    "PropertyTypeGroupID": "1",
    "TransactionTypeId": "2",
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


def infer_neighbourhood(address: str, sb) -> str | None:
    rows = sb.table("neighbourhoods").select("name, keywords").execute().data
    address_lower = address.lower()
    for row in rows:
        for kw in (row.get("keywords") or []):
            if kw in address_lower:
                return row["name"]
    return None


async def scrape_page_via_scraperapi(client: httpx.AsyncClient, page: int) -> list[dict]:
    """Use ScraperAPI async jobs endpoint for POST requests."""
    payload = {**BASE_PAYLOAD, "CurrentPage": str(page)}
    body = urllib.parse.urlencode(payload)

    # Submit async job
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
        # Submit the job
        r = await client.post(
            SCRAPER_API_ENDPOINT,
            json=job_payload,
            timeout=30,
        )
        print(f"[scraper] job submit status: {r.status_code}")
        if r.status_code not in (200, 201):
            print(f"[scraper] job submit failed: {r.text[:300]}")
            return []

        job = r.json()
        job_id = job.get("id")
        status_url = job.get("statusUrl")
        print(f"[scraper] job {job_id} submitted, polling...")

        # Poll for result
        for attempt in range(30):
            await asyncio.sleep(3)
            status_r = await client.get(status_url, timeout=15)
            status_data = status_r.json()
            status = status_data.get("status")
            print(f"[scraper] job {job_id} status: {status} (attempt {attempt+1})")

            if status == "finished":
                response_body = status_data.get("response", {}).get("body", "")
                try:
                    import json
                    data = json.loads(response_body)
                    results = data.get("Results", [])
                    print(f"[scraper] page {page}: {len(results)} listings")
                    return results
                except Exception as e:
                    print(f"[scraper] JSON parse error: {e}, body: {response_body[:200]}")
                    return []
            elif status == "failed":
                print(f"[scraper] job failed: {status_data}")
                return []

        print(f"[scraper] job {job_id} timed out")
        return []

    except Exception as e:
        print(f"[scraper] ScraperAPI error page {page}: {e}")
        return []


async def scrape_page_direct(client: httpx.AsyncClient, page: int) -> list[dict]:
    """Direct request — works locally, blocked on cloud IPs."""
    payload = {**BASE_PAYLOAD, "CurrentPage": str(page)}
    body = urllib.parse.urlencode(payload)
    try:
        r = await client.post(
            REALTOR_API,
            content=body,
            headers=REALTOR_HEADERS,
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("Results", [])
        print(f"[scraper] page {page}: {len(results)} listings (direct)")
        return results
    except Exception as e:
        print(f"[scraper] direct error page {page}: {e}")
        return []


async def scrape_and_upsert():
    """Main scrape job."""
    sb = supabase_client()
    all_results = []

    async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
        for page in range(1, 4):
            if SCRAPER_API_KEY:
                results = await scrape_page_via_scraperapi(client, page)
            else:
                results = await scrape_page_direct(client, page)

            all_results.extend(results)
            if len(results) < 50:
                break
            await asyncio.sleep(2)

    print(f"[scraper] total fetched: {len(all_results)} listings")

    if not all_results:
        print("[scraper] No results.")
        return

    upserted = 0
    for item in all_results:
        try:
            mls_id = item.get("MlsNumber", "")
            if not mls_id:
                continue

            price = int(item.get("Property", {}).get("PriceUnformatted", 0))
            address = item.get("Property", {}).get("Address", {}).get("AddressText", "")
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

    active_ids = [item.get("MlsNumber") for item in all_results if item.get("MlsNumber")]
    if active_ids:
        sb.table("listings").update({"is_active": False}).not_.in_("id", active_ids).execute()

    print(f"[scraper] done — upserted {upserted} listings")
