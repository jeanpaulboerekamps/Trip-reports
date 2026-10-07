from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from trip_store import make_record
from trip_table_ui import table_payload
from test_trip_store import search, summary


class AppTests(unittest.TestCase):
    def start(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
        at.run()
        self.assertFalse(at.exception)
        return at

    def button(self, at, label):
        return next(b for b in at.button if b.label == label)

    def test_home_is_default_and_new_trip_opens_form(self):
        at = self.start()
        self.assertEqual(at.text_input[0].value, 'jeanpaulboerekamps')
        self.assertEqual(at.session_state.page, 'home')
        self.button(at, 'Nieuwe trip').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, 'report')
        self.assertEqual(at.text_input[1].value, 'jeanpaulboerekamps')
        self.button(at, '← Mijn trips').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, 'home')

    def test_latest_counts_history_user_filter_and_load_existing_trip(self):
        at = self.start()
        first = make_record('Reis', search(), summary())
        latest = make_record('Reis', search('2026-10-02T10:00:00+00:00'), summary(6), existing=first)
        other_search = search()
        other_search['username'] = 'ander'
        other = make_record('Andere reis', other_search, summary())
        at.session_state.saved_rows = [latest, other]
        with patch('trip_table_ui._table', return_value=None) as table:
            at.run()
            rows = table.call_args.kwargs['rows']
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['cells']['Soorten'], ['6'])
            self.assertNotIn('Opnieuw berekenen', [b.label for b in at.button])
            context = table.call_args.kwargs['context']
        event = {'selected_id':first['id'], 'context':context, 'nonce':'click-1'}
        with patch('trip_table_ui._table', return_value=event):
            at.run()
            self.assertFalse(at.exception)
            self.assertEqual(list(at.dataframe[0].value['Soorten']), [6, 4])
            self.button(at, 'Opnieuw berekenen').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.saved_trip_id, first['id'])
        self.assertEqual(at.text_input[0].value, 'Reis')
        self.assertEqual(at.session_state.trip_start.isoformat(), '2025-01-01')

    def test_user_filter_survives_form_navigation(self):
        at = self.start()
        at.text_input[0].set_value('ander').run()
        self.button(at, 'Nieuwe trip').click().run()
        self.assertEqual(at.text_input[1].value, 'ander')
        self.button(at, '← Mijn trips').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.text_input[0].value, 'ander')

    def test_blank_old_username_is_replaced_on_upgrade(self):
        at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'app.py'), default_timeout=20)
        at.session_state.overview_username = ''
        at.session_state.overview_user_filter = ''
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.text_input[0].value, 'jeanpaulboerekamps')
        at.text_input[0].set_value('   ').run()
        self.assertEqual(at.text_input[0].value, 'jeanpaulboerekamps')

    def test_delete_only_available_after_selection_and_targets_one_trip(self):
        at = self.start()
        first = make_record('Reis', search(), summary())
        other = make_record('Tweede reis', search(), summary())
        at.session_state.saved_rows = [first, other]
        at.run()
        self.assertNotIn('Trip verwijderen', [b.label for b in at.button])
        at.session_state.selected_overview_trip_id = other['id']
        at.run()
        self.button(at, 'Trip verwijderen').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.storage_action['op'], 'delete')
        self.assertEqual(at.session_state.storage_action['trip_id'], other['id'])

    def test_missing_legacy_map_location_is_recovered_without_new_version(self):
        at = self.start()
        settings = search()
        settings['geometry'] = ''
        settings.pop('heat_points', None)
        row = make_record('Sulawesi', settings, summary())
        row.pop('versions')
        row['search'].pop('calculated_at')
        at.session_state.saved_rows = [row]
        observations = [{'id': 1, 'observed_on': '2025-01-05', 'geojson': {'coordinates': [120.3, -1.4]}}]
        with patch('trip_locations.trip_observations', return_value=observations), patch('trip_table_ui._table', return_value=None) as table:
            at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.storage_action['op'], 'locations')
        self.assertAlmostEqual(at.session_state.saved_rows[0]['map_location'][1], 120.3)
        self.assertEqual(table.call_args.kwargs['rows'][0]['cells']['Soorten'], ['4'])
        self.assertEqual(table.call_args.kwargs['rows'][0]['cells']['Versies'], ['1'])

    def test_selected_trip_can_be_renamed_without_recalculation(self):
        at = self.start()
        row = make_record('Reis', search(), summary())
        at.session_state.saved_rows = [row]
        at.session_state.selected_overview_trip_id = row['id']
        at.run()
        name_input = next(w for w in at.text_input if w.label == 'Tripnaam wijzigen')
        name_input.set_value('Nieuwe naam')
        self.button(at, 'Naam opslaan').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.storage_action['op'], 'rename')
        self.assertEqual(at.session_state.storage_action['trip_id'], row['id'])
        self.assertEqual(at.session_state.storage_action['name'], 'Nieuwe naam')

    def test_sort_controls_change_row_order_without_changing_selection(self):
        at = self.start()
        low = make_record('Z-trip', search(), summary(2))
        high = make_record('A-trip', search(), summary(7))
        at.session_state.saved_rows = [low, high]
        at.session_state.selected_overview_trip_id = low['id']
        with patch('trip_table_ui._table', return_value=None) as table:
            at.run()
            next(w for w in at.selectbox if w.label == 'Sorteren op').set_value('Soorten').run()
            self.assertEqual([r['cells']['Soorten'] for r in table.call_args.kwargs['rows']], [['7'], ['2']])
            at.radio[0].set_value('Oplopend').run()
            self.assertEqual([r['cells']['Soorten'] for r in table.call_args.kwargs['rows']], [['2'], ['7']])
        self.assertEqual(at.session_state.selected_overview_trip_id, low['id'])
        self.assertIn('Z-trip', [w.value for w in at.subheader])

    def test_stale_or_unknown_selection_does_not_open_wrong_trip(self):
        at = self.start()
        row = make_record('Reis', search(), summary())
        at.session_state.saved_rows = [row]
        with patch('trip_table_ui._table', return_value={'selected_id':row['id'], 'context':'wrong-filter', 'nonce':'stale'}):
            at.run()
        self.assertNotIn('Trip verwijderen', [b.label for b in at.button])
        at.session_state.selected_overview_trip_id = 'missing-id'
        at.run()
        self.assertNotIn('Trip verwijderen', [b.label for b in at.button])

    def test_map_view_controls_allow_europe_and_indian_ocean(self):
        at = self.start()
        control = next(w for w in at.selectbox if w.label == 'Kaartgebied')
        for area in ['Europa', 'Midden-Oosten en Indische Oceaan', 'Alle trips']:
            control.set_value(area).run()
            self.assertFalse(at.exception)


if __name__ == '__main__':
    unittest.main()
