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
        val = float(size_str.split()[0].replace(",", ""))
        unit = size_str.split()[1].lower() if len(size_str.split()) > 1 else "sqft"
        return int(val * 10.764) if "m" in unit else int(val)
    except Exception:
        return None


def infer_neighbourhood(address: str, sb) -> str | None:
    """Infer neighbourhood name from address using keywords table."""
    rows = sb.table("neighbourhoods").select("name, keywords").execute().data
    address_lower = address.lower()
    for row in rows:
        for kw in (row.get("keywords") or []):
            if kw in address_lower:
                return row["name"]
    return None


async def scrape_page(client: httpx.AsyncClient, page: int) -> list[dict]:
    payload = {**SEARCH_PAYLOAD, "CurrentPage": str(page)}
    r = await client.post(REALTOR_API, data=payload, headers=HEADERS)
    r.raise_for_status()
    return r.json().get("Results", [])


async def scrape_and_upsert():
    """Main scrape job — call this from the scheduler."""
    sb = supabase_client()
    all_results = []

    async with httpx.AsyncClient(timeout=30) as client:
        # Fetch pages 1–3 for up to 150 listings
        for page in range(1, 4):
            try:
                results = await scrape_page(client, page)
                all_results.extend(results)
                print(f"[scraper] page {page}: {len(results)} listings")
                if len(results) < 50:
                    break  # no more pages
                await asyncio.sleep(1)  # be polite
            except Exception as e:
                print(f"[scraper] error on page {page}: {e}")
                break

    print(f"[scraper] total fetched: {len(all_results)} listings")

    for item in all_results:
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

            # Upsert listing
            sb.table("listings").upsert(listing_row).execute()

            # Score and upsert score
            score_result = score_listing(listing_row, sb)
            score_row = {"listing_id": mls_id, **score_result}
            sb.table("listing_scores").upsert(score_row, on_conflict="listing_id").execute()

        except Exception as e:
            print(f"[scraper] error on {item.get('MlsNumber')}: {e}")

    # Mark listings no longer in results as inactive
    active_ids = [item.get("MlsNumber") for item in all_results if item.get("MlsNumber")]
    if active_ids:
        sb.table("listings") \
          .update({"is_active": False}) \
          .not_.in_("id", active_ids) \
          .execute()

    print("[scraper] done")
