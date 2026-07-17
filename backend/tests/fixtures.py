"""Mock CSV data matching Worth Rises assignment provider schemas."""

from __future__ import annotations

import pandas as pd

# Worth Rises test format: one row per call type (in_state flag + per_min).
WORTH_RISES_RAW_ROWS: list[dict] = [
    {
        "provider": "securus",
        "state": "AK",
        "county": "",
        "facility_id": 4660,
        "facility_name": "AK DOC - ANCHORAGE CORRECTIONAL COMPLEX/EAST (ANCHORAGE JAIL)",
        "phone": "9074653500",
        "in_state": True,
        "per_min": 0.085,
    },
    {
        "provider": "securus",
        "state": "AK",
        "county": "",
        "facility_id": 4660,
        "facility_name": "AK DOC - ANCHORAGE CORRECTIONAL COMPLEX/EAST (ANCHORAGE JAIL)",
        "phone": "8015381000",
        "in_state": False,
        "per_min": 0.085,
    },
    {
        "provider": "securus",
        "state": "AL",
        "county": "",
        "facility_id": 432,
        "facility_name": "MARION COUNTY SHERIFF'S DEPT",
        "phone": "2059214000",
        "in_state": True,
        "per_min": 0.19,
    },
    {
        "provider": "securus",
        "state": "AL",
        "county": "",
        "facility_id": 432,
        "facility_name": "MARION COUNTY SHERIFF'S DEPT",
        "phone": "8005550100",
        "in_state": False,
        "per_min": 0.21,
    },
    {
        "provider": "securus",
        "state": "AL",
        "county": "",
        "facility_id": 100,
        "facility_name": "CHILTON COUNTY JAIL",
        "phone": "2057554691",
        "in_state": True,
        "per_min": 0.12,
    },
    {
        "provider": "securus",
        "state": "AL",
        "county": "",
        "facility_id": 100,
        "facility_name": "CHILTON COUNTY JAIL",
        "phone": "8005550101",
        "in_state": False,
        "per_min": 0.12,
    },
    {
        "provider": "securus",
        "state": "AL",
        "county": "",
        "facility_id": 200,
        "facility_name": "Jefferson County Youth Detention Center",
        "phone": "2055550100",
        "in_state": True,
        "per_min": 0.05,
    },
    {
        "provider": "securus",
        "state": "CO",
        "county": "",
        "facility_id": 300,
        "facility_name": "DENVER COUNTY JAIL",
        "phone": "3035550100",
        "in_state": True,
        "per_min": 0.15,
    },
    {
        "provider": "securus",
        "state": "CO",
        "county": "",
        "facility_id": 300,
        "facility_name": "DENVER COUNTY JAIL",
        "phone": "8005550102",
        "in_state": False,
        "per_min": 0.15,
    },
]

# Legacy wide-format sample (repo sample-data).
LEGACY_RAW_ROWS: list[dict] = [
    {
        "facility_name": "Alaska Department of Corrections",
        "state": "AK",
        "county": "",
        "facility_type": "State Prison",
        "provider": "Securus",
        "in_state_rate": 2.10,
        "out_of_state_rate": 3.15,
    },
    {
        "facility_name": "Chilton County Jail",
        "state": "AL",
        "county": "CHILTON",
        "facility_type": "County Jail",
        "provider": "Securus",
        "in_state_rate": 3.25,
        "out_of_state_rate": 4.50,
    },
    {
        "facility_name": "Denver County Jail",
        "state": "CO",
        "county": "DENVER",
        "facility_type": "County Jail",
        "provider": "Securus",
        "in_state_rate": 3.75,
        "out_of_state_rate": 5.10,
    },
]

MOCK_JURISDICTIONS_ROWS: list[dict] = [
    {"type": "state", "state": "AK", "county": ""},
    {"type": "state", "state": "CO", "county": ""},
    {"type": "county", "state": "AL", "county": "CHILTON"},
    {"type": "county", "state": "AL", "county": "MARION"},
    {"type": "county", "state": "CO", "county": "DENVER"},
]


def worth_rises_raw_df() -> pd.DataFrame:
    return pd.DataFrame(WORTH_RISES_RAW_ROWS)


def legacy_raw_df() -> pd.DataFrame:
    return pd.DataFrame(LEGACY_RAW_ROWS)


def mock_jurisdictions_df() -> pd.DataFrame:
    return pd.DataFrame(MOCK_JURISDICTIONS_ROWS)
