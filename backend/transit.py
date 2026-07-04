"""
Real transit time to Union Station via Google Distance Matrix API (transit mode).
Targets weekday morning departures (leaving home). Caches results in the DB to avoid re-charging
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

# Hard safety cap: never exceed this many API calls per run.
# 5 departure samples per listing (unrestricted transit, one query each).
# Sized to cover a full first run of the entire matching inventory (~1100
# eligible listings x 5 = 5500). Cache means steady-state runs only call for
# NEW listings, so this rarely binds. First full run ~$28-55 against credit.
MAX_TRANSIT_LOOKUPS_PER_RUN = 6000

# Eastern Time offset (EDT = UTC-4). Toronto is on daylight time most of the year;
# for a commute estimate this is close enough and avoids a tz dependency.
ET_OFFSET_HOURS = -4


def next_weekday_epoch(hour: int = 8, minute: int = 0) -> int:
    """Epoch seconds for the next upcoming weekday at HH:MM ET.
    Used as a transit departure_time (must be in the future)."""
    now_utc = datetime.now(timezone.utc)
    now_et = now_utc + timedelta(hours=ET_OFFSET_HOURS)

    target = now_et.replace(hour=hour, minute=minute, second=0, microsecond=0)

    # If the target time today already passed, move to tomorrow
    if target <= now_et:
        target += timedelta(days=1)

    # Skip weekends (5 = Saturday, 6 = Sunday)
    while target.weekday() >= 5:
        target += timedelta(days=1)

    target_utc = target - timedelta(hours=ET_OFFSET_HOURS)
    return int(target_utc.timestamp())


# Backwards-compatible alias
def next_weekday_8am_epoch() -> int:
    return next_weekday_epoch(8, 0)


# Departure times we sample (weekday morning, leaving home). We take the MAX
# across these so a single unusually favourable departure can't understate a
# typical commute. 5 samples across the peak window (7:30-8:30) reflect leaving
# home to reach the office at Union.
SAMPLE_DEPARTURES = [(7, 30), (7, 45), (8, 0), (8, 15), (8, 30)]


class TransitLookup:
    """Tracks per-run call count so we never exceed the safety cap."""

    _logged_raw = False  # one-time raw-response diagnostic flag

    def __init__(self):
        self.calls_made = 0

    def _lookup(self, lat: float, lng: float, transit_mode: str | None,
                departure_epoch: int) -> int | None:
        """Single Distance Matrix call for one departure time (leaving home).
        transit_mode None = all modes; pass 'rail|train|subway|bus' for GO."""
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
            "departure_time": str(departure_epoch),
            "key": GOOGLE_MAPS_API_KEY,
        }
        # NOTE: We deliberately do NOT set transit_mode. Restricting it (e.g.
        # 'rail|train|subway|bus') combined with departure_time makes Google
        # return ZERO_RESULTS on many trips. Unrestricted transit already
        # includes GO rail, TTC subway, buses, and streetcars — Google picks the
        # fastest real route, which is what a commuter actually experiences.
        if transit_mode:
            # kept for API compatibility but intentionally unused
            pass

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
                # ZERO_RESULTS here is legitimate: no viable transit route (or
                # an extremely long one). The listing simply won't qualify.
                return None

            return round(element["duration"]["value"] / 60)

        except Exception as e:
            print(f"[transit] lookup error: {e}")
            return None

    def _sampled_max(self, lat: float, lng: float) -> int | None:
        """Query several weekday morning departure times (leaving home) and
        return the MAX minutes, so a single unusually favourable departure can't
        understate a typical commute. Unrestricted transit (all modes: GO rail,
        TTC subway, bus, streetcar) — Google picks the fastest real route.
        Returns None only if EVERY sample failed."""
        results = []
        for hour, minute in SAMPLE_DEPARTURES:
            if self.calls_made >= MAX_TRANSIT_LOOKUPS_PER_RUN:
                break
            epoch = next_weekday_epoch(hour, minute)
            val = self._lookup(lat, lng, None, epoch)
            if val is not None:
                results.append(val)
        return max(results) if results else None

    def get_commute_minutes(self, lat: float, lng: float) -> int | None:
        """Door-to-door commute to Union using all transit modes, worst of 5
        sampled morning departures. One value serves both strategies — the
        difference between Nucleus and Big Family is the ceiling (60 vs 70),
        not the transit mode."""
        return self._sampled_max(lat, lng)

    # Backwards-compatible aliases (both now return the same unrestricted value)
    def get_transit_minutes(self, lat: float, lng: float) -> int | None:
        return self.get_commute_minutes(lat, lng)

    def get_go_transit_minutes(self, lat: float, lng: float) -> int | None:
        return self.get_commute_minutes(lat, lng)
