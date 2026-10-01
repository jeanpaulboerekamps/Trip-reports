"""25 km neighbourhoods and independent historical first-record counts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from functools import lru_cache
import numpy as np
from trip_data import get, _first, _prior_species
from trip_map import observation_points


def concentration_circles(observations, frame):
    species = {oid: int(row.species_id) for row in frame.itertuples() for oid in row.obs_ids}
    records = []
    for obs in observations:
        points = observation_points([obs])
        if points:
            records.append({'id': obs['id'], 'point': points[0],
                            'species': species.get(obs['id']), 'places': obs.get('place_ids') or []})
    if not records:
        return [], records
    coords = np.radians([r['point'] for r in records])
    centres = np.unique(coords, axis=0)
    neighbours = []
    for chunk in np.array_split(centres, max(1, (len(centres)+127)//128)):
        delta = chunk[:, None, :] - coords[None, :, :]
        hav = np.sin(delta[:,:,0]/2)**2 + np.cos(chunk[:,None,0])*np.cos(coords[None,:,0])*np.sin(delta[:,:,1]/2)**2
        for row in hav:
            neighbours.append(np.flatnonzero(row <= np.sin(25/6371.0088/2)**2).tolist())
    available = set(range(len(centres)))
    circles = []
    while available:
        index = min(available, key=lambda i: (-len(neighbours[i]), i))
        members = neighbours[index]
        if len(members) <= 25:
            break
        lat, lon = np.degrees(centres[index]).tolist()
        circles.append({'lat': lat, 'lon': lon, 'members': members, 'observations': len(members),
                        'species': len({records[i]['species'] for i in members if records[i]['species'] is not None})})
        # Keep distinct centres: a dense neighbourhood gets one label, not one per photo.
        delta = centres - centres[index]
        hav = np.sin(delta[:,0]/2)**2 + np.cos(centres[:,0])*np.cos(centres[index,0])*np.sin(delta[:,1]/2)**2
        available.difference_update(np.flatnonzero(hav <= np.sin(25/6371.0088/2)**2).tolist())
    return circles, records


@lru_cache(maxsize=8192)
def first_id(sid, end, user=None, country=None):
    params = {'taxon_id': sid, 'd2': end}
    if user is not None:
        params['user_id'] = user
    if country is not None:
        params['place_id'] = country
    row = _first(params)
    return row['id'] if row else 0


def enrich_circles(circles, records, user, start, end, progress=None):
    if not circles:
        return []
    selected = {i for c in circles for i in c['members']}
    place_ids = sorted({p for i in selected for p in records[i]['places']})
    countries = {}
    country_lookup_complete = True
    for offset in range(0, len(place_ids), 50):
        try:
            rows = get('/places/' + ','.join(map(str, place_ids[offset:offset+50])), {'admin_level': 0}).get('results', [])
            countries.update({p['id']: p.get('display_name') or p.get('name') or str(p['id'])
                              for p in rows if p.get('admin_level') == 0})
        except Exception:
            country_lookup_complete = False
    for i in selected:
        records[i]['countries'] = set(records[i]['places']) & countries.keys()
    all_species = {records[i]['species'] for i in selected if records[i]['species'] is not None}
    scopes = [('own', user, None, all_species), ('global', None, None, all_species)]
    for country in sorted(countries):
        ids = {records[i]['species'] for i in selected if country in records[i]['countries'] and records[i]['species'] is not None}
        if ids:
            scopes.append(('country', None, country, ids))
    history = {}
    cutoff = (date.fromisoformat(start)-timedelta(days=1)).isoformat()
    for kind, owner, country, ids in scopes:
        filters = {'user_id': owner} if owner is not None else {'place_id': country} if country is not None else {}
        try:
            ordered_ids = sorted(ids)
            old = set()
            for offset in range(0, len(ordered_ids), 80):
                old.update(_prior_species(ordered_ids[offset:offset+80], cutoff, **filters))
        except Exception:
            old = set()  # Exact first-record queries still establish the result.
        for sid in old:
            history[kind, country, sid] = 0
        def check(sid):
            try:
                value = first_id(sid, end, owner, country)
            except Exception:
                value = None
            return sid, value
        with ThreadPoolExecutor(max_workers=4) as pool:
            for sid, value in pool.map(check, sorted(ids-old)):
                history[kind, country, sid] = value
                if progress:
                    progress(kind)
    result = []
    for number, circle in enumerate(circles, 1):
        members = [records[i] for i in circle['members']]
        species_ids = {r['species'] for r in members if r['species'] is not None}
        observed_ids = {r['id'] for r in members}
        stats = {}
        for kind in ('own', 'global'):
            values = [history[kind, None, sid] for sid in species_ids]
            count = sum(v in observed_ids for v in values if v is not None)
            stats[kind] = str(count) if all(v is not None for v in values) else f'>={count} (?)'
        new_country, unknown = set(), not country_lookup_complete
        for sid in species_ids:
            rows = [r for r in members if r['species'] == sid]
            for row in rows:
                if not row['countries']:
                    unknown = True
            for country in {p for r in rows for p in r['countries']}:
                value = history['country', country, sid]
                if value is None:
                    unknown = True
                elif any(r['id'] == value and country in r['countries'] for r in rows):
                    new_country.add(sid)
        stats['country'] = str(len(new_country)) if not unknown else f'>={len(new_country)} (?)'
        result.append({k: v for k, v in circle.items() if k != 'members'} | stats | {
            'number': number, 'countries': ', '.join(sorted({countries[p] for r in members for p in r['countries']}))})
    return result


def circle_lines(circle):
    return [f"{circle['observations']} waarnemingen", f"{circle['species']} soorten",
            f"{circle.get('own', '?')} nieuw voor mij", f"{circle.get('country', '?')} nieuw voor land",
            f"{circle.get('global', '?')} nieuw op iNaturalist"]
