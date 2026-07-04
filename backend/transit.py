"""
Real transit time to Union Station via Google Distance Matrix API (transit mode).
Targets weekday 8:00 AM arrival. Caches results in the DB to avoid re-charging
for listings whose coordinates haven't changed.
"""
import os
import httpx
from datetime import datetime, timedelta, timezone

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
DISTANCE_MATRIX_URL = "https://maps.googleapis.com/maps/api/distancematrix/json"

# Union Station, Toronto
UNION_LAT = 43.6452
UNION_LNG = -79.3806

# Hard safety cap: never make more than this many API calls in a single run.
# 207 listings x 2 calls (TTC+GO) = ~414 for a full fresh measure. Cache means
# steady-state runs only call for NEW listings, so this cap rarely binds and
# monthly cost stays ~$14 (see loaders/README for the math).
MAX_TRANSIT_LOOKUPS_PER_RUN = 450

# Eastern Time offset (EDT = UTC-4). Toronto is on daylight time most of the year;
# for a commute estimate this is close enough and avoids a tz dependency.
ET_OFFSET_HOURS = -4


def next_weekday_8am_epoch() -> int:
    """Return the epoch seconds for the next upcoming weekday at 08:00 ET.
    Google transit requires arrival_time in the future."""
    now_utc = datetime.now(timezone.utc)
    now_et = now_utc + timedelta(hours=ET_OFFSET_HOURS)

    target = now_et.replace(hour=8, minute=0, second=0, microsecond=0)

    # If 8 AM today already passed, move to tomorrow
    if target <= now_et:
        target += timedelta(days=1)

    # Skip weekends (5 = Saturday, 6 = Sunday)
    while target.weekday() >= 5:
        target += timedelta(days=1)

    # Convert back to UTC epoch
    target_utc = target - timedelta(hours=ET_OFFSET_HOURS)
    return int(target_utc.timestamp())


class TransitLookup:
    """Tracks per-run call count so we never exceed the safety cap."""

    def __init__(self):
        self.calls_made = 0

    def _lookup(self, lat: float, lng: float, transit_mode: str | None) -> int | None:
        """Shared Distance Matrix call. transit_mode None = default (all modes).
        Pass 'rail|train|subway|tram|bus' to bias toward regional rail (GO)."""
        if not GOOGLE_MAPS_API_KEY:
            return None
        if not lat or not lng:
            return None
        if self.calls_made >= MAX_TRANSIT_LOOKUPS_PER_RUN:
            print(f"[transit] safety cap ({MAX_TRANSIT_LOOKUPS_PER_RUN}) reached, skipping")
            return None

        params = {
            "origins": f"{lat},{lng}",
            "destinations": f"{UNION_LAT},{UNION_LNG}",
            "mode": "transit",
            "arrival_time": str(next_weekday_8am_epoch()),
            "key": GOOGLE_MAPS_API_KEY,
        }
        if transit_mode:
            params["transit_mode"] = transit_mode

        try:
            self.calls_made += 1
            r = httpx.get(DISTANCE_MATRIX_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            if data.get("status") != "OK":
                print(f"[transit] API status: {data.get('status')} - {data.get('error_message', '')}")
                return None

            element = data["rows"][0]["elements"][0]
            if element.get("status") != "OK":
                print(f"[transit] element status: {element.get('status')} (mode={transit_mode})")
                return None

            return round(element["duration"]["value"] / 60)

        except Exception as e:
            print(f"[transit] lookup error (mode={transit_mode}): {e}")
            return None

    def get_transit_minutes(self, lat: float, lng: float) -> int | None:
        """TTC-only style commute to Union (Nucleus strategy).
        Biases toward local transit modes (subway/bus/tram/streetcar)."""
        return self._lookup(lat, lng, transit_mode="subway|bus|tram")

    def get_go_transit_minutes(self, lat: float, lng: float) -> int | None:
        """Door-to-door commute to Union including GO/regional rail
        (Happy Big Family strategy). 'rail|train' biases toward GO."""
        return self._lookup(lat, lng, transit_mode="rail|train|subway|bus")
