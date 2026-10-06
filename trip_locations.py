"""Recover a map location for older trips without stored geographical metadata."""
from datetime import date, time
import math
import json

from shapely.geometry import shape
from shapely import make_valid
from trip_data import get
from trip_map import select_time_window, observation_points
from trip_store import normalize_record, version_key


def valid_location(value):
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        lat, lon = float(value[0]), float(value[1])
        if math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180:
            return [lat, lon]
    except (ValueError, TypeError):
        pass
    return None


def stored_trip_location(raw):
    row = normalize_record(raw)
    for version in sorted(row['versions'], key=version_key, reverse=True):
        search = version['search']
        location = valid_location(search.get('map_location'))
        if location:
            return location
        points = search.get('heat_points') or []
        for point in points:
            location = valid_location(point)
            if location:
                return location
        geometry = search.get('geometry')
        try:
            geometry = json.loads(geometry) if isinstance(geometry, str) and geometry else geometry
            if geometry and geometry.get('type') == 'Feature':
                geometry = geometry.get('geometry')
            region = shape(geometry) if geometry else None
            if region is not None and not region.is_empty:
                if not region.is_valid:
                    region = make_valid(region)
                point = region.representative_point()
                location = valid_location([point.y, point.x])
                if location:
                    return location
        except (ValueError, TypeError, KeyError, AttributeError):
            pass
    return valid_location(row.get('map_location'))


def recover_trip_location(search):
    """Find one public observation in the original trip period, without species checks.

    Pagination skips observations outside partial boundary days. Old place filters
    are retained; no location is guessed from a trip name.
    """
    places = search.get('places') or [None]
    for place_id in places:
        params = {'user_id': search['username'], 'd1': search['start'], 'd2': search['end'],
                  'per_page': 200, 'order_by': 'observed_on', 'order': 'asc'}
        if place_id is not None:
            params['place_id'] = place_id
        for page in range(1, 51):  # Same 10,000-result API limit as the existing trip fetcher.
            response = get('/observations', {**params, 'page': page})
            results = response.get('results') or []
            selected, _ = select_time_window(results, date.fromisoformat(search['start']),
                                             date.fromisoformat(search['end']),
                                             time.fromisoformat(search.get('start_time', '00:00')),
                                             time.fromisoformat(search.get('end_time', '23:59')))
            for point in observation_points(selected):
                location = valid_location(point)
                if location:
                    return location
            if not results or page * 200 >= response.get('total_results', len(results)):
                break
    return None
