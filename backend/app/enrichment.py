"""Apply Google Places enrichment to matched jurisdiction results."""

from __future__ import annotations

from app.geo import get_coordinates
from app.places import PlacesClient
from app.transform.matcher import MatchResult


def enrich_results_with_places(
    results: list[MatchResult],
    places: PlacesClient,
) -> None:
    """Geocode matched facilities and attach place metadata (in-place)."""
    if not places.enabled:
        _apply_centroid_fallback(results)
        return

    pending: list[tuple[int, str, str, str | None]] = []
    for index, result in enumerate(results):
        if not result.facility_name:
            _apply_jurisdiction_centroid(result)
            continue
        pending.append((index, result.facility_name, result.state, result.county))

    if not pending:
        return

    place_results = places.lookup_many(
        [(name, state, county) for _, name, state, county in pending]
    )

    for (index, _name, _state, _county), place in zip(pending, place_results):
        result = results[index]
        if place and place.latitude is not None and place.longitude is not None:
            result.latitude = place.latitude
            result.longitude = place.longitude
            result.place_id = place.place_id
            result.place_description = place.formatted_address
            if place.county and not result.county:
                result.county = place.county
            if place.county and result.notes:
                result.notes = f"{result.notes}; Places county: {place.county}"
            elif place.county:
                result.notes = f"Places county: {place.county}"
        else:
            _apply_jurisdiction_centroid(result)


def _apply_centroid_fallback(results: list[MatchResult]) -> None:
    for result in results:
        _apply_jurisdiction_centroid(result)


def _apply_jurisdiction_centroid(result: MatchResult) -> None:
    lat, lng = get_coordinates(result.state, result.county, result.jurisdiction_type)
    result.latitude = lat
    result.longitude = lng
