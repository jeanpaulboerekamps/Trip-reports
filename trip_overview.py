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


def overview_map(rows):
    """One marker per trip, at a point inside its latest public observation area."""
    world = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap")
    bounds = []
    missing = 0
    for raw in rows:
        row = normalize_record(raw)
        location = stored_trip_location(row)
        if location is None:
            missing += 1
            continue
        lat, lon = location
        latest = max(row["versions"], key=version_key)
        summary = latest["summary"]
        popup = (f"<b>{html.escape(row['name'])}</b><br>"
                 f"{html.escape(row['start_date'])} t/m {html.escape(row['end_date'])}<br>"
                 f"{summary['observations']} waarnemingen · {summary['species']} soorten<br>"
                 f"Berekend: {html.escape(calculation_label(latest.get('calculated_at')))}")
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
