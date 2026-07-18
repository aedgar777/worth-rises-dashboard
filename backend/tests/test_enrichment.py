import unittest
from unittest.mock import MagicMock

from app.enrichment import enrich_results_with_places
from app.places import PlaceResult, PlacesClient
from app.transform.matcher import MatchResult


class TestEnrichmentCounty(unittest.TestCase):
    def test_places_county_not_applied_to_state_jurisdiction(self) -> None:
        result = MatchResult(
            jurisdiction_type="state",
            state="CO",
            county=None,
            facility_name="COLORADO DOC",
            provider="securus",
            in_state_rate=0.05,
            out_of_state_rate=0.12,
            match_status="matched",
            match_confidence=0.8,
            notes="State prison / DOC facility",
        )
        places = PlacesClient(api_key="test-key")
        places.lookup_many = MagicMock(
            return_value=[
                PlaceResult(
                    formatted_address="123 Main St, Denver, CO",
                    latitude=39.7,
                    longitude=-104.9,
                    county="DENVER",
                    state="CO",
                )
            ]
        )

        enrich_results_with_places([result], places)

        self.assertIsNone(result.county)
        self.assertEqual(result.latitude, 39.7)

    def test_places_county_applied_to_county_jurisdiction(self) -> None:
        result = MatchResult(
            jurisdiction_type="county",
            state="CO",
            county=None,
            facility_name="DENVER COUNTY JAIL",
            provider="securus",
            in_state_rate=0.05,
            out_of_state_rate=0.12,
            match_status="matched",
            match_confidence=0.8,
            notes="County jail / sheriff facility",
        )
        places = PlacesClient(api_key="test-key")
        places.lookup_many = MagicMock(
            return_value=[
                PlaceResult(
                    formatted_address="123 Main St, Denver, CO",
                    latitude=39.7,
                    longitude=-104.9,
                    county="DENVER",
                    state="CO",
                )
            ]
        )

        enrich_results_with_places([result], places)

        self.assertEqual(result.county, "DENVER")


if __name__ == "__main__":
    unittest.main()
