"""Overview map and compact tables for saved trip versions."""
from zoneinfo import ZoneInfo
from datetime import date
import html

import folium

from trip_store import normalize_record, version_key
from trip_locations import stored_trip_location


def calculation_label(stamp):
    if not stamp:
        return "Onbekend (oudere trip)"
    parsed = version_key({"calculated_at": stamp})
    return parsed.astimezone(ZoneInfo("Europe/Amsterdam")).strftime("%d-%m-%Y %H:%M:%S")


def trip_table(rows):
    result = []
    for raw in rows:
        row = normalize_record(raw)
        latest = max(row["versions"], key=version_key)
        result.append({"Trip": row["name"], "Van": date.fromisoformat(row["start_date"]), "Tot": date.fromisoformat(row["end_date"]),
                       **summary_columns(latest["summary"]),
                       "Berekend op": (version_key(latest).astimezone(ZoneInfo("Europe/Amsterdam"))
                                       if latest.get("calculated_at") else None),
                       "Versies": len(row["versions"])})
    return result


def summary_columns(summary):
    return {"Waarnemingen": summary["observations"], "Soorten": summary["species"],
            "Niet op soort": summary["unidentified"], "Nieuw voor mij": summary["own"],
            "Nieuw in gebied": summary["area"], "Nieuw op iNat": summary["global"]}


def version_table(row):
    return [{"Berekend op": calculation_label(v.get("calculated_at")), **summary_columns(v["summary"])}
            for v in sorted(normalize_record(row)["versions"], key=version_key, reverse=True)]


def overview_map(rows, ebird_summaries=None):
    """One marker per trip, at a point inside its latest public observation area."""
    world = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap",
                       zoom_control=True, prefer_canvas=True, zoom_animation=False,
                       fade_animation=False, marker_zoom_animation=False)
    bounds = []
    missing = 0
    ebird_summaries = ebird_summaries or {}
    for raw in rows:
        row = normalize_record(raw)
        location = stored_trip_location(row)
        if location is None:
            missing += 1
            continue
        lat, lon = location
        latest = max(row["versions"], key=version_key)
        summary = latest["summary"]
        bird = ebird_summaries.get(row['id'])
        def fmt(value):
            return str(value) if value is not None else '—'
        popup = (f"<div style='font:13px/1.5 Arial,sans-serif;min-width:260px'>"
                 f"<b>{html.escape(row['name'])}</b><br>"
                 f"{html.escape(row['start_date'])} t/m {html.escape(row['end_date'])}"
                 f"<table style='width:100%;margin:9px 0;border-collapse:collapse;text-align:right'>"
                 f"<tr><th style='text-align:left'></th><th>iNaturalist</th><th>eBird</th></tr>"
                 f"<tr><td style='text-align:left'>Waarnemingen</td><td>{fmt(summary.get('observations'))}</td><td>{fmt(bird.get('Waarnemingen')) if bird else '—'}</td></tr>"
                 f"<tr><td style='text-align:left'>Soorten</td><td>{fmt(summary.get('species'))}</td><td>{fmt(bird.get('Soorten')) if bird else '—'}</td></tr>"
                 f"<tr><td style='text-align:left'>Nieuwe soorten</td><td>{fmt(summary.get('own'))}</td><td>{fmt(bird.get('Nieuw voor mij')) if bird else '—'}</td></tr>"
                 f"</table>Berekend: {html.escape(calculation_label(latest.get('calculated_at')))}</div>")
        folium.CircleMarker([lat, lon], radius=8, color="#205e3b", weight=2,
                            fill=True, fill_color="#3c995c", fill_opacity=0.9,
                            tooltip=html.escape(row["name"]),
                      popup=folium.Popup(popup, max_width=320)).add_to(world)
        bounds.append([lat, lon])
    if bounds:
        world.fit_bounds(bounds, padding=(35, 35), max_zoom=9)
    return world, missing


def sorted_trips(rows, column="Van", descending=True):
    """Sort typed values, keeping unknown dates/counts last in either direction."""
    pairs = [(row, trip_table([row])[0][column]) for row in rows]
    known = [(row, value) for row, value in pairs if value is not None]
    unknown = [row for row, value in pairs if value is None]
    if column == "Trip":
        known.sort(key=lambda pair: pair[1].casefold(), reverse=descending)
    else:
        known.sort(key=lambda pair: pair[1], reverse=descending)
    return [row for row, _ in known] + unknown
