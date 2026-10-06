import unittest
from datetime import date
from unittest.mock import patch

import trip_data


def obs(oid, lng, lat):
    return {"id": oid, "geojson": {"coordinates": [lng, lat]}, "observed_on": "2024-05-01",
            "taxon": {"id": 1, "name": "Example species", "rank": "species"}}


class TripDataTests(unittest.TestCase):
    def test_union_of_places_and_exact_polygon_deduplicates(self):
        geom = {"type": "Polygon", "coordinates": [[[4, 51], [6, 51], [6, 53], [4, 53], [4, 51]]]}
        def pages(params):
            if params.get("place_id") == 10:
                return [obs(1, 5, 52)]
            if params.get("place_id") == 20:
                return [obs(1, 5, 52), obs(2, 8, 52)]
            return [obs(1, 5, 52), obs(3, 5.5, 52), obs(4, 9, 52)]
        with patch.object(trip_data, "_pages", side_effect=pages):
            found = trip_data.trip_observations("someone", date(2024, 5, 1), date(2024, 5, 3), (10, 20), geom)
        self.assertEqual([x["id"] for x in found], [1, 2, 3])

    def test_star_priority_and_unverified_area(self):
        ids = {42}
        self.assertEqual(trip_data.star_for(ids, (42, 42, 42, True), has_area=True)["star"], "🔴")
        self.assertEqual(trip_data.star_for(ids, (42, 42, 10, True), has_area=True)["star"], "🟠")
        self.assertEqual(trip_data.star_for(ids, (42, 42, 10, False), has_area=True)["star"], "🟡")
        self.assertEqual(trip_data.star_for(ids, (10, 9, 8, True), has_area=True)["star"], "")

    def test_date_window_splits_before_ten_thousand_cap(self):
        def fake_get(path, params):
            if params["d1"] == "2024-05-01" and params["d2"] == "2024-05-02":
                return {"total_results": 10001, "results": []}
            return {"total_results": 1, "results": [{"id": params["d1"]}]}
        with patch.object(trip_data, "get", side_effect=fake_get):
            rows = trip_data._pages({"d1": "2024-05-01", "d2": "2024-05-02"})
        self.assertEqual([r["id"] for r in rows], ["2024-05-01", "2024-05-02"])


if __name__ == "__main__":
    unittest.main()
