"""Resumable server jobs. Workers never call Streamlit."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, time as clock, timedelta, datetime, timezone
from pathlib import Path
from threading import Lock
import hashlib
import json
import pickle
import tempfile
import time
from uuid import uuid4
import pandas as pd
from concentrations import concentration_circles, personal_circles, full_circles
from trip_data import resolve_username, trip_observations, species_frame, personal_species_counts, own_firsts_in_window, batch_stars, _prior_species, refresh_trip_rg
from trip_map import observation_points, select_time_window, infer_trip_area


def build_report(search, progress, checkpoint=None, save=None):
    state = checkpoint if checkpoint is not None else {}
    save = save or (lambda state: None)
    username, start, end, start_time, end_time = search[:5]
    map_extended = bool(search[5]) if len(search) > 5 else False
    trip_name = str(search[6]).strip() if len(search) > 6 else ''
    if len(search)>6 and (not trip_name or len(trip_name)>120):
        raise ValueError('Vul een naam voor deze trip in (maximaal 120 tekens).')
    extended = True  # Totals and species stars are always fully checked.
    start, end = date.fromisoformat(start), date.fromisoformat(end)
    start_time, end_time = clock.fromisoformat(start_time), clock.fromisoformat(end_time)
    def stage(name, message, operation):
        if name not in state:
            progress(message)
            state[name] = operation()
            save(state)
        return state[name]
    account = stage('account', 'iNaturalist-gebruikersnaam controleren…', lambda: resolve_username(username))
    user = account['id']
    candidates = stage('candidates', 'Waarnemingen ophalen…', lambda: trip_observations(user, start, end,
        on_page=lambda page,total,count: progress(f'Waarnemingen ophalen: pagina {page} van {total} ({count:,} waarnemingen)')))
    observations, unknown = select_time_window(candidates, start, end, start_time, end_time)
    points = observation_points(observations)
    geometry = infer_trip_area(points)
    frame = stage('frame', f'{len(observations):,} waarnemingen opgehaald; soorten opbouwen…', lambda: species_frame(observations)).copy()
    firsts = own_firsts_in_window(user, start, end, frame['species_id'], trip_observations_all=candidates)
    warnings = state.setdefault('warnings', [])
    ids = sorted(int(sid) for sid in frame['species_id'])
    prior = state.setdefault('own_prior', {})
    cutoff = (start-timedelta(days=1)).isoformat()
    for offset in range(0, len(ids), 80):
        batch = ids[offset:offset+80]
        if all(sid in prior for sid in batch):
            continue
        progress(f'Nieuw voor mij: {offset} van {len(ids)} soorten; groepscontrole')
        try:
            old = _prior_species(batch, cutoff, user_id=user)
            prior.update({sid: sid in old for sid in batch})
        except Exception as exc:
            prior.update({sid: None for sid in batch})
            warnings.append(f'Persoonlijke controle onvolledig: {exc}')
        save(state)
    personal = {}
    for row in frame.itertuples():
        sid = int(row.species_id)
        own = None if prior.get(sid) is None else not prior[sid] and firsts.get(sid) in set(row.obs_ids)
        personal[sid] = {'own': own, 'area': None, 'global': None,
                         'star': '?' if own is None else '🟡' if own else ''}
    def circle_stats():
        circles, records = concentration_circles(observations, frame)
        return personal_circles(circles, records, personal, firsts)
    stats = stage('circles', 'Concentraties binnen 25 km berekenen…', circle_stats)
    def total_counts():
        try:
            return personal_species_counts(user, frame['species_id'])
        except Exception as exc:
            warnings.append(f'Totale aantallen konden niet worden geladen: {exc}')
            return None
    counts = stage('totals', 'Je totale aantallen per soort ophalen…', total_counts) if ids else {}
    frame['Mijn waarnemingen wereldwijd'] = (frame['species_id'].map(counts).fillna(0).astype(int)
                                             if counts is not None else pd.NA)
    meta = {'username': account['login'], 'user_id': user, 'start': start.isoformat(), 'end': end.isoformat(),
            'trip_name': trip_name,
            'start_time': start_time.strftime('%H:%M'), 'end_time': end_time.strftime('%H:%M'),
            'places': (), 'geometry': json.dumps(geometry, sort_keys=True) if geometry else '',
            'selected_places': [], 'place_names': (), 'area_name': 'Automatisch reisgebied' if geometry else '',
            'heat_points': points, 'concentrations': stats, 'missing_location_total': len(observations)-len(points),
            'unknown_time_total': unknown, 'observation_total': len(observations),
            'extended_checks': extended,
            'map_extended_checks': map_extended,
            'unidentified_total': len(observations)-int(frame['Waarnemingen in gebied'].sum())}
    identified = {oid for ids in frame['obs_ids'] for oid in ids}
    meta['unidentified_records'] = []
    for observation in observations:
        if observation['id'] in identified:
            continue
        taxon = observation.get('taxon') or {}
        photos = observation.get('photos') or []
        photo = (photos[0].get('medium_url') or photos[0].get('url') or '') if photos else ''
        meta['unidentified_records'].append({'id':observation['id'],
            'name':taxon.get('preferred_common_name') or taxon.get('name') or 'Onbekend',
            'date':observation.get('observed_on') or '', 'photo':photo,
            'url':f"https://www.inaturalist.org/observations/{observation['id']}"})
    novelty = personal.copy()
    if extended:
        checked = state.setdefault('extended_novelty', {})
        rows = [row for _,row in frame.iterrows()]
        for offset in range(0,len(rows),40):
            batch = rows[offset:offset+40]
            if all(int(row['species_id']) in checked and
                   (not map_extended or 'area_first_id' in checked[int(row['species_id'])]) for row in batch):
                continue
            progress(f'Uitgebreide stercontrole: {offset} van {len(rows)} soorten (langzamer)')
            try:
                checked.update(batch_stars(batch, user, meta['start'], meta['end'], (), meta['geometry'], firsts))
            except Exception as exc:
                for row in batch:
                    sid = int(row['species_id'])
                    checked[sid] = personal[sid].copy()
                warnings.append(f'Uitgebreide stercontrole onvolledig: {exc}')
            save(state)
        novelty.update(checked)
    if map_extended:
        def map_stats():
            circles, records = concentration_circles(observations, frame)
            return full_circles(circles, records, novelty, firsts)
        meta['concentrations'] = stage('map_circles_v9', 'Extra kaarttellingen samenstellen…', map_stats)
    if not frame.empty:
        progress('Actuele Research Grade-status van tripwaarnemingen ophalen…')
        try:
            frame = refresh_trip_rg(frame,user,meta['start'],meta['end'])
        except Exception as exc:
            warnings.append(f'RG-status kon niet worden ververst; de eerder opgehaalde status wordt gebruikt: {exc}')
    meta['calculated_at'] = datetime.now(timezone.utc).isoformat()
    return {'frame': frame, 'meta': meta, 'novelty': novelty, 'firsts': firsts, 'warnings': warnings}


def encode_state(value):
    if isinstance(value, pd.DataFrame):
        return {'__frame__': json.loads(value.to_json(orient='split'))}
    if isinstance(value, dict):
        # Preserve integer keys (species IDs) in portable JSON.
        return {'__pairs__': [[encode_state(k),encode_state(v)] for k,v in value.items()]}
    if isinstance(value, (tuple,list,set)):
        return [encode_state(v) for v in value]
    if value is pd.NA:
        return None
    if hasattr(value, 'item'):
        return value.item()
    return value


def decode_state(value):
    if isinstance(value, list):
        return [decode_state(v) for v in value]
    if isinstance(value, dict):
        if set(value) == {'__frame__'}:
            data = value['__frame__']
            return pd.DataFrame(data['data'], columns=data['columns'])
        if set(value) == {'__pairs__'}:
            return {decode_state(k):decode_state(v) for k,v in value['__pairs__']}
        raise ValueError('Ongeldig herstartbestand.')
    return value


class ReportJobs:
    def __init__(self, directory=None, builder=build_report):
        self.directory = Path(directory or Path(tempfile.gettempdir())/'tripreport-jobs-v9')
        self.directory.mkdir(parents=True, exist_ok=True)
        self.builder = builder
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='tripreport')
        self.lock = Lock()
        self.jobs = {}

    @staticmethod
    def key(search):
        normalized = list(search)
        normalized[0] = str(normalized[0]).strip().casefold()
        return hashlib.sha256(json.dumps(normalized).encode()).hexdigest()

    def _write(self, path, value):
        temporary = path.with_name(path.name+'.'+uuid4().hex+'.tmp')
        temporary.write_bytes(pickle.dumps(value))
        temporary.replace(path)

    def _load(self, path):
        if path.exists() and time.time()-path.stat().st_mtime < 7*86400:
            return pickle.loads(path.read_bytes())  # Only server-created files.
        return None

    def _result(self, token):
        path = self.directory/(token+'.pickle')
        result = self._load(path)
        if result and isinstance(result.get('meta'),dict):
            # This completed-result file is written when the calculation finishes.
            result['meta'].setdefault('calculated_at',datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat())
        return result

    def start(self, search):
        search = tuple(search)
        key = self.key(search)
        with self.lock:
            for token,job in self.jobs.items():
                if job['key'] == key and job['state'] == 'running':
                    return token
            saved = self._load(self.directory/(key+'.checkpoint'))
            if saved is None and len(search) >= 6:
                # A changed map checkbox reuses the same trip history and star checks.
                other = (*search[:5], not search[5], *search[6:])
                previous = self._load(self.directory/(self.key(other)+'.checkpoint'))
                if previous:
                    saved = {**previous, 'token':uuid4().hex, 'search':search}
            token = saved['token'] if saved else uuid4().hex
            result = self._result(token)
            if result is not None and self.builder is build_report and 'unidentified_records' not in result.get('meta',{}):
                result = None  # Rebuild metadata from checkpoint; historical checks remain saved.
            if result is not None:
                self.jobs[token] = {'state':'done','message':'Tripreport gereed','key':key,'result':result,
                                    'completed':(self.directory/(token+'.pickle')).stat().st_mtime}
                return token
            saved = saved or {'token':token, 'search':search, 'state':{}, 'message':'Reisgegevens ophalen…'}
            self._write(self.directory/(key+'.checkpoint'), saved)
            self.jobs[token] = {'state':'running', 'message':'Hervatten: '+saved['message'] if saved['state'] else saved['message'],
                                'started':time.time(), 'key':key}
            self.pool.submit(self._run, token, saved)
            return token

    def _run(self, token, saved):
        key = self.key(saved['search'])
        def progress(message):
            with self.lock:
                self.jobs[token]['message'] = message
        def save(state):
            with self.lock:
                saved['message'] = self.jobs[token]['message']
            saved['state'] = state
            self._write(self.directory/(key+'.checkpoint'), saved)
        try:
            if self.builder is build_report:
                result = self.builder(saved['search'], progress, saved['state'], save)
            else:
                result = self.builder(saved['search'], progress)
            self._write(self.directory/(token+'.pickle'), result)
            with self.lock:
                self.jobs[token].update(state='done', message='Tripreport gereed', result=result, completed=time.time())
        except Exception as exc:
            with self.lock:
                self.jobs[token].update(state='error', message=str(exc), completed=time.time())

    def _saved_token(self, token):
        for path in self.directory.glob('*.checkpoint'):
            saved = self._load(path)
            if saved and saved.get('token') == token:
                return saved
        return None

    def snapshot(self, token):
        if not isinstance(token,str) or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):
            return None
        with self.lock:
            if token in self.jobs:
                job = self.jobs[token]
                if job['state'] != 'running' and time.time()-job.get('completed',job.get('started',0)) >= 7*86400:
                    return None
                return job.copy()
        result = self._result(token)
        if result is not None:
            if self.builder is build_report and 'unidentified_records' not in result.get('meta',{}):
                return {'state':'paused','message':'Rapport bijwerken met de extra foto’s vanaf het opgeslagen punt'}
            return {'state':'done','message':'Tripreport gereed','result':result}
        saved = self._saved_token(token)
        if saved:
            return {'state':'paused','message':saved['message']}
        return None

    def resume(self, token):
        saved = self._saved_token(token)
        if not saved:
            raise ValueError('Geen tussentijdse opslag gevonden. Laad een herstartbestand of maak de trip opnieuw.')
        return self.start(saved['search'])

    def settings(self, token):
        """Recover form values independently of Streamlit Session State."""
        if not isinstance(token,str) or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):
            return None
        saved = self._saved_token(token)
        if saved:
            return tuple(saved['search'])
        job = self.snapshot(token)
        if job and job['state'] == 'done':
            meta = job['result'].get('meta', {})
            if meta:
                return (meta['username'],meta['start'],meta['end'],meta['start_time'],meta['end_time'],
                        meta.get('map_extended_checks',False),meta.get('trip_name',''))
        return None

    def export_checkpoint(self, token):
        saved = self._saved_token(token)
        if saved:
            return json.dumps({'format':'tripreport-checkpoint-v9','payload':encode_state(saved)}, ensure_ascii=False).encode()

    def import_checkpoint(self, data):
        if len(data) > 32*1024*1024:
            raise ValueError('Herstartbestand te groot (maximaal 32 MB).')
        document = json.loads(data)
        if document.get('format') not in ('tripreport-checkpoint-v8', 'tripreport-checkpoint-v9'):
            raise ValueError('Dit is geen geldig herstartbestand (versie 8 of 9).')
        saved = decode_state(document['payload'])
        search = saved['search']
        if len(search) not in (6,7) or not isinstance(search[0],str) or not isinstance(search[5],bool):
            raise ValueError('Ongeldige reisinstellingen.')
        if len(search)==7 and (not isinstance(search[6],str) or not search[6].strip() or len(search[6])>120):
            raise ValueError('Vul een geldige tripnaam in.')
        date.fromisoformat(search[1]); date.fromisoformat(search[2])
        clock.fromisoformat(search[3]); clock.fromisoformat(search[4])
        if not isinstance(saved['state'],dict):
            raise ValueError('Ongeldig herstartpunt.')
        saved['token'] = uuid4().hex
        with self.lock:
            if any(job['key'] == self.key(search) and job['state'] == 'running' for job in self.jobs.values()):
                raise ValueError('Deze berekening loopt al. Keer terug naar het actieve rapport.')
            self._write(self.directory/(self.key(search)+'.checkpoint'), saved)
        return self.start(search)
