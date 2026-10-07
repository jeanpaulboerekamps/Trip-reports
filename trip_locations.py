"""Recover a map location for older trips without stored geographical metadata."""
from datetime import date, time
import math
import json

from shapely.geometry import shape
from shapely import make_valid
import numpy as np
from trip_data import trip_observations
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


DENSITY_METHOD = "density-25km-v1"


def busiest_location(points):
    """Actual observation coordinate with the most observations within 25 km.

    Each observation counts, including repeat coordinates and unidentified records.
    Work in bounded chunks; resolve ties by coordinate order for stable markers.
    """
    locations = [location for point in points if (location := valid_location(point))]
    if not locations:
        return None
    coords, weights = np.unique(np.radians(locations), axis=0, return_counts=True)
    threshold = np.sin(25 / 6371.0088 / 2) ** 2
    best_count, best_index = -1, 0
    # Chunk both axes so even large trips do not allocate an N x N matrix.
    for offset in range(0, len(coords), 128):
        centres = coords[offset:offset + 128]
        counts = np.zeros(len(centres), dtype=np.int64)
        for start in range(0, len(coords), 2048):
            neighbours = coords[start:start + 2048]
            delta = centres[:, None, :] - neighbours[None, :, :]
            hav = (np.sin(delta[:, :, 0] / 2) ** 2 + np.cos(centres[:, None, 0])
                   * np.cos(neighbours[None, :, 0]) * np.sin(delta[:, :, 1] / 2) ** 2)
            counts += (hav <= threshold) @ weights[start:start + 2048]
        index = int(np.argmax(counts))
        if int(counts[index]) > best_count:
            best_count, best_index = int(counts[index]), offset + index
    return np.degrees(coords[best_index]).tolist()


def has_density_location(raw):
    row = normalize_record(raw)
    latest = max(row['versions'], key=version_key)
    return bool((latest['search'].get('map_location_method') == DENSITY_METHOD
                 and valid_location(latest['search'].get('map_location')))
                or (row.get('map_location_method') == DENSITY_METHOD
                    and valid_location(row.get('map_location'))))


def stored_trip_location(raw):
    row = normalize_record(raw)
    latest = max(row['versions'], key=version_key)
    if latest['search'].get('map_location_method') == DENSITY_METHOD:
        location = valid_location(latest['search'].get('map_location'))
        if location:
            return location
    if row.get('map_location_method') == DENSITY_METHOD:
        location = valid_location(row.get('map_location'))
        if location:
            return location
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
    """Fetch all trip locations to find the density peak; preserve original scope."""
    start, end = date.fromisoformat(search['start']), date.fromisoformat(search['end'])
    geometry = search.get('geometry')
    geometry = json.loads(geometry) if isinstance(geometry, str) and geometry else geometry
    if geometry and geometry.get('type') == 'Feature':
        geometry = geometry.get('geometry')
    if geometry:
        region = shape(geometry)
        if not region.is_valid:
            from shapely.geometry import mapping
            geometry = mapping(make_valid(region))
    observations = trip_observations(search['username'].strip(), start, end,
                                     tuple(search.get('places') or []), geometry)
    selected, _ = select_time_window(observations, start, end,
                                     time.fromisoformat(search.get('start_time', '00:00')),
                                     time.fromisoformat(search.get('end_time', '23:59')))
    return busiest_location(observation_points(selected))
