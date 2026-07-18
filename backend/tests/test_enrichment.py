import unittest
from unittest.mock import MagicMock

from app.enrichment import enrich_results_with_places
from app.places import PlaceResult, PlacesClient
from app.transform.matcher import MatchResult


class TestEnrichmentCounty(unittest.TestCase):
    def test_places_county_not_applied_to_state_jurisdiction(self) -> None:
        result = MatchResult(
            jurisdiction_type="state",
            state="TX",
            county=None,
            facility_name="TDCJ - WYNNE UNIT",
            provider="securus",
            in_state_rate=0.06,
            out_of_state_rate=0.06,
            match_status="matched",
            match_confidence=0.8,
            notes="State prison / DOC facility",
        )
        places = PlacesClient(api_key="test-key")
        places.lookup_many = MagicMock(
            return_value=[
                PlaceResult(
                    formatted_address="8101 FM 969, Austin, TX 78724",
                    latitude=30.28,
                    longitude=-97.62,
                    county="TRAVIS",
                    state="TX",
                )
            ]
        )

        enrich_results_with_places([result], places)

        self.assertIsNone(result.county)
        self.assertEqual(result.latitude, 30.28)

    def test_places_county_applied_to_county_jurisdiction(self) -> None:
        result = MatchResult(
            jurisdiction_type="county",
            state="TX",
            county=None,
            facility_name="TRAVIS COUNTY JAIL",
            provider="securus",
            in_state_rate=0.14,
            out_of_state_rate=0.14,
            match_status="matched",
            match_confidence=0.8,
            notes="County jail / sheriff facility",
        )
        places = PlacesClient(api_key="test-key")
        places.lookup_many = MagicMock(
            return_value=[
                PlaceResult(
                    formatted_address="500 W 10th St, Austin, TX 78701",
                    latitude=30.27,
                    longitude=-97.74,
                    county="TRAVIS",
                    state="TX",
                )
            ]
        )

        enrich_results_with_places([result], places)

        self.assertEqual(result.county, "TRAVIS")


if __name__ == "__main__":
    unittest.main()
