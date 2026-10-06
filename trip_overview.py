"""Overview map and compact tables for saved trip versions."""
from zoneinfo import ZoneInfo
import html
import json

import folium
from shapely.geometry import shape
from folium.plugins import MarkerCluster

from trip_store import normalize_record, version_key


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
        result.append({"Trip": row["name"], "Van": row["start_date"], "Tot": row["end_date"],
                       "Berekend op": calculation_label(latest.get("calculated_at")),
                       "Versies": len(row["versions"]), **summary_columns(latest["summary"])})
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
    cluster = MarkerCluster(name="Trips").add_to(world)
    bounds = []
    missing = 0
    for raw in rows:
        row = normalize_record(raw)
        geometry = row["search"].get("geometry")
        try:
            geometry = json.loads(geometry) if isinstance(geometry, str) and geometry else geometry
            region = shape(geometry) if geometry else None
            if region is None or region.is_empty or not region.is_valid:
                missing += 1
                continue
            point = region.representative_point()
            # A multipolygon may cross the date line: use one real point, not the centroid in the ocean.
            lat, lon = point.y, point.x
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                missing += 1
                continue
        except (ValueError, TypeError, KeyError, AttributeError):
            missing += 1
            continue
        latest = max(row["versions"], key=version_key)
        summary = latest["summary"]
        popup = (f"<b>{html.escape(row['name'])}</b><br>"
                 f"{html.escape(row['start_date'])} t/m {html.escape(row['end_date'])}<br>"
                 f"{summary['observations']} waarnemingen · {summary['species']} soorten<br>"
                 f"Berekend: {html.escape(calculation_label(latest.get('calculated_at')))}")
        folium.Marker([lat, lon], tooltip=html.escape(row["name"]),
                      popup=folium.Popup(popup, max_width=320)).add_to(cluster)
        bounds.append([lat, lon])
    if bounds:
        world.fit_bounds(bounds, padding=(35, 35), max_zoom=9)
    return world, missing
