"""Mock CSV data for unit tests.

Test states and counties are chosen from TX, WI, and NY with facility names
modeled on real jails/prisons (TDCJ, WI DOC, Erie County Sheriff). These are
NOT present in the Worth Rises assignment raw export at
sample-data/worth-rises-raw-data.csv (which covers AK, AL, AR, AZ, CA, CO, etc.).
"""

from __future__ import annotations

import pandas as pd

# Worth Rises per_min format: one row per call type (in_state flag + per_min).
WORTH_RISES_RAW_ROWS: list[dict] = [
    {
        "provider": "securus",
        "state": "TX",
        "county": "",
        "facility_id": 9001,
        "facility_name": "TDCJ - WYNNE UNIT",
        "phone": "9038757768",
        "in_state": True,
        "per_min": 0.06,
    },
    {
        "provider": "securus",
        "state": "TX",
        "county": "",
        "facility_id": 9001,
        "facility_name": "TDCJ - WYNNE UNIT",
        "phone": "8005550200",
        "in_state": False,
        "per_min": 0.06,
    },
    {
        "provider": "securus",
        "state": "WI",
        "county": "",
        "facility_id": 9002,
        "facility_name": "WAUPUN CORRECTIONAL INSTITUTION",
        "phone": "9203245571",
        "in_state": True,
        "per_min": 0.08,
    },
    {
        "provider": "securus",
        "state": "WI",
        "county": "",
        "facility_id": 9002,
        "facility_name": "WAUPUN CORRECTIONAL INSTITUTION",
        "phone": "8005550201",
        "in_state": False,
        "per_min": 0.10,
    },
    {
        "provider": "securus",
        "state": "TX",
        "county": "",
        "facility_id": 9003,
        "facility_name": "TRAVIS COUNTY JAIL",
        "phone": "5128549770",
        "in_state": True,
        "per_min": 0.14,
    },
    {
        "provider": "securus",
        "state": "TX",
        "county": "",
        "facility_id": 9003,
        "facility_name": "TRAVIS COUNTY JAIL",
        "phone": "8005550202",
        "in_state": False,
        "per_min": 0.14,
    },
    {
        "provider": "securus",
        "state": "NY",
        "county": "",
        "facility_id": 9004,
        "facility_name": "ERIE COUNTY HOLDING CENTER",
        "phone": "7168587638",
        "in_state": True,
        "per_min": 0.11,
    },
    {
        "provider": "securus",
        "state": "NY",
        "county": "",
        "facility_id": 9004,
        "facility_name": "ERIE COUNTY HOLDING CENTER",
        "phone": "8005550203",
        "in_state": False,
        "per_min": 0.13,
    },
    {
        "provider": "securus",
        "state": "WI",
        "county": "",
        "facility_id": 9005,
        "facility_name": "Rock County Youth Detention Center",
        "phone": "6085550100",
        "in_state": True,
        "per_min": 0.05,
    },
]

# Legacy wide-format sample (repo sample-data).
LEGACY_RAW_ROWS: list[dict] = [
    {
        "facility_name": "WAUPUN CORRECTIONAL INSTITUTION",
        "state": "WI",
        "county": "",
        "facility_type": "State Prison",
        "provider": "Securus",
        "in_state_rate": 2.10,
        "out_of_state_rate": 3.15,
    },
    {
        "facility_name": "TRAVIS COUNTY JAIL",
        "state": "TX",
        "county": "TRAVIS",
        "facility_type": "County Jail",
        "provider": "Securus",
        "in_state_rate": 3.25,
        "out_of_state_rate": 4.50,
    },
    {
        "facility_name": "ERIE COUNTY HOLDING CENTER",
        "state": "NY",
        "county": "ERIE",
        "facility_type": "County Jail",
        "provider": "Securus",
        "in_state_rate": 3.75,
        "out_of_state_rate": 5.10,
    },
]

MOCK_JURISDICTIONS_ROWS: list[dict] = [
    {"type": "state", "state": "TX", "county": ""},
    {"type": "state", "state": "WI", "county": ""},
    {"type": "county", "state": "TX", "county": "TRAVIS"},
    {"type": "county", "state": "NY", "county": "ERIE"},
    {"type": "county", "state": "WI", "county": "ROCK"},
]


def worth_rises_raw_df() -> pd.DataFrame:
    return pd.DataFrame(WORTH_RISES_RAW_ROWS)


def legacy_raw_df() -> pd.DataFrame:
    return pd.DataFrame(LEGACY_RAW_ROWS)


def mock_jurisdictions_df() -> pd.DataFrame:
    return pd.DataFrame(MOCK_JURISDICTIONS_ROWS)
