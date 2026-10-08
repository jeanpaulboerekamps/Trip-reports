"""Personal eBird exports, indexed by calendar day (no area or time filter)."""
import csv
import io
import json
import re
import zipfile
from collections import defaultdict
from datetime import date

REQUIRED = {'Submission ID', 'Common Name', 'Scientific Name', 'Date', 'Count'}


def species_key(scientific, common):
    """Collapse subspecies to binomials; keep unidentified taxa separately."""
    words = scientific.strip().split()
    key = ' '.join(words[:2])
    if (len(words) < 2 or not re.fullmatch(r'[A-Z][a-z]+ [a-z]+', key)
            or words[1] in ('sp', 'spp') or ' x ' in scientific
            or 'Domestic' in common):
        return None
    return key


def read_export(content):
    if len(content) > 100 * 1024 * 1024:
        raise ValueError('De export is groter dan 100 MB.')
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            files = [f for f in archive.infolist() if f.filename.lower().endswith('.csv') and not f.filename.startswith('__MACOSX/')]
            if len(files) != 1:
                raise ValueError('De zip moet één eBird CSV-bestand bevatten.')
            if files[0].file_size > 100 * 1024 * 1024:
                raise ValueError('Het uitgepakte CSV-bestand is groter dan 100 MB.')
            with archive.open(files[0]) as stream:
                return parse_csv(io.TextIOWrapper(stream, encoding='utf-8-sig', newline=''))
    try:
        return parse_csv(io.StringIO(content.decode('utf-8-sig'), newline=''))
    except UnicodeError as exc:
        raise ValueError('Gebruik de originele UTF-8-export van eBird.') from exc


def parse_csv(stream):
    reader = csv.DictReader(stream)
    if not REQUIRED.issubset(reader.fieldnames or []):
        raise ValueError('Dit is geen persoonlijke eBird-export: vereiste kolommen ontbreken.')
    taxa = []
    taxon_ids = {}
    checklists = []
    checklist_ids = {}
    observations = []
    seen = set()
    for line, row in enumerate(reader, 2):
        stamp = (row.get('Date') or '').strip()
        try:
            stamp = date.fromisoformat(stamp).isoformat()
        except ValueError as exc:
            raise ValueError(f'Ongeldige datum op CSV-regel {line}.') from exc
        submission = (row.get('Submission ID') or '').strip()
        scientific = (row.get('Scientific Name') or '').strip()
        common = (row.get('Common Name') or '').strip()
        if not submission or not scientific or not common:
            raise ValueError(f'Ontbrekende checklist of vogelnaam op CSV-regel {line}.')
        # The original export can contain repeated rows: do not count them twice.
        identity = (submission, scientific, stamp)
        if identity in seen:
            continue
        seen.add(identity)
        key = species_key(scientific, common)
        taxon_key = key or scientific
        if taxon_key not in taxon_ids:
            taxon_ids[taxon_key] = len(taxa)
            try:
                order = float(row.get('Taxonomic Order') or 1e9)
            except ValueError:
                order = 1e9
            taxa.append([taxon_key, common.split(' (')[0] if key else common, order, bool(key)])
        if submission not in checklist_ids:
            checklist_ids[submission] = len(checklists)
            checklists.append(submission)
        count = (row.get('Count') or '').strip()
        if count.upper() in ('X', ''):
            number = None
        elif count.isdecimal():
            number = int(count)
        else:
            raise ValueError(f'Ongeldig aantal op CSV-regel {line}: {count}.')
        observations.append([stamp, checklist_ids[submission], taxon_ids[taxon_key], number])
    if not observations:
        raise ValueError('De export bevat geen waarnemingen.')
    observations.sort(key=lambda row: row[0])
    return {'format': 1, 'taxa': taxa, 'checklists': checklists, 'observations': observations,
            'first_date': observations[0][0], 'last_date': observations[-1][0]}


class EbirdIndex:
    def __init__(self, data):
        if not isinstance(data, dict) or data.get('format') != 1:
            raise ValueError('Ongeldige bewaarde eBird-export. Importeer de export opnieuw.')
        self.data = data
        self.days = defaultdict(list)
        self.first_seen = {}
        for observation in data['observations']:
            stamp, checklist, taxon, count = observation
            self.days[stamp].append(observation)
            if data['taxa'][taxon][3]:
                self.first_seen[taxon] = min(stamp, self.first_seen.get(taxon, stamp))

    def trip(self, trip):
        start, end = trip['start_date'], trip['end_date']
        observations = [row for stamp, rows in self.days.items() if start <= stamp <= end for row in rows]
        species = {row[2] for row in observations if self.data['taxa'][row[2]][3]}
        new = {taxon for taxon in species if start <= self.first_seen[taxon] <= end}
        summary = {'Trip': trip['name'], 'Van': start, 'Tot': end,
                   'Checklists': len({row[1] for row in observations}),
                   'Waarnemingen': len(observations), 'Soorten': len(species),
                   'Niet op soort': sum(not self.data['taxa'][row[2]][3] for row in observations),
                   'Nieuw voor mij': len(new)}
        grouped = defaultdict(list)
        for row in observations:
            grouped[row[2]].append(row)
        birds = []
        for taxon in sorted(grouped, key=lambda t: (self.data['taxa'][t][2], self.data['taxa'][t][0])):
            rows = grouped[taxon]
            scientific, common, _, is_species = self.data['taxa'][taxon]
            birds.append({'Vogel': common, 'Wetenschappelijke naam': scientific,
                          'Op soort': is_species, 'Nieuw voor mij': taxon in new,
                          'Checklists': len({row[1] for row in rows}),
                          'Bekend aantal': sum(row[3] or 0 for row in rows),
                          'Aantal onbekend (X)': sum(row[3] is None for row in rows),
                          'Eerste dag': min(row[0] for row in rows), 'Laatste dag': max(row[0] for row in rows),
                          'Eerste in export': self.first_seen.get(taxon, '')})
        return summary, birds


def bird_csv(birds):
    if not birds:
        return b''
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(birds[0]))
    writer.writeheader()
    writer.writerows(birds)
    return ('\ufeff' + stream.getvalue()).encode('utf-8')
