"""Overview map and compact tables for saved trip versions."""
from zoneinfo import ZoneInfo
from datetime import date
import html

import folium
from branca.element import MacroElement
from jinja2 import Template

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


def overview_map(rows, view="Alle trips"):
    """One marker per trip, at a point inside its latest public observation area."""
    world = folium.Map(location=[20, 0], zoom_start=2, tiles="OpenStreetMap", control_scale=True, max_zoom=18)
    markers = []
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
        marker = folium.CircleMarker([lat, lon], radius=7, color="#205e3b", weight=2,
                            fill=True, fill_color="#3c995c", fill_opacity=0.9,
                            tooltip=html.escape(row["name"]),
                      popup=folium.Popup(popup, max_width=320)).add_to(world)
        markers.append(marker)
        bounds.append([lat, lon])
    if view == "Europa":
        world.fit_bounds([[28, -25], [72, 45]], padding=(20, 20))
    elif view == "Midden-Oosten en Indische Oceaan":
        world.fit_bounds([[-10, 35], [35, 90]], padding=(20, 20))
    elif bounds:
        world.fit_bounds(bounds, padding=(25, 25), max_zoom=11)
    if markers:
        world.add_child(ExpandOverlappingTrips(markers))
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


class ExpandOverlappingTrips(MacroElement):
    """Keep each trip visible; let overlapping circles spread on tap without clustering."""
    _template = Template(r"""
    {% macro script(this, kwargs) %}
    (function() {
        const map = {{this._parent.get_name()}};
        const markers = [{{this.marker_names | join(',')}}];
        const original = markers.map(marker => marker.getLatLng());
        let lines = [];
        let expanded = false;
        function reset() {
            markers.forEach((marker, i) => marker.setLatLng(original[i]));
            lines.forEach(line => map.removeLayer(line));
            lines = [];
            expanded = false;
        }
        markers.forEach((marker, clicked) => {
            marker.on('click', function(event) {
                if (expanded) return;
                const centre = map.latLngToLayerPoint(original[clicked]);
                const nearby = markers.map((other, i) => i).filter(i =>
                    map.latLngToLayerPoint(original[i]).distanceTo(centre) < 16);
                if (nearby.length < 2) return;
                marker.closePopup();
                expanded = true;
                const radius = Math.max(28, nearby.length * 7);
                nearby.forEach((i, offset) => {
                    const angle = 2 * Math.PI * offset / nearby.length;
                    const point = L.point(centre.x + radius * Math.cos(angle), centre.y + radius * Math.sin(angle));
                    const target = map.layerPointToLatLng(point);
                    lines.push(L.polyline([original[i], target], {color:'#48725c', weight:1.2, opacity:0.7, interactive:false}).addTo(map));
                    markers[i].setLatLng(target);
                    markers[i].bringToFront();
                });
                if (event.originalEvent) L.DomEvent.stopPropagation(event.originalEvent);
            });
        });
        map.on('zoomstart', reset);
        map.on('dragstart', reset);
        map.on('click', reset);
    })();
    {% endmacro %}
    """)

    def __init__(self, markers):
        super().__init__()
        self._name = 'ExpandOverlappingTrips'
        self.marker_names = [marker.get_name() for marker in markers]
