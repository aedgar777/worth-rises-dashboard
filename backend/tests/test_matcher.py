"""Unit tests for jurisdiction matching and candidate selection."""

from __future__ import annotations

import unittest

import pandas as pd

from app.transform.columns import normalize_raw_columns
from app.transform.matcher import (
    MatchResult,
    _pick_best,
    _score_candidate,
    _tied_candidates_have_different_rates,
    match_jurisdictions,
)
from tests.fixtures import (
    legacy_raw_df,
    mock_jurisdictions_df,
    worth_rises_raw_df,
)


def _row(**fields) -> pd.Series:
    defaults = {
        "facility_name": "",
        "state": "AL",
        "county": "",
        "facility_type": "",
        "in_state_rate": 0.10,
        "out_of_state_rate": 0.10,
    }
    defaults.update(fields)
    return pd.Series(defaults)


class TestColumnNormalization(unittest.TestCase):
    def test_worth_rises_per_min_schema_collapses_to_facility_rows(self) -> None:
        normalized = normalize_raw_columns(worth_rises_raw_df())
        self.assertIn("in_state_rate", normalized.columns)
        self.assertIn("out_of_state_rate", normalized.columns)
        self.assertNotIn("per_min", normalized.columns)

        marion = normalized[normalized["facility_name"].str.contains("MARION", na=False)]
        self.assertEqual(len(marion), 1)
        self.assertAlmostEqual(float(marion.iloc[0]["in_state_rate"]), 0.19)
        self.assertAlmostEqual(float(marion.iloc[0]["out_of_state_rate"]), 0.21)

    def test_in_state_false_maps_to_out_of_state_rate(self) -> None:
        normalized = normalize_raw_columns(worth_rises_raw_df())
        chilton = normalized[normalized["facility_name"] == "CHILTON COUNTY JAIL"].iloc[0]
        self.assertAlmostEqual(float(chilton["in_state_rate"]), 0.12)
        self.assertAlmostEqual(float(chilton["out_of_state_rate"]), 0.12)


class TestScoreCandidate(unittest.TestCase):
    def test_state_mismatch_scores_zero(self) -> None:
        score, reason = _score_candidate(
            _row(state="TX", facility_name="Some Jail"),
            "county",
            "AL",
            "CHILTON",
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(reason, "State mismatch")

    def test_excluded_facility_scores_zero(self) -> None:
        score, reason = _score_candidate(
            _row(facility_name="Jefferson County Youth Detention Center"),
            "county",
            "AL",
            "JEFFERSON",
        )
        self.assertEqual(score, 0.0)
        self.assertEqual(reason, "Matched exclusion keyword")

    def test_county_jail_with_name_match_scores_high(self) -> None:
        score, reason = _score_candidate(
            _row(facility_name="CHILTON COUNTY JAIL"),
            "county",
            "AL",
            "CHILTON",
        )
        self.assertGreaterEqual(score, 0.55)
        self.assertIn("County name in facility name", reason)

    def test_state_doc_scores_high_for_state_jurisdiction(self) -> None:
        score, reason = _score_candidate(
            _row(
                state="AK",
                facility_name="AK DOC - ANCHORAGE CORRECTIONAL COMPLEX/EAST",
            ),
            "state",
            "AK",
            None,
        )
        self.assertGreaterEqual(score, 0.55)
        self.assertIn("DOC naming pattern", reason)


class TestPickBest(unittest.TestCase):
    def test_tied_candidates_with_same_rates_skip_ambiguous_penalty(self) -> None:
        candidates = [
            (_row(in_state_rate=0.12, out_of_state_rate=0.12), 0.60, "first"),
            (_row(facility_name="Other Jail", in_state_rate=0.12, out_of_state_rate=0.12), 0.58, "second"),
        ]
        best, confidence, notes, _ = _pick_best(candidates)
        self.assertAlmostEqual(confidence, 0.60)
        self.assertIn("share rates", notes)
        self.assertIsNotNone(best)

    def test_tied_candidates_with_different_rates_are_ambiguous_without_tiebreaker(self) -> None:
        candidates = [
            (_row(in_state_rate=0.19, out_of_state_rate=0.21), 0.60, "first"),
            (_row(facility_name="Other Jail", in_state_rate=0.19, out_of_state_rate=0.19), 0.58, "second"),
        ]
        best, confidence, notes, _ = _pick_best(candidates)
        self.assertAlmostEqual(confidence, 0.54)
        self.assertIn("Ambiguous match", notes)
        self.assertIsNotNone(best)

    def test_tied_candidates_with_different_rates_use_tiebreaker(self) -> None:
        candidates = [
            (_row(facility_name="Facility A", in_state_rate=0.19, out_of_state_rate=0.21), 0.60, "a"),
            (_row(facility_name="Facility B", in_state_rate=0.19, out_of_state_rate=0.19), 0.58, "b"),
        ]

        def tiebreaker(top: list) -> int:
            return 1

        best, _confidence, notes, _ = _pick_best(candidates, tiebreaker=tiebreaker)
        self.assertEqual(best["facility_name"], "Facility B")
        self.assertIn("Places tie-break", notes)

    def test_below_threshold_returns_no_match(self) -> None:
        candidates = [(_row(facility_name="Unknown Facility"), 0.30, "weak")]
        best, confidence, notes, reference = _pick_best(candidates)
        self.assertIsNone(best)
        self.assertLess(confidence, 0.45)
        self.assertIn("Below confidence threshold", notes)
        self.assertIsNotNone(reference)


class TestTiedRateDetection(unittest.TestCase):
    def test_detects_different_out_of_state_rates(self) -> None:
        candidates = [
            (_row(out_of_state_rate=0.21), 0.6, ""),
            (_row(out_of_state_rate=0.19), 0.58, ""),
        ]
        self.assertTrue(_tied_candidates_have_different_rates(candidates, 0.6))

    def test_same_rates_not_different(self) -> None:
        candidates = [
            (_row(in_state_rate=0.12, out_of_state_rate=0.12), 0.6, ""),
            (_row(in_state_rate=0.12, out_of_state_rate=0.12), 0.58, ""),
        ]
        self.assertFalse(_tied_candidates_have_different_rates(candidates, 0.6))


class TestMatchJurisdictionsIntegration(unittest.TestCase):
    def _result_for(
        self,
        results: list[MatchResult],
        j_type: str,
        state: str,
        county: str | None = None,
    ) -> MatchResult | None:
        for result in results:
            if (
                result.jurisdiction_type == j_type
                and result.state == state
                and (county is None or result.county == county)
            ):
                return result
        return None

    def test_worth_rises_mock_data_matches_ak_state(self) -> None:
        results = match_jurisdictions(mock_jurisdictions_df(), worth_rises_raw_df())
        ak = self._result_for(results, "state", "AK")
        self.assertIsNotNone(ak)
        assert ak is not None
        self.assertEqual(ak.match_status, "matched")
        self.assertIn("DOC", ak.facility_name or "")
        self.assertAlmostEqual(ak.in_state_rate or 0, 0.085, places=3)

    def test_worth_rises_mock_data_matches_chilton_county(self) -> None:
        results = match_jurisdictions(mock_jurisdictions_df(), worth_rises_raw_df())
        chilton = self._result_for(results, "county", "AL", "CHILTON")
        self.assertIsNotNone(chilton)
        assert chilton is not None
        self.assertEqual(chilton.match_status, "matched")
        self.assertIn("CHILTON", chilton.facility_name or "")

    def test_excluded_juvenile_does_not_match_jurisdiction(self) -> None:
        jurisdictions = pd.DataFrame(
            [{"type": "county", "state": "AL", "county": "JEFFERSON"}]
        )
        results = match_jurisdictions(jurisdictions, worth_rises_raw_df())
        jefferson = self._result_for(results, "county", "AL", "JEFFERSON")
        self.assertIsNotNone(jefferson)
        assert jefferson is not None
        self.assertEqual(jefferson.match_status, "unmatched")

    def test_legacy_sample_schema_still_matches(self) -> None:
        jurisdictions = pd.DataFrame(
            [
                {"type": "state", "state": "AK", "county": ""},
                {"type": "county", "state": "AL", "county": "CHILTON"},
            ]
        )
        results = match_jurisdictions(jurisdictions, legacy_raw_df())
        ak = self._result_for(results, "state", "AK")
        chilton = self._result_for(results, "county", "AL", "CHILTON")
        self.assertEqual(ak.match_status if ak else None, "matched")
        self.assertEqual(chilton.match_status if chilton else None, "matched")


if __name__ == "__main__":
    unittest.main()
