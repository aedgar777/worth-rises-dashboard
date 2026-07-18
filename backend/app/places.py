"""Google Places API client for geocoding, county resolution, and tie-breaking."""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.id,places.formattedAddress,places.location,places.addressComponents"
DEFAULT_MAX_WORKERS = 12

LookupQuery = tuple[str, str, str | None]


@dataclass
class PlaceResult:
    place_id: str | None = None
    formatted_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    county: str | None = None
    state: str | None = None


@dataclass
class PlacesClient:
    api_key: str
    max_workers: int = DEFAULT_MAX_WORKERS
    _cache: dict[str, PlaceResult | None] = field(default_factory=dict)
    _cache_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip())

    def lookup(
        self,
        facility_name: str,
        state: str,
        county_hint: str | None = None,
    ) -> PlaceResult | None:
        if not self.enabled or not facility_name.strip():
            return None

        cache_key = _cache_key(facility_name, state, county_hint)
        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        query_parts = [facility_name.strip(), state.strip().upper()]
        if county_hint:
            query_parts.insert(1, f"{county_hint} County")
        result = self._search(", ".join(query_parts))

        with self._cache_lock:
            self._cache.setdefault(cache_key, result)
            return self._cache[cache_key]

    def lookup_many(self, queries: list[LookupQuery]) -> list[PlaceResult | None]:
        if not queries:
            return []
        if not self.enabled:
            return [None] * len(queries)
        if len(queries) == 1:
            name, state, county = queries[0]
            return [self.lookup(name, state, county)]

        workers = min(self.max_workers, len(queries))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            return list(executor.map(lambda q: self.lookup(*q), queries))

    def jurisdiction_alignment_score(
        self,
        place: PlaceResult | None,
        jurisdiction_type: str,
        state: str,
        county: str | None,
    ) -> float:
        if place is None:
            return 0.0

        score = 0.0
        if place.state and place.state.upper() == state.upper():
            score += 0.5
        elif place.formatted_address and state.upper() in place.formatted_address.upper():
            score += 0.35

        if jurisdiction_type == "county" and county and place.county:
            if _normalize_county(place.county) == _normalize_county(county):
                score += 0.5
            elif _normalize_county(county) in _normalize_county(place.county):
                score += 0.3

        if place.latitude is not None and place.longitude is not None:
            score += 0.1

        return score

    def _search(self, text_query: str) -> PlaceResult | None:
        payload = json.dumps({"textQuery": text_query, "maxResultCount": 1}).encode()
        request = urllib.request.Request(
            PLACES_SEARCH_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key,
                "X-Goog-FieldMask": FIELD_MASK,
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return None

        places = data.get("places") or []
        if not places:
            return None

        place = places[0]
        location = place.get("location") or {}
        county, state = _parse_address_components(place.get("addressComponents") or [])

        return PlaceResult(
            place_id=place.get("id"),
            formatted_address=place.get("formattedAddress"),
            latitude=location.get("latitude"),
            longitude=location.get("longitude"),
            county=county,
            state=state,
        )


def _cache_key(facility_name: str, state: str, county_hint: str | None) -> str:
    return f"{facility_name.strip()}|{state.strip().upper()}|{county_hint or ''}"


def _parse_address_components(components: list[dict]) -> tuple[str | None, str | None]:
    county = None
    state = None
    for component in components:
        types = component.get("types") or []
        text = component.get("longText") or component.get("shortText") or ""
        if "administrative_area_level_2" in types:
            county = _normalize_county(text)
        if "administrative_area_level_1" in types:
            state = (component.get("shortText") or text).upper()
    return county, state


def _normalize_county(value: str) -> str:
    cleaned = re.sub(r"\s+county$", "", value.strip(), flags=re.IGNORECASE)
    return re.sub(r"[^A-Z0-9 ]", " ", cleaned.upper()).strip()


def fill_missing_counties(raw_df, places: PlacesClient) -> int:
    """Resolve blank county fields in raw provider data via Places API."""
    if not places.enabled:
        return 0

    rows_by_key: dict[tuple[str, str], list] = {}
    for idx, row in raw_df.iterrows():
        current = str(row.get("county", "") or "").strip()
        if current:
            continue
        facility = str(row.get("facility_name", "") or "").strip()
        state = str(row.get("state", "") or "").strip().upper()
        if not facility or not state:
            continue
        rows_by_key.setdefault((facility, state), []).append(idx)

    if not rows_by_key:
        return 0

    keys = list(rows_by_key.keys())
    place_results = places.lookup_many([(facility, state, None) for facility, state in keys])

    filled = 0
    for (facility, state), place in zip(keys, place_results):
        if not place or not place.county:
            continue
        for idx in rows_by_key[(facility, state)]:
            raw_df.at[idx, "county"] = place.county
            filled += 1
    return filled
