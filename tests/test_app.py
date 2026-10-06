from pathlib import Path
import unittest
from copy import deepcopy
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
        self.assertEqual(list(at.dataframe[1].value['Soorten']), [6, 4])
        self.button(at, 'Nieuwe versie berekenen').click().run()
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


if __name__ == '__main__':
    unittest.main()
