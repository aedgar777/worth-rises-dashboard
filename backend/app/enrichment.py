"""Apply Google Places enrichment to matched jurisdiction results."""

from __future__ import annotations

from app.geo import get_coordinates
from app.places import PlacesClient
from app.transform.matcher import MatchResult


def enrich_results_with_places(
    results: list[MatchResult],
    places: PlacesClient,
) -> None:
    """Attach map coordinates and formatted addresses to every jurisdiction result.

    Looks up each matched facility name through Google Places in parallel. When Places
    cannot resolve a facility, falls back to a static state/county centroid so the
    map still renders.
    """
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
            # Only county jurisdictions carry a county; never copy Places county onto state rows.
            if (
                place.county
                and not result.county
                and result.jurisdiction_type == "county"
            ):
                result.county = place.county
            if place.county and result.notes and result.jurisdiction_type == "county":
                result.notes = f"{result.notes}; Places county: {place.county}"
            elif place.county and result.jurisdiction_type == "county":
                result.notes = f"Places county: {place.county}"
        else:
            _apply_jurisdiction_centroid(result)


def _apply_centroid_fallback(results: list[MatchResult]) -> None:
    """Use built-in centroids for every row when the Places API key is not configured."""
    for result in results:
        _apply_jurisdiction_centroid(result)


def _apply_jurisdiction_centroid(result: MatchResult) -> None:
    """Set lat/lng from a static lookup table keyed by state and county."""
    lat, lng = get_coordinates(result.state, result.county, result.jurisdiction_type)
    result.latitude = lat
    result.longitude = lng
