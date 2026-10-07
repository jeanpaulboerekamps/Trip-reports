from pathlib import Path
import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import streamlit as st
from streamlit.testing.v1 import AppTest
from trip_store import make_record
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
        at.run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.dataframe[0].value), 1)
        self.assertEqual(at.dataframe[0].value.iloc[0]['Soorten'], 6)
        self.assertEqual(len(at.dataframe), 1)
        self.assertNotIn('Opnieuw berekenen', [b.label for b in at.button])
        self.assertNotIn('Trip verwijderen', [b.label for b in at.button])
        # AppTest cannot send dataframe selection events; simulate its return value.
        real_dataframe = st.dataframe
        def selected_dataframe(*args, **kwargs):
            value = real_dataframe(*args, **kwargs)
            if kwargs.get('on_select'):
                return SimpleNamespace(selection=SimpleNamespace(rows=[0]))
            return value
        with patch.object(st, 'dataframe', side_effect=selected_dataframe):
            at.run()
            self.assertFalse(at.exception)
            self.assertEqual(list(at.dataframe[1].value['Soorten']), [6, 4])
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
        real_dataframe = st.dataframe
        def selected_dataframe(*args, **kwargs):
            value = real_dataframe(*args, **kwargs)
            if kwargs.get('on_select'):
                return SimpleNamespace(selection=SimpleNamespace(rows=[1]))
            return value
        with patch.object(st, 'dataframe', side_effect=selected_dataframe):
            at.run()
            self.button(at, 'Trip verwijderen').click().run()
            self.assertFalse(at.exception)
            self.assertEqual(at.session_state.storage_action['op'], 'delete')
            self.assertEqual(at.session_state.storage_action['trip_id'], other['id'])

    def test_missing_legacy_map_location_is_recovered_and_saved_without_new_version(self):
        at = self.start()
        settings = search()
        settings['geometry'] = ''
        settings.pop('heat_points', None)
        row = make_record('Sulawesi', settings, summary())
        row.pop('versions')
        row['search'].pop('calculated_at')
        at.session_state.saved_rows = [row]
        response = {'total_results': 1, 'results': [{'id': 1, 'observed_on': '2025-01-05',
                    'geojson': {'coordinates': [120.3, -1.4]}}]}
        with patch('trip_locations.trip_observations', return_value=response['results']):
            at.run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.storage_action['op'], 'locations')
        self.assertAlmostEqual(at.session_state.saved_rows[0]['map_location'][1], 120.3)
        self.assertEqual(at.dataframe[0].value.iloc[0]['Soorten'], 4)
        self.assertEqual(at.dataframe[0].value.iloc[0]['Versies'], 1)

    def test_selected_trip_can_be_renamed_without_recalculation(self):
        at = self.start()
        row = make_record('Reis', search(), summary())
        at.session_state.saved_rows = [row]
        real_dataframe = st.dataframe
        def selected_dataframe(*args, **kwargs):
            value = real_dataframe(*args, **kwargs)
            if kwargs.get('on_select'):
                return SimpleNamespace(selection=SimpleNamespace(rows=[0]))
            return value
        with patch.object(st, 'dataframe', side_effect=selected_dataframe):
            at.run()
            name_input = next(w for w in at.text_input if w.label == 'Tripnaam wijzigen')
            name_input.set_value('Nieuwe naam')
            self.button(at, 'Naam opslaan').click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.storage_action['op'], 'rename')
        self.assertEqual(at.session_state.storage_action['trip_id'], row['id'])
        self.assertEqual(at.session_state.storage_action['name'], 'Nieuwe naam')

    def test_sort_controls_change_row_order(self):
        at = self.start()
        low = make_record('Z-trip', search(), summary(2))
        high = make_record('A-trip', search(), summary(7))
        at.session_state.saved_rows = [low, high]
        at.run()
        at.selectbox[0].set_value('Soorten').run()
        self.assertEqual(list(at.dataframe[0].value['Soorten']), [7, 2])
        at.radio[0].set_value('Oplopend').run()
        self.assertEqual(list(at.dataframe[0].value['Soorten']), [2, 7])


if __name__ == '__main__':
    unittest.main()
