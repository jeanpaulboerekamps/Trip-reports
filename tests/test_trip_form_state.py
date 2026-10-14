import unittest
from trip_form_state import load_existing_trip, prepare_form_widgets, sync_form_values

class TripFormStateTests(unittest.TestCase):
    def setUp(self):
        self.row = {'id':'abc','name':'Alpen', 'search': {'username':'jeanpaulboerekamps', 'start':'2012-08-11','end':'2012-08-17'}}

    def test_existing_trip_populates_both_fields_and_dates(self):
        state = {'trip_name':'', 'trip_username':''}
        load_existing_trip(state, self.row)
        self.assertEqual(state['trip_name_form_abc'],'Alpen')
        self.assertEqual(state['trip_username_form_abc'],'jeanpaulboerekamps')
        self.assertEqual(state['trip_start'].isoformat(),'2012-08-11')
        self.assertEqual(prepare_form_widgets(state),('trip_name_form_abc','trip_username_form_abc'))

    def test_user_edits_survive_rerun(self):
        state = {}
        load_existing_trip(state, self.row)
        state['trip_name_form_abc'] = 'Nieuwe naam'
        prepare_form_widgets(state)
        sync_form_values(state)
        self.assertEqual(state['trip_name'],'Nieuwe naam')

    def test_switching_between_saved_trips_does_not_leak_values(self):
        state = {}
        load_existing_trip(state, self.row)
        other = {'id':'xyz','name':'Bali','search':{'username':'andere_gebruiker','start':'2012-07-09','end':'2012-07-31'}}
        load_existing_trip(state, other)
        self.assertEqual(state['trip_name_form_xyz'],'Bali')
        self.assertEqual(state['trip_username_form_xyz'],'andere_gebruiker')
        load_existing_trip(state, self.row)
        self.assertEqual(state['trip_name_form_abc'],'Alpen')

if __name__ == '__main__': unittest.main()
