"""
Realtor.ca internal API scraper.
"""
import httpx
import asyncio
from db import supabase_client
from scoring import score_listing

REALTOR_API = "https://api2.realtor.ca/Listing.svc/PropertySearch_Post"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-CA,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.realtor.ca/map#view=list&sort=6-D&pgeo=2&geoIds=g30_dpz89rm7&trans=2&dr=true&bed=3-0&bath=2-0&minprice=900000&maxprice=1700000",
    "Origin": "https://www.realtor.ca",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
    "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "X-Requested-With": "XMLHttpRequest",
}

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
    "TransactionTypeId": "2",  # For sale
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


async def scrape_page(client: httpx.AsyncClient, page: int) -> list[dict]:
    payload = {**BASE_PAYLOAD, "CurrentPage": str(page)}
    try:
        r = await client.post(REALTOR_API, data=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        data = r.json()
        results = data.get("Results", [])
        print(f"[scraper] page {page}: {len(results)} listings (total: {data.get('Paging', {}).get('TotalRecords', '?')})")
        return results
    except httpx.HTTPStatusError as e:
        print(f"[scraper] HTTP error page {page}: {e.response.status_code} - {e.response.text[:200]}")
        return []
    except Exception as e:
        print(f"[scraper] error page {page}: {e}")
        return []


async def scrape_and_upsert():
    """Main scrape job."""
    sb = supabase_client()
    all_results = []

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        # First do a GET to realtor.ca to get cookies
        try:
            await client.get("https://www.realtor.ca/", headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            })
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[scraper] cookie fetch failed: {e}")

        for page in range(1, 4):
            results = await scrape_page(client, page)
            all_results.extend(results)
            if len(results) < 50:
                break
            await asyncio.sleep(2)

    print(f"[scraper] total fetched: {len(all_results)} listings")

    if not all_results:
        print("[scraper] No results — Realtor.ca may be blocking. Skipping upsert.")
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

    # Mark stale listings inactive
    active_ids = [item.get("MlsNumber") for item in all_results if item.get("MlsNumber")]
    if active_ids:
        sb.table("listings").update({"is_active": False}).not_.in_("id", active_ids).execute()

    print(f"[scraper] done — upserted {upserted} listings")
