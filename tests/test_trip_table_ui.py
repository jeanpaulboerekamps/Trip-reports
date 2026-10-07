import unittest
from copy import deepcopy
from pathlib import Path
from trip_table_ui import COLUMNS, table_payload
from trip_overview import trip_table, overview_map
from test_trip_store import search, summary
from trip_store import make_record


class TableLayoutTests(unittest.TestCase):
    def test_metadata_columns_are_last_and_headers_wrap(self):
        row = make_record('Reis', search(), summary())
        keys = [c['key'] for c in COLUMNS]
        self.assertEqual(keys[-2:], ['Berekend op', 'Versies'])
        self.assertEqual(list(trip_table([row])[0]), keys)
        self.assertGreater(len(next(c for c in COLUMNS if c['key'] == 'Nieuw voor mij')['lines']), 1)
        self.assertLessEqual(sum(c['width'] for c in COLUMNS), 1100)

    def test_payload_preserves_ids_typed_sorting_and_datetime_lines(self):
        row = make_record('<script>test</script>', search(), summary())
        data = table_payload([row])[0]
        self.assertEqual(data['id'], row['id'])
        self.assertEqual(data['cells']['Trip'], ['<script>test</script>'])
        self.assertIsInstance(data['sort_values']['Soorten'], int)
        self.assertIsInstance(data['sort_values']['Berekend op'], float)
        self.assertEqual(len(data['cells']['Berekend op']), 2)
        self.assertEqual(data['sort_values']['Van'], '2025-01-01')

    def test_map_never_clusters_distant_trips(self):
        first = make_record('Oman', search(), summary())
        second = deepcopy(first)
        second['id'] = 'maldives'
        second['name'] = 'Malediven'
        first['versions'][0]['search']['map_location'] = [23.6, 58.5]
        second['versions'][0]['search']['map_location'] = [4.2, 73.5]
        world, missing = overview_map([first, second])
        markup = world.get_root().render()
        self.assertEqual(missing, 0)
        self.assertNotIn('markerClusterGroup', markup)
        self.assertEqual(markup.count('L.circleMarker('), 2)
        self.assertIn('23.6', markup)
        self.assertIn('73.5', markup)
        self.assertIn('nearby.length', markup)

    def test_regional_map_view_changes_bounds(self):
        world, _ = overview_map([], view='Europa')
        self.assertIn('[[28, -25], [72, 45]]', world.get_root().render())
        world, _ = overview_map([], view='Midden-Oosten en Indische Oceaan')
        self.assertIn('[[-10, 35], [35, 90]]', world.get_root().render())


if __name__ == '__main__':
    unittest.main()
