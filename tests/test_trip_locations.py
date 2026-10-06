import unittest
from unittest.mock import patch
from copy import deepcopy

from trip_locations import recover_trip_location, stored_trip_location
from trip_store import make_record
from trip_overview import overview_map
from test_trip_store import search, summary


class LocationTests(unittest.TestCase):
    def legacy(self):
        settings = search()
        settings['geometry'] = ''
        settings.pop('heat_points', None)
        row = make_record('Sulawesi', settings, summary())
        row.pop('versions')
        row['search'].pop('calculated_at')
        return row

    def test_legacy_location_recovered_without_modifying_counts(self):
        row = self.legacy()
        original = deepcopy(row)
        result = {'total_results': 1, 'results': [{'id': 1, 'observed_on': '2025-01-05',
                   'geojson': {'coordinates': [120.3, -1.4]}}]}
        with patch('trip_locations.get', return_value=result) as get:
            location = recover_trip_location(row['search'])
            self.assertAlmostEqual(location[0], -1.4)
            self.assertAlmostEqual(location[1], 120.3)
            self.assertEqual(get.call_args.args[1]['user_id'], 'jeanpaulboerekamps')
        self.assertEqual(row, original)
        row['map_location'] = location
        self.assertEqual(stored_trip_location(row), location)
        world, missing = overview_map([row])
        self.assertEqual(missing, 0)
        self.assertIn('Sulawesi', world.get_root().render())

    def test_map_frames_both_italy_and_sulawesi(self):
        italy = make_record('Italië', search(), summary())
        sulawesi = self.legacy()
        sulawesi['map_location'] = [-1.4, 120.3]
        world, missing = overview_map([italy, sulawesi])
        self.assertEqual(missing, 0)
        markup = world.get_root().render()
        self.assertIn('120.3', markup)
        self.assertIn('52.0', markup)
        self.assertIn('fitBounds', markup)
        self.assertIn('circleMarker', markup)

    def test_partial_day_skips_outside_times_and_paginates(self):
        row = self.legacy()
        row['search'].update(start_time='12:00', end_time='23:59')
        first = {'id': 1, 'observed_on': '2025-01-01', 'time_observed_at': '2025-01-01T09:00:00+00:00',
                 'geojson': {'coordinates': [5, 52]}}
        second = {'id': 201, 'observed_on': '2025-01-02', 'geojson': {'coordinates': [120.3, -1.4]}}
        with patch('trip_locations.get', side_effect=[{'total_results': 201, 'results': [first]*200},
                                                     {'total_results': 201, 'results': [second]}]) as get:
            location = recover_trip_location(row['search'])
            self.assertAlmostEqual(location[0], -1.4)
            self.assertAlmostEqual(location[1], 120.3)
            self.assertEqual(get.call_count, 2)

    def test_no_public_locations_remains_missing_and_failure_propagates(self):
        row = self.legacy()
        with patch('trip_locations.get', return_value={'results': [], 'total_results': 0}):
            self.assertIsNone(recover_trip_location(row['search']))
        with patch('trip_locations.get', side_effect=RuntimeError('Offline')):
            with self.assertRaises(RuntimeError):
                recover_trip_location(row['search'])

    def test_legacy_place_filter_is_preserved(self):
        row = self.legacy()
        row['search']['places'] = [99]
        with patch('trip_locations.get', return_value={'results': [], 'total_results': 0}) as get:
            recover_trip_location(row['search'])
            self.assertEqual(get.call_args.args[1]['place_id'], 99)


if __name__ == '__main__':
    unittest.main()
