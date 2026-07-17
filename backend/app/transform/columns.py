"""Normalize raw provider CSV columns to the pipeline's expected schema."""

from __future__ import annotations

import re

import pandas as pd

REQUIRED = {"facility_name", "state", "in_state_rate", "out_of_state_rate"}

COLUMN_ALIASES: dict[str, list[str]] = {
    "facility_name": [
        "facility_name",
        "facility",
        "site_name",
        "site",
        "location",
        "name",
        "agency_name",
        "location_name",
    ],
    "state": ["state", "state_code", "st"],
    "county": ["county", "county_name"],
    "city": ["city", "city_name"],
    "facility_type": ["facility_type", "agency_type", "category"],
    "provider": ["provider", "provider_company", "vendor", "telecom_provider", "company"],
    "in_state_rate": [
        "in_state_rate",
        "instate_rate",
        "local_rate",
        "instate",
        "rate_in_state",
    ],
    "out_of_state_rate": [
        "out_of_state_rate",
        "out_state_rate",
        "outstate_rate",
        "out_of_state",
        "interstate_rate",
        "outstate",
        "rate_out_of_state",
        "rate_out_state",
    ],
}


def _normalize_header(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower())
    return cleaned.strip("_")


def _parse_bool(value) -> bool | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().upper()
    if text in {"TRUE", "T", "YES", "Y", "1"}:
        return True
    if text in {"FALSE", "F", "NO", "N", "0"}:
        return False
    return None


def _is_worth_rises_per_min_format(raw_df: pd.DataFrame) -> bool:
    if "per_min" not in raw_df.columns:
        return False
    if "in_state" not in raw_df.columns:
        return False
    sample = raw_df["in_state"].head(20)
    return sample.map(_parse_bool).notna().any()


def _collapse_per_min_format(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Merge Worth Rises row-per-call-type records into one row per facility."""
    df = raw_df.copy()
    df["_is_in_state_call"] = df["in_state"].map(_parse_bool)
    df["_per_min_rate"] = df["per_min"].map(parse_dollar_rate)

    group_cols = ["facility_id"] if "facility_id" in df.columns else []
    if not group_cols:
        group_cols = [col for col in ("facility_name", "state", "county") if col in df.columns]
    if not group_cols:
        group_cols = ["facility_name", "state"]

    records: list[dict] = []
    for _, group in df.groupby(group_cols, dropna=False):
        base = group.iloc[0].to_dict()
        in_rates = group.loc[group["_is_in_state_call"] == True, "_per_min_rate"].dropna()
        out_rates = group.loc[group["_is_in_state_call"] == False, "_per_min_rate"].dropna()

        base["in_state_rate"] = float(in_rates.iloc[0]) if len(in_rates) else None
        base["out_of_state_rate"] = float(out_rates.iloc[0]) if len(out_rates) else None

        if base["in_state_rate"] is None and base["out_of_state_rate"] is not None:
            base["in_state_rate"] = base["out_of_state_rate"]
        elif base["out_of_state_rate"] is None and base["in_state_rate"] is not None:
            base["out_of_state_rate"] = base["in_state_rate"]

        records.append(base)

    collapsed = pd.DataFrame(records)
    drop_cols = {
        "in_state",
        "per_min",
        "phone",
        "_is_in_state_call",
        "_per_min_rate",
    }
    return collapsed.drop(columns=[col for col in drop_cols if col in collapsed.columns])


def normalize_raw_columns(raw_df: pd.DataFrame) -> pd.DataFrame:
    raw_df = raw_df.copy()
    raw_df.columns = [_normalize_header(c) for c in raw_df.columns]

    worth_rises_format = _is_worth_rises_per_min_format(raw_df)
    if worth_rises_format:
        raw_df = _collapse_per_min_format(raw_df)
    elif "per_min" in raw_df.columns:
        raw_df["in_state_rate"] = raw_df["per_min"].map(parse_dollar_rate)
        raw_df["out_of_state_rate"] = raw_df["per_min"].map(parse_dollar_rate)
        raw_df = raw_df.drop(columns=["per_min"])

    for canonical, aliases in COLUMN_ALIASES.items():
        if canonical in raw_df.columns:
            continue
        for alias in aliases:
            if alias not in raw_df.columns:
                continue
            if worth_rises_format and alias == "in_state":
                continue
            raw_df = raw_df.rename(columns={alias: canonical})
            break

    if "facility_name" not in raw_df.columns:
        raw_df["facility_name"] = _derive_facility_names(raw_df)

    for col in ("facility_type", "county", "provider", "city"):
        if col not in raw_df.columns:
            raw_df[col] = ""

    for col in ("in_state_rate", "out_of_state_rate"):
        if col in raw_df.columns:
            raw_df[col] = raw_df[col].apply(parse_dollar_rate)

    if worth_rises_format and "in_state" in raw_df.columns:
        raw_df = raw_df.drop(columns=["in_state"])

    return raw_df


def parse_dollar_rate(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        cleaned = str(value).replace("$", "").replace(",", "").strip()
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def _derive_facility_names(df: pd.DataFrame) -> pd.Series:
    names = []
    for _, row in df.iterrows():
        state = str(row.get("state", "") or "").strip().upper()
        county = str(row.get("county", "") or "").strip()
        city = str(row.get("city", "") or "").strip()
        ftype = str(row.get("facility_type", "") or "").strip().upper()

        if county:
            names.append(f"{county} County Jail")
        elif city:
            names.append(f"{city} Detention Center")
        elif ftype == "STATE" or (not county and not city and state):
            names.append(f"{state} Department of Corrections")
        else:
            names.append(f"{state} Correctional Facility" if state else "Unknown Facility")
    return pd.Series(names, index=df.index)


def validate_raw_columns(raw_df: pd.DataFrame) -> None:
    missing = REQUIRED - set(raw_df.columns)
    if missing:
        found = ", ".join(raw_df.columns)
        hint = _hint_for_columns(raw_df.columns)
        raise ValueError(
            f"Raw CSV missing columns: {', '.join(sorted(missing))}. "
            f"Found: {found}. {hint}"
        )


def _hint_for_columns(columns: pd.Index) -> str:
    cols = set(columns)
    if cols <= {"type", "state", "county"}:
        return (
            "This looks like the jurisdictions reference file — upload raw provider "
            "telecom data instead (with rates and facility/agency info)."
        )
    if "per_min" in cols and "in_state" in cols:
        return (
            "Worth Rises provider format detected (per_min + in_state flag); "
            "re-upload after deploy if this error persists."
        )
    if "provider_company" in cols or "out_state_rate" in cols:
        return "Worth Rises provider format is supported; re-upload after deploy."
    return "Expected state plus in-state and out-of-state rate columns (or per_min)."
