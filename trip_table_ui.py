"""Selectable table with genuinely wrapped headers and typed column sorting."""
from datetime import datetime, date
import hashlib
import json
from pathlib import Path

from streamlit.components.v1 import declare_component
from trip_overview import trip_table

COLUMNS = [
    {"key": "Trip", "lines": ["Trip"], "width": 220},
    {"key": "Van", "lines": ["Van"], "width": 82},
    {"key": "Tot", "lines": ["Tot"], "width": 82},
    {"key": "Waarnemingen", "lines": ["Waarne-", "mingen"], "width": 76},
    {"key": "Soorten", "lines": ["Soorten"], "width": 64},
    {"key": "Niet op soort", "lines": ["Niet op", "soort"], "width": 72},
    {"key": "Nieuw voor mij", "lines": ["Nieuw", "voor mij"], "width": 72},
    {"key": "Nieuw in gebied", "lines": ["Nieuw in", "gebied"], "width": 72},
    {"key": "Nieuw op iNat", "lines": ["Nieuw op", "iNat"], "width": 72},
    {"key": "Berekend op", "lines": ["Berekend", "op"], "width": 110},
    {"key": "Versies", "lines": ["Versies"], "width": 58},
]
_table = declare_component("trip_compact_table", path=str(Path(__file__).parent / "trip_table_component"))


def table_payload(rows):
    output = []
    for row, values in zip(rows, trip_table(rows)):
        cells, sort_values = {}, {}
        for key, value in values.items():
            if isinstance(value, datetime):
                cells[key] = [value.strftime('%d-%m-%Y'), value.strftime('%H:%M:%S')]
                sort_values[key] = value.timestamp()
            elif isinstance(value, date):
                cells[key] = [value.strftime('%d-%m-%Y')]
                sort_values[key] = value.isoformat()
            else:
                cells[key] = ['—' if value is None else str(value)]
                sort_values[key] = value
        output.append({'id': row['id'], 'cells': cells, 'sort_values': sort_values})
    return output


def render_trip_table(rows, selected_id, context, sort_by, descending):
    payload = table_payload(rows)
    signature = hashlib.sha256(json.dumps([row["id"] for row in payload], ensure_ascii=False).encode()).hexdigest()[:20]
    return _table(rows=payload, columns=COLUMNS, selected_id=selected_id, context=context,
                  sort_by=sort_by, descending=descending, order_signature=signature,
                  key="overview_compact_table_v20", default=None)
