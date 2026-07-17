"""Approximate county/state centroids for map display."""

# State centroids (lat, lng) for state-level jurisdictions
STATE_CENTROIDS: dict[str, tuple[float, float]] = {
    "AK": (64.2008, -149.4937),
    "AR": (34.9697, -92.3731),
    "AZ": (34.0489, -111.0937),
    "CO": (39.5501, -105.7821),
    "GA": (32.1656, -82.9001),
    "KY": (37.8393, -84.2700),
    "MO": (38.4561, -92.2884),
    "ND": (47.5289, -99.7840),
}

# Sample county centroids for demo map plotting
COUNTY_CENTROIDS: dict[tuple[str, str], tuple[float, float]] = {
    ("CA", "KERN"): (35.3433, -118.7273),
    ("CA", "SACRAMENTO"): (38.4747, -121.3542),
    ("CO", "DENVER"): (39.7392, -104.9903),
    ("FL", "BROWARD"): (26.1901, -80.3659),
    ("FL", "PALM BEACH"): (26.7056, -80.0364),
    ("GA", "FULTON"): (33.7904, -84.4677),
    ("GA", "GWINNETT"): (33.9617, -84.0236),
    ("IL", "COOK"): (41.7377, -87.6970),
    ("MI", "WAYNE"): (42.2814, -83.2325),
    ("NC", "MECKLENBURG"): (35.2467, -80.8328),
    ("TX", "HARRIS"): (29.8580, -95.3935),
}


def get_coordinates(state: str, county: str | None, jurisdiction_type: str) -> tuple[float | None, float | None]:
    state = state.upper()
    if jurisdiction_type == "state":
        if state in STATE_CENTROIDS:
            lat, lng = STATE_CENTROIDS[state]
            return lat, lng
        return None, None

    if county:
        key = (state, county.upper())
        if key in COUNTY_CENTROIDS:
            lat, lng = COUNTY_CENTROIDS[key]
            return lat, lng
        # Fallback: use state centroid with small offset based on county name hash
        if state in STATE_CENTROIDS:
            lat, lng = STATE_CENTROIDS[state]
            offset = (hash(county) % 100) / 500
            return lat + offset, lng + offset

    return None, None
