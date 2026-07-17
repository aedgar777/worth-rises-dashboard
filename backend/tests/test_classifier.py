"""Unit tests for facility classification rules."""

import unittest

from app.transform.classifier import (
    classify_record,
    describe_facility_rules,
    matched_exclude_rules,
)


class TestClassifierExclude(unittest.TestCase):
    def test_excludes_juvenile_facility(self) -> None:
        result = classify_record(
            "Jefferson County Youth Detention Center",
            "",
            "county",
        )
        self.assertEqual(result.decision, "exclude")
        self.assertIn("youth facility", result.matched_exclude_rules)

    def test_excludes_federal_facility(self) -> None:
        result = classify_record("Federal Correctional Institution", "", "state")
        self.assertEqual(result.decision, "exclude")
        self.assertIn("federal facility", result.matched_exclude_rules)

    def test_matched_exclude_rules_helper(self) -> None:
        rules = matched_exclude_rules("County Work Release Center", "County")
        self.assertIn("work release program", rules)


class TestClassifierInclude(unittest.TestCase):
    def test_state_doc_is_include(self) -> None:
        result = classify_record(
            "AK DOC - ANCHORAGE CORRECTIONAL COMPLEX/EAST (ANCHORAGE JAIL)",
            "",
            "state",
        )
        self.assertEqual(result.decision, "include")
        self.assertTrue(result.matched_include_signals)

    def test_county_jail_is_include(self) -> None:
        result = classify_record("CHILTON COUNTY JAIL", "County Jail", "county")
        self.assertEqual(result.decision, "include")
        self.assertIn("county jail", result.matched_include_signals)

    def test_county_sheriff_is_include(self) -> None:
        result = classify_record("MARION COUNTY SHERIFF'S DEPT", "", "county")
        self.assertEqual(result.decision, "include")


class TestClassifierReview(unittest.TestCase):
    def test_jail_like_name_on_state_jurisdiction(self) -> None:
        result = classify_record("DENVER COUNTY JAIL", "", "state")
        self.assertEqual(result.decision, "review")
        self.assertEqual(result.reason, "Jail-like name on state jurisdiction")

    def test_prison_like_name_on_county_jurisdiction(self) -> None:
        result = classify_record(
            "Arkansas Department of Correction",
            "State Prison",
            "county",
        )
        self.assertEqual(result.decision, "review")
        self.assertEqual(result.reason, "Prison-like name on county jurisdiction")


class TestDescribeFacilityRules(unittest.TestCase):
    def test_describes_exclusion_detail(self) -> None:
        text = describe_facility_rules(
            "Jefferson County Youth Detention Center",
            "",
            "county",
            match_confidence=0.2,
        )
        self.assertIn("Excluded by facility rules", text)
        self.assertIn("youth facility", text)

    def test_describes_low_confidence(self) -> None:
        text = describe_facility_rules(
            "CHILTON COUNTY JAIL",
            "",
            "county",
            match_score=0.3,
            score_reason="County mismatch",
            match_confidence=0.3,
        )
        self.assertIn("Below jurisdiction match threshold", text)


if __name__ == "__main__":
    unittest.main()
