import json
import unittest
from copy import deepcopy
from trip_store import make_record, normalize_record, validate_import, merge_records, same_trip, rename_record
from trip_overview import sorted_trips
from trip_overview import overview_map, trip_table


def search(stamp="2026-10-01T10:00:00+00:00"):
    return {"username": "jeanpaulboerekamps", "start": "2025-01-01", "end": "2025-01-10",
            "places": [], "geometry": json.dumps({"type": "Polygon", "coordinates": [
                [[4, 51], [6, 51], [6, 53], [4, 53], [4, 51]]]}), "calculated_at": stamp,
            "heat_points": [[52, 5]]}


def summary(species=4):
    return {"observations": 10, "species": species, "unidentified": 10-species,
            "own": 3, "area": 2, "global": 1, "unresolved": 0}


class StoreTests(unittest.TestCase):
    def test_new_version_preserves_old_numbers_and_uses_latest_date(self):
        first = make_record("Reis", search(), summary())
        original = deepcopy(first)
        latest = make_record("Reis", search("2026-10-02T10:00:00+00:00"), summary(6), existing=first)
        self.assertEqual(first, original)
        self.assertEqual([v["summary"]["species"] for v in latest["versions"]], [4, 6])
        self.assertEqual(latest["summary"]["species"], 6)
        self.assertEqual(latest["id"], first["id"])
        self.assertNotIn("heat_points", latest["search"])
        older = make_record("Reis", search("2026-09-01T10:00:00+00:00"), summary(3), existing=latest)
        self.assertEqual(older["summary"]["species"], 6)
        self.assertEqual(trip_table([older])[0]["Soorten"], 6)

    def test_repeated_save_is_idempotent(self):
        first = make_record("Reis", search(), summary())
        repeated = make_record("Reis", search(), summary(7), existing=first)
        self.assertEqual(repeated["versions"], first["versions"])
        self.assertEqual(repeated["summary"], first["summary"])

    def test_legacy_backup_retains_undated_snapshot(self):
        row = make_record("Reis", search(), summary())
        del row["versions"]
        del row["search"]["calculated_at"]
        migrated = validate_import(json.dumps([row]))[0]
        self.assertIsNone(migrated["versions"][0]["calculated_at"])
        updated = make_record("Reis", search(), summary(6), existing=migrated)
        self.assertEqual(len(updated["versions"]), 2)
        self.assertEqual(updated["versions"][0]["summary"]["species"], 4)

    def test_import_old_backup_never_removes_newer_version(self):
        first = make_record("Reis", search(), summary())
        latest = make_record("Reis", search("2026-10-02T10:00:00+00:00"), summary(6), existing=first)
        result = merge_records([latest], validate_import(json.dumps([first])))[0]
        self.assertEqual(len(result["versions"]), 2)
        self.assertEqual(result["summary"]["species"], 6)
        self.assertEqual(validate_import(json.dumps([result])), [normalize_record(result)])

    def test_new_geometry_stays_same_trip_but_changed_period_does_not(self):
        first = make_record("Reis", search(), summary())
        changed = search("2026-10-02T10:00:00+00:00")
        changed["geometry"] = ""
        self.assertTrue(same_trip(changed, first["search"]))
        changed["end"] = "2025-01-11"
        with self.assertRaises(ValueError):
            make_record("Reis", changed, summary(), existing=first)

    def test_invalid_version_rejected(self):
        row = make_record("Reis", search(), summary())
        row["versions"][0]["summary"]["species"] = -1
        with self.assertRaises(ValueError):
            validate_import(json.dumps([row]))
        row = make_record("Reis", search(), summary())
        row["versions"][0]["search"]["username"] = "someone_else"
        with self.assertRaises(ValueError):
            validate_import(json.dumps([row]))

    def test_map_has_marker_and_handles_missing_and_invalid_geometry(self):
        first = make_record("<Reis>", search(), summary())
        missing = deepcopy(first)
        missing["versions"][0]["search"]["geometry"] = ""
        missing["versions"][0]["search"].pop("map_location", None)
        invalid = deepcopy(missing)
        invalid["versions"][0]["search"]["geometry"] = "invalid JSON"
        world, omitted = overview_map([first, missing, invalid])
        self.assertEqual(omitted, 2)
        markup = world.get_root().render()
        self.assertIn("&lt;Reis&gt;", markup)
        self.assertIn("10 waarnemingen", markup)

    def test_rename_preserves_trip_identity_and_every_version(self):
        first = make_record('Reis', search(), summary())
        latest = make_record('Reis', search('2026-10-02T10:00:00+00:00'), summary(6), existing=first)
        renamed = rename_record(latest, '  Nieuwe naam  ')
        self.assertEqual(renamed['name'], 'Nieuwe naam')
        self.assertEqual(renamed['versions'], latest['versions'])
        self.assertEqual(renamed['id'], latest['id'])
        self.assertEqual(latest['name'], 'Reis')
        for value in (' ', 'a'*121):
            with self.assertRaises(ValueError):
                rename_record(latest, value)

    def test_sort_numeric_and_missing_values(self):
        low = make_record('z', search(), summary(2))
        high = make_record('A', search(), summary(7))
        unknown = deepcopy(low)
        unknown['id'] = 'unknown'
        unknown['versions'][0]['summary']['area'] = None
        self.assertEqual([r['name'] for r in sorted_trips([low, high], 'Trip', False)], ['A', 'z'])
        self.assertEqual([r['name'] for r in sorted_trips([low, high], 'Soorten', True)], ['A', 'z'])
        for descending in (True, False):
            self.assertEqual(sorted_trips([unknown, low], 'Nieuw in gebied', descending)[-1]['id'], 'unknown')

    def test_sort_calculation_date_is_chronological(self):
        earlier = make_record('Earlier', search('2026-02-28T10:00:00+00:00'), summary())
        later = make_record('Later', search('2026-03-01T10:00:00+00:00'), summary())
        undated = deepcopy(earlier)
        undated['versions'][0]['calculated_at'] = None
        undated['name'] = 'Undated'
        self.assertEqual([r['name'] for r in sorted_trips([earlier, undated, later], 'Berekend op', True)],
                         ['Later', 'Earlier', 'Undated'])


if __name__ == "__main__":
    unittest.main()
