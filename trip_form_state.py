"""Single transition point for trip form values (independent of Streamlit UI)."""
from datetime import date, time

DEFAULT_USERNAME = 'jeanpaulboerekamps'


def load_existing_trip(state, row):
    """Populate both canonical values and widget values before showing the form."""
    saved = row['search']
    trip_id = row['id']
    name = row['name']
    username = saved['username']
    state['trip_name'] = name
    state['trip_username'] = username
    state['trip_start'] = date.fromisoformat(saved['start'])
    state['trip_end'] = date.fromisoformat(saved['end'])
    state['trip_start_time'] = time.fromisoformat(saved.get('start_time', '00:00'))
    state['trip_end_time'] = time.fromisoformat(saved.get('end_time', '23:59'))
    state['trip_name_form_' + trip_id] = name
    state['trip_username_form_' + trip_id] = username
    state['saved_trip_id'] = trip_id
    state['saved_search'] = saved


def form_widget_keys(state):
    suffix = state.get('saved_trip_id') or 'new'
    return 'trip_name_form_' + suffix, 'trip_username_form_' + suffix


def prepare_form_widgets(state):
    """Initialize absent widgets without ever replacing a user edit on rerun."""
    name_key, username_key = form_widget_keys(state)
    if name_key not in state:
        state[name_key] = state.get('trip_name', '')
    if username_key not in state:
        state[username_key] = state.get('trip_username', DEFAULT_USERNAME)
    return name_key, username_key


def sync_form_values(state):
    name_key, username_key = prepare_form_widgets(state)
    state['trip_name'] = state[name_key]
    state['trip_username'] = state[username_key].strip()
