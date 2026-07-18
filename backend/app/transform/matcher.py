"""Match raw telecom provider records to reference jurisdictions."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from typing import TYPE_CHECKING, Callable

import pandas as pd

from app.transform.classifier import classify_record, describe_facility_rules
from app.transform.columns import normalize_raw_columns, validate_raw_columns

if TYPE_CHECKING:
    from app.places import PlacesClient

STATE_NAMES = {
    "AL": "ALABAMA",
    "AK": "ALASKA",
    "AZ": "ARIZONA",
    "AR": "ARKANSAS",
    "CA": "CALIFORNIA",
    "CO": "COLORADO",
    "GA": "GEORGIA",
    "KY": "KENTUCKY",
    "MO": "MISSOURI",
    "ND": "NORTH DAKOTA",
    "FL": "FLORIDA",
    "IA": "IOWA",
    "ID": "IDAHO",
    "IL": "ILLINOIS",
    "IN": "INDIANA",
    "KS": "KANSAS",
    "MD": "MARYLAND",
    "ME": "MAINE",
    "MI": "MICHIGAN",
    "MN": "MINNESOTA",
    "MS": "MISSISSIPPI",
    "MT": "MONTANA",
    "NC": "NORTH CAROLINA",
}


@dataclass
class MatchResult:
    """One output row: a reference jurisdiction paired with the best provider match."""

    jurisdiction_type: str
    state: str
    county: str | None
    facility_name: str | None
    provider: str | None
    in_state_rate: float | None
    out_of_state_rate: float | None
    match_status: str
    match_confidence: float
    notes: str
    facility_rules: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    place_id: str | None = None
    place_description: str | None = None


def _normalize(text: str | None) -> str:
    """Uppercase and strip punctuation so county and facility names compare reliably."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    return re.sub(r"[^A-Z0-9 ]", " ", str(text).upper()).strip()


def _county_in_name(county: str, facility_name: str) -> bool:
    """True when the county name (or all of its tokens) appears in the facility name."""
    county_norm = _normalize(county)
    name_norm = _normalize(facility_name)
    if not county_norm:
        return False
    county_tokens = county_norm.split()
    if county_norm in name_norm:
        return True
    if len(county_tokens) > 1 and all(t in name_norm for t in county_tokens):
        return True
    return False


def _score_candidate(
    row: pd.Series,
    jurisdiction_type: str,
    state: str,
    county: str | None,
) -> tuple[float, str]:
    """Score how well one raw provider row fits a target jurisdiction (0.0–1.0).

    Returns zero for wrong state or excluded facilities. Otherwise starts at 0.35 and
    adjusts for county alignment, DOC naming patterns, and classifier decision.
    """
    facility_name = str(row.get("facility_name", "") or "")
    row_state = str(row.get("state", "") or "").upper().strip()
    row_county = _normalize(row.get("county"))

    if row_state != state.upper():
        return 0.0, "State mismatch"

    classification = classify_record(
        facility_name,
        str(row.get("facility_type", "") or ""),
        jurisdiction_type,
    )
    if classification.decision == "exclude":
        return 0.0, classification.reason

    score = 0.35
    reasons = [classification.reason]

    if jurisdiction_type == "county" and county:
        county_norm = _normalize(county)
        if row_county == county_norm:
            score += 0.35
            reasons.append("Exact county field match")
        elif _county_in_name(county, facility_name):
            score += 0.25
            reasons.append("County name in facility name")
        else:
            score -= 0.2
            reasons.append("County mismatch")

    if jurisdiction_type == "state":
        state_name = STATE_NAMES.get(state.upper(), "")
        name_norm = _normalize(facility_name)
        if state_name and state_name in name_norm:
            score += 0.15
            reasons.append("State name in facility name")
        if "DEPARTMENT" in name_norm or " CORRECTION" in name_norm:
            score += 0.2
            reasons.append("DOC naming pattern")

    if classification.decision == "include":
        score += 0.15
    elif classification.decision == "review":
        score -= 0.05

    return min(score, 1.0), "; ".join(reasons)


def _summarize_no_candidates(
    raw_df: pd.DataFrame,
    j_type: str,
    state: str,
    county: str | None,
) -> str:
    """Explain why no raw facility cleared the minimum candidate score for this jurisdiction."""
    state_upper = state.upper()
    state_rows = raw_df[
        raw_df["state"].astype(str).str.upper().str.strip() == state_upper
    ]

    if state_rows.empty:
        return "No candidates: no raw provider records for this state"

    excluded: Counter[str] = Counter()
    below_threshold: list[tuple[float, str]] = []
    county_mismatch_count = 0

    for _, row in state_rows.iterrows():
        score, reason = _score_candidate(row, j_type, state, county)
        if score == 0.0:
            excluded[reason] += 1
        elif score < 0.35:
            below_threshold.append((score, reason))
            if "County mismatch" in reason:
                county_mismatch_count += 1

    total = len(state_rows)
    excluded_total = sum(excluded.values())

    if excluded_total == total:
        top_reason, count = excluded.most_common(1)[0]
        return (
            f"No candidates: all {total} in-state record(s) filtered out "
            f"({top_reason}: {count})"
        )

    if below_threshold and not excluded_total:
        best_score, best_reason = max(below_threshold, key=lambda item: item[0])
        return (
            f"No candidates: closest record scored {best_score:.2f} "
            f"(minimum 0.35) — {best_reason}"
        )

    if below_threshold and excluded_total:
        parts = []
        if below_threshold:
            parts.append(f"{len(below_threshold)} below score threshold")
        if excluded_total:
            parts.append(f"{excluded_total} excluded by facility rules")
        detail = "; ".join(parts)
        if j_type == "county" and county and county_mismatch_count:
            return (
                f"No candidates: raw records exist for {state} but none align with "
                f"{county} County ({detail})"
            )
        return f"No candidates: {detail}"

    if j_type == "county" and county:
        return (
            f"No candidates: no raw provider records align with "
            f"{county} County, {state}"
        )

    return "No candidates: no raw provider records matched this jurisdiction"


def _find_reference_facility(
    raw_df: pd.DataFrame,
    j_type: str,
    state: str,
    county: str | None,
) -> pd.Series | None:
    """Return the highest-scoring in-state row for context, even when it cannot match."""
    state_upper = state.upper()
    best_row: pd.Series | None = None
    best_score = -1.0

    for _, row in raw_df.iterrows():
        if str(row.get("state", "") or "").upper().strip() != state_upper:
            continue
        score, _ = _score_candidate(row, j_type, state, county)
        if score > best_score:
            best_score = score
            best_row = row

    return best_row


def _facility_name_from_row(row: pd.Series | None) -> str | None:
    """Extract a non-empty facility name from a raw provider row."""
    if row is None:
        return None
    name = str(row.get("facility_name", "") or "").strip()
    return name or None


def _facility_rules_from_row(
    row: pd.Series | None,
    j_type: str,
    state: str,
    county: str | None,
    match_confidence: float,
) -> str | None:
    """Describe exclusion/scoring rules for the reference facility on an unmatched row."""
    if row is None:
        return None
    facility_name = str(row.get("facility_name", "") or "")
    facility_type = str(row.get("facility_type", "") or "")
    if not facility_name.strip():
        return None
    score, score_reason = _score_candidate(row, j_type, state, county)
    return describe_facility_rules(
        facility_name,
        facility_type,
        j_type,
        match_score=score,
        score_reason=score_reason,
        match_confidence=match_confidence,
    )


def _provider_from_row(row: pd.Series | None) -> str | None:
    """Extract the telecom vendor name from a raw provider row."""
    if row is None:
        return None
    provider = str(row.get("provider", "") or "").strip()
    return provider or None


def _as_rate(value) -> float | None:
    """Parse a rate column value, returning None for blanks or invalid numbers."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tied_candidates_have_different_rates(
    candidates: list[tuple[pd.Series, float, str]],
    best_score: float,
) -> bool:
    """True when tied candidates disagree on in-state or out-of-state rate."""
    tied_rows = [row for row, score, _ in candidates if score >= best_score - 0.05]
    if len(tied_rows) < 2:
        return False

    in_rates = {_as_rate(row.get("in_state_rate")) for row in tied_rows}
    out_rates = {_as_rate(row.get("out_of_state_rate")) for row in tied_rows}
    in_rates.discard(None)
    out_rates.discard(None)

    return len(in_rates) > 1 or len(out_rates) > 1


def _pick_best(
    candidates: list[tuple[pd.Series, float, str]],
    tiebreaker: Callable[[list[tuple[pd.Series, float, str]]], int] | None = None,
) -> tuple[pd.Series | None, float, str, pd.Series | None]:
    """Choose the best candidate and derive match confidence and explanatory notes.

    Thresholds: candidates need score >= 0.35 to compete, >= 0.45 to win outright.
    When the top two scores are within 0.05, Places breaks ties only if their rates differ.
    """
    if not candidates:
        return None, 0.0, "No candidates", None
    candidates.sort(key=lambda item: item[1], reverse=True)
    best_row, best_score, best_reason = candidates[0]
    if best_score < 0.45:
        return None, best_score, f"Below confidence threshold ({best_reason})", best_row
    if len(candidates) > 1 and candidates[1][1] >= best_score - 0.05:
        rates_differ = _tied_candidates_have_different_rates(candidates, best_score)
        if rates_differ and tiebreaker:
            winner_idx = tiebreaker(candidates[:3])
            winner = candidates[winner_idx]
            return winner[0], winner[1], f"Places tie-break (rates differ); {winner[2]}", winner[0]
        if rates_differ:
            return best_row, best_score * 0.9, f"Ambiguous match; {best_reason}", best_row
        return best_row, best_score, f"Tied candidates share rates; {best_reason}", best_row
    return best_row, best_score, best_reason, best_row


def _make_places_tiebreaker(
    places: PlacesClient,
    jurisdiction_type: str,
    state: str,
    county: str | None,
):
    """Build a tie-breaker that geocodes tied facilities and picks the best address fit."""

    def tiebreaker(top_candidates: list[tuple[pd.Series, float, str]]) -> int:
        place_results = places.lookup_many(
            [
                (str(row.get("facility_name", "") or ""), state, county)
                for row, _score, _reason in top_candidates
            ]
        )
        best_idx = 0
        best_alignment = -1.0
        for idx, place in enumerate(place_results):
            alignment = places.jurisdiction_alignment_score(
                place, jurisdiction_type, state, county
            )
            if alignment > best_alignment:
                best_alignment = alignment
                best_idx = idx
        return best_idx

    return tiebreaker


def match_jurisdictions(
    jurisdictions_df: pd.DataFrame,
    raw_df: pd.DataFrame,
    places: PlacesClient | None = None,
) -> list[MatchResult]:
    """Produce one MatchResult per reference jurisdiction in the seed list.

    Pipeline: normalize raw CSV → optionally fill counties via Places → score every
    in-state facility → pick the best match → label as matched, review, or unmatched.
    """
    raw_df = raw_df.copy()
    raw_df = normalize_raw_columns(raw_df)
    validate_raw_columns(raw_df)

    for col in ("facility_type", "county", "provider"):
        if col not in raw_df.columns:
            raw_df[col] = ""

    if places and places.enabled:
        from app.places import fill_missing_counties

        filled = fill_missing_counties(raw_df, places)
        if filled:
            raw_df["county"] = raw_df["county"].fillna("")

    jurisdictions_df = jurisdictions_df.copy()
    jurisdictions_df.columns = [c.strip().lower() for c in jurisdictions_df.columns]

    results: list[MatchResult] = []

    for _, jurisdiction in jurisdictions_df.iterrows():
        j_type = str(jurisdiction["type"]).lower().strip()
        state = str(jurisdiction["state"]).upper().strip()
        county_val = jurisdiction.get("county")
        county = None if pd.isna(county_val) or str(county_val).strip() == "" else str(county_val).strip()

        candidates: list[tuple[pd.Series, float, str]] = []
        for _, row in raw_df.iterrows():
            score, reason = _score_candidate(row, j_type, state, county)
            if score >= 0.35:
                candidates.append((row, score, reason))

        tiebreaker = None
        if places and places.enabled:
            tiebreaker = _make_places_tiebreaker(places, j_type, state, county)

        best_row, confidence, notes, reference_row = _pick_best(candidates, tiebreaker=tiebreaker)

        if best_row is None:
            if notes == "No candidates":
                notes = _summarize_no_candidates(raw_df, j_type, state, county)
            if reference_row is None:
                reference_row = _find_reference_facility(raw_df, j_type, state, county)
            results.append(
                MatchResult(
                    jurisdiction_type=j_type,
                    state=state,
                    county=county,
                    facility_name=_facility_name_from_row(reference_row),
                    provider=_provider_from_row(reference_row),
                    in_state_rate=None,
                    out_of_state_rate=None,
                    match_status="unmatched",
                    match_confidence=round(confidence, 3),
                    notes=notes,
                    facility_rules=_facility_rules_from_row(
                        reference_row, j_type, state, county, confidence
                    ),
                )
            )
            continue

        # High confidence → matched; borderline → review for human follow-up.
        status = "matched" if confidence >= 0.55 else "review"
        results.append(
            MatchResult(
                jurisdiction_type=j_type,
                state=state,
                county=county,
                facility_name=str(best_row.get("facility_name")),
                provider=str(best_row.get("provider") or "") or None,
                in_state_rate=_as_rate(best_row.get("in_state_rate")),
                out_of_state_rate=_as_rate(best_row.get("out_of_state_rate")),
                match_status=status,
                match_confidence=round(confidence, 3),
                notes=notes,
                facility_rules=None,
            )
        )

    return results


def results_to_dataframe(results: list[MatchResult]) -> pd.DataFrame:
    """Convert match results to a flat DataFrame for export or inspection."""
    return pd.DataFrame([r.__dict__ for r in results])
