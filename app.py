"""Tripreport Verkenner — afgeronde reizen met openbare iNaturalist-gegevens."""
from datetime import date, timedelta, datetime, time
import html
import hashlib
import json
import re
import tempfile
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
from streamlit.components.v1 import declare_component

from report_pdf import make_trip_pdf, pdf_trip_name, pdf_filename
import report_pdf
from trip_map import select_time_window, observation_points, infer_trip_area, leaflet_heatmap
from report_jobs import ReportJobs
from taxonomy import sort_species_overview
from trip_data import batch_stars, first_record, own_firsts_in_window, personal_species_counts, resolve_username, species_frame, star_for, summary_counts, trip_observations, refresh_trip_rg

EARLIEST_TRIP_DATE = date(1965, 1, 1)


# Embedded so a single app.py update can start even if the component directory
# was not uploaded by the hosting interface.
_BROWSER_COMPONENT_HTML = '<!doctype html>\n<html lang="nl"><head><meta charset="utf-8"></head><body style="margin:0">\n<script>\nconst STORAGE_KEY = "tripreport_verkenner_saved_trips_v1";\nconst REPORT_KEY = "tripreport_last_report_v1";\nlet lastNonce = null;\nlet lastActive = null;\nfunction send(type, extra = {}) {\n  window.parent.postMessage({isStreamlitMessage:true, type, ...extra}, "*");\n}\nfunction read() {\n  const value = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");\n  if (!Array.isArray(value)) throw new Error("De bewaarde trips zijn beschadigd.");\n  return value;\n}\nfunction mergeRecord(old, incoming) {\n  if (!old) return incoming;\n  const snapshots = row => row.versions && row.versions.length ? row.versions : [{\n    id: "legacy-" + row.id, calculated_at: row.search.calculated_at || null,\n    search: row.search, summary: row.summary\n  }];\n  const versions = new Map(snapshots(old).map(v => [v.id, v]));\n  snapshots(incoming).forEach(v => { if (!versions.has(v.id)) versions.set(v.id, v); });\n  const ordered = [...versions.values()].sort((a, b) =>\n    (a.calculated_at ? Date.parse(a.calculated_at) : -Infinity) -\n    (b.calculated_at ? Date.parse(b.calculated_at) : -Infinity));\n  const latest = ordered[ordered.length - 1];\n  return {...old, ...incoming, versions: ordered, search: latest.search, summary: latest.summary};\n}\nfunction publish(nonce, records, error = "") {\n  let last_report = localStorage.getItem(REPORT_KEY) || "";\n  if (!/^[a-f0-9]{32}$/.test(last_report)) last_report = "";\n  send("streamlit:setComponentValue", {dataType:"json", value:{nonce, records, error, last_report}});\n}\nwindow.addEventListener("message", event => {\n  if (event.data.type !== "streamlit:render") return;\n  const {op = "list", nonce = "initial", record, imported, active_report, trip_id, locations, name} = event.data.args || {};\n  const changed = active_report && active_report !== lastActive;\n  if (nonce === lastNonce && !changed) return;\n  lastNonce = nonce;\n  try {\n    if (active_report && /^[a-f0-9]{32}$/.test(active_report)) {\n      localStorage.setItem(REPORT_KEY, active_report);\n      lastActive = active_report;\n    }\n    let records = read();\n    if (op === "save") {\n      const pos = records.findIndex(x => x.id === record.id);\n      if (pos < 0) records.push(record); else records[pos] = mergeRecord(records[pos], record);\n      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));\n    } else if (op === "rename") {\n      if (typeof name !== "string" || !name.trim() || name.trim().length > 120) {\n        throw new Error("Geef de trip een naam van maximaal 120 tekens.");\n      }\n      const row = records.find(x => x.id === trip_id);\n      if (!row) throw new Error("Deze trip bestaat niet meer.");\n      row.name = name.trim();\n      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));\n    } else if (op === "delete") {\n      records = records.filter(x => x.id !== trip_id);\n      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));\n    } else if (op === "locations") {\n      (locations || []).forEach(item => {\n        const row = records.find(x => x.id === item.id);\n        if (row && Array.isArray(item.map_location) && item.map_location.length === 2 &&\n            item.map_location.every(Number.isFinite) && Math.abs(item.map_location[0]) <= 90 && Math.abs(item.map_location[1]) <= 180) {\n          row.map_location = item.map_location;\n          if (item.map_location_method === "density-25km-v1") row.map_location_method = item.map_location_method;\n        }\n      });\n      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));\n    } else if (op === "import") {\n      if (!Array.isArray(imported) || imported.length > 1000 ||\n          !imported.every(x => x && typeof x.id === "string" && x.search && x.summary)) {\n        throw new Error("Dit bestand bevat geen geldige trips.");\n      }\n      const byId = new Map(records.map(x => [x.id, x]));\n      imported.forEach(x => byId.set(x.id, mergeRecord(byId.get(x.id), x)));\n      records = [...byId.values()];\n      localStorage.setItem(STORAGE_KEY, JSON.stringify(records));\n    }\n    publish(nonce, records);\n  } catch (error) {\n    publish(nonce, [], String(error.message || error));\n  }\n});\nsend("streamlit:componentReady", {apiVersion:1});\nsend("streamlit:setFrameHeight", {height:0});\n</script>\n</body></html>\n'

from trip_store import make_record, summary_snapshot, matches_search, validate_import, normalize_record, merge_records, same_trip, rename_record
from trip_overview import overview_map, trip_table, version_table, calculation_label, sorted_trips
from trip_locations import stored_trip_location, recover_trip_location, has_density_location, DENSITY_METHOD

st.set_page_config(page_title="Tripreport Verkenner", page_icon="🧭", layout="wide")
st.markdown("""<style>
.block-container{max-width:1250px;padding-top:1.4rem;padding-bottom:3rem}
.intro{padding:1rem 1.2rem;border-radius:16px;background:#eaf4ed;border:1px solid #c6ddcc;margin:.5rem 0 1.2rem}
.species-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:1rem;margin:.8rem 0 1rem}
.species-card{border:1px solid #cad6cd;border-radius:13px;overflow:hidden;background:var(--secondary-background-color)}
.species-card a{color:inherit;text-decoration:none}.photo-wrap{position:relative}
.species-photo,.photo-empty{height:170px;width:100%;object-fit:contain;display:block;background:#e4ede7}
.photo-empty{display:flex;align-items:center;justify-content:center;font-size:2rem}
.stars{position:absolute;right:10px;top:8px;display:flex;gap:3px;align-items:center}.star{font-size:2rem;line-height:1;text-shadow:0 1px 5px #343a32,0 0 2px #fff}
.star.red{color:#e3342f}.star.orange{color:#f28b24}.star.yellow{color:#f0cc24}
.species-card.rg{border:3px solid #268348}
.species-body{padding:.8rem}.species-name{font-weight:750;line-height:1.2}.scientific{font-style:italic;opacity:.72;font-size:.9rem;margin:.18rem 0 .65rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pill{font-size:.8rem;background:rgba(58,130,79,.13);border-radius:30px;padding:.25rem .5rem}
.legend{display:flex;gap:1rem;flex-wrap:wrap;margin:.7rem 0 1.1rem}.legend span{font-size:.92rem}
.legend b{font-size:1.35rem;vertical-align:middle}.legend .red{color:#e3342f}.legend .orange{color:#f28b24}.legend .yellow{color:#e3b51e}
.trip-summary{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:.65rem;margin:.85rem 0 1.4rem}
.trip-stat{border:1px solid #cfddd3;background:#edf5ef;border-radius:12px;padding:.8rem;min-width:0}
.trip-stat strong{display:block;font-size:1.55rem;line-height:1.15;color:#1b5035}
.trip-stat span{display:block;font-size:.85rem;line-height:1.25;margin-top:.25rem}
@media(max-width:700px){.trip-summary{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:540px){.species-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}.species-photo,.photo-empty{height:130px}.species-body{padding:.58rem}.species-name{font-size:.95rem}}
</style>""", unsafe_allow_html=True)

for key, value in {"places": [], "geometry": None, "area_name": "", "trip": None, "query": None, "novelty": {}, "place_results": [], "show_map": False}.items():
    if key not in st.session_state:
        st.session_state[key] = value
for key, value in {"trip_username": "jeanpaulboerekamps", "trip_start": date.today() - timedelta(days=7),
                   "trip_end": date.today() - timedelta(days=1), "trip_start_time": time(0, 0),
                   "trip_end_time": time(23, 59), "trip_name": "",
                   "saved_trip_id": None, "saved_search": None, "page": "report" if st.query_params.get("report") else "home",
                   "previous_report_token": None,
                   "saved_rows": [], "storage_action": {"op": "list", "nonce": "initial"},
                   "last_storage_nonce": None, "storage_notice": ""}.items():
    if key not in st.session_state:
        st.session_state[key] = value


DEFAULT_USERNAME = "jeanpaulboerekamps"
if not str(st.session_state.get("overview_user_filter") or "").strip():
    st.session_state.overview_user_filter = DEFAULT_USERNAME


def remember_overview_username():
    value = st.session_state.overview_username_v18.strip() or DEFAULT_USERNAME
    st.session_state.overview_user_filter = value
    st.session_state.overview_username_v18 = value


@st.cache_data(ttl=900, show_spinner=False)
def cached_trip_location(search_json):
    return recover_trip_location(json.loads(search_json))


@st.cache_resource
def report_jobs():
    return ReportJobs()


component_dir = Path(__file__).parent / "local_store_component"
if not (component_dir / "index.html").is_file():
    component_dir = Path(tempfile.gettempdir()) / "tripreport-browser-store-v1"
    component_dir.mkdir(parents=True, exist_ok=True)
    (component_dir / "index.html").write_text(_BROWSER_COMPONENT_HTML, encoding="utf-8")
browser_store = declare_component("trip_browser_store", path=str(component_dir))
action = st.session_state.storage_action
storage_event = browser_store(**action, active_report=st.session_state.get('report_job') or st.query_params.get('report'), key="trip_browser_store")
if isinstance(storage_event, dict):
    previous_report = storage_event.get('last_report')
    if isinstance(previous_report, str) and re.fullmatch(r'[a-f0-9]{32}', previous_report):
        st.session_state.previous_report_token = previous_report

restore_token = st.session_state.get('report_job') or st.query_params.get('report')
if st.session_state.page == 'report' and restore_token and st.session_state.get('restored_form_token') != restore_token:
    settings = report_jobs().settings(restore_token)
    if settings:
        st.session_state.trip_username = settings[0]
        st.session_state.trip_start = date.fromisoformat(settings[1])
        st.session_state.trip_end = date.fromisoformat(settings[2])
        st.session_state.trip_start_time = time.fromisoformat(settings[3])
        st.session_state.trip_end_time = time.fromisoformat(settings[4])
        st.session_state.map_extra_choice = settings[5]
        if len(settings)>6:
            linked = next((row for row in st.session_state.saved_rows
                           if row["id"] == st.session_state.saved_trip_id), None)
            settings_search = {"username": settings[0], "start": settings[1], "end": settings[2],
                               "start_time": settings[3], "end_time": settings[4]}
            st.session_state.trip_name = (linked["name"] if linked and same_trip(settings_search, linked["search"])
                                          else settings[6])
        st.session_state.restored_form_token = restore_token
if isinstance(storage_event, dict) and storage_event.get("nonce") != st.session_state.last_storage_nonce:
    st.session_state.last_storage_nonce = storage_event.get("nonce")
    if storage_event.get("error"):
        st.session_state.storage_notice = "Opslag in deze browser is mislukt: " + storage_event["error"]
    else:
        try:
            st.session_state.saved_rows = validate_import(json.dumps(storage_event.get("records", [])))
        except (ValueError, TypeError, KeyError) as exc:
            st.session_state.storage_notice = "Bewaarde trips konden niet worden gelezen: " + str(exc)
        if action.get("op") == "save":
            st.session_state.storage_notice = "Tripversie is in deze browser bewaard."
        elif action.get("op") == "import":
            st.session_state.storage_notice = "Trips zijn geïmporteerd."
        elif action.get("op") == "rename":
            st.session_state.storage_notice = "Tripnaam is gewijzigd."
            if st.session_state.saved_trip_id == action.get("trip_id"):
                st.session_state.trip_name = action["name"]
        elif action.get("op") == "delete":
            st.session_state.storage_notice = "Trip en alle bewaarde versies zijn verwijderd."
            if st.session_state.saved_trip_id == action.get("trip_id"):
                st.session_state.saved_trip_id = None
                st.session_state.saved_search = None
    st.session_state.storage_action = {"op": "list", "nonce": "initial"}

def clear_report():
    for key in ("report_job", "loaded_report_job", "restored_form_token", "pdf_bytes", "pdf_key"):
        st.session_state.pop(key, None)
    st.query_params.pop("report", None)
    st.session_state.trip = None
    st.session_state.query = None
    st.session_state.novelty = {}


def open_trip(row):
    clear_report()
    saved = row["search"]
    st.session_state.trip_username = saved["username"]
    st.session_state.trip_start = date.fromisoformat(saved["start"])
    st.session_state.trip_end = date.fromisoformat(saved["end"])
    st.session_state.trip_start_time = time.fromisoformat(saved.get("start_time", "00:00"))
    st.session_state.trip_end_time = time.fromisoformat(saved.get("end_time", "23:59"))
    st.session_state.places = [dict(place) for place in saved.get("selected_places", [])]
    st.session_state.geometry = json.loads(saved["geometry"]) if isinstance(saved.get("geometry"), str) and saved["geometry"] else saved.get("geometry")
    st.session_state.area_name = saved.get("area_name", "")
    st.session_state.trip_name = row["name"]
    st.session_state.map_extra_choice = saved.get("map_extended_checks", False)
    st.session_state.saved_trip_id = row["id"]
    st.session_state.saved_search = saved
    st.session_state.page = "report"
    st.rerun()


st.title("🧭 Tripreport Verkenner")
st.caption("Versie 19 · Zwaartepunt op de kaart, tripnaam wijzigen en sorteren")
if st.session_state.storage_notice:
    st.info(st.session_state.storage_notice)
    st.session_state.storage_notice = ""

if st.session_state.page == "home":
    title_col, new_col = st.columns([4, 1])
    title_col.subheader("Mijn trips")
    if new_col.button("Nieuwe trip", type="primary", use_container_width=True):
        clear_report()
        st.session_state.trip_username = st.session_state.overview_user_filter.strip() or DEFAULT_USERNAME
        st.session_state.trip_name = ""
        st.session_state.trip_start = date.today() - timedelta(days=7)
        st.session_state.trip_end = date.today() - timedelta(days=1)
        st.session_state.trip_start_time = time(0, 0)
        st.session_state.trip_end_time = time(23, 59)
        st.session_state.saved_trip_id = None
        st.session_state.saved_search = None
        st.session_state.places = []
        st.session_state.geometry = None
        st.session_state.area_name = ""
        st.session_state.map_extra_choice = False
        st.session_state.page = "report"
        st.rerun()
    selected_user = st.text_input("iNaturalist-gebruikersnaam", value=st.session_state.overview_user_filter,
                                  key="overview_username_v18", on_change=remember_overview_username).strip().casefold()
    user_rows = sorted([row for row in st.session_state.saved_rows
                        if row["username"].strip().casefold() == selected_user],
                       key=lambda row: row["start_date"], reverse=True)
    st.caption("Je bewaarde trips in deze browser. Totalen zijn van de meest recente berekening. Berekentijden: Europe/Amsterdam.")
    st.subheader("Trips op de kaart")
    st.caption("De marker staat bij de waarnemingslocatie met de meeste waarnemingen binnen 25 km. Alleen openbare locaties tellen mee.")
    recovered = []
    location_errors = []
    missing_rows = [row for row in user_rows if not has_density_location(row)]
    if missing_rows:
        with st.spinner("Plaatsen met de meeste waarnemingen bepalen…"):
            for row in missing_rows:
                try:
                    location = cached_trip_location(json.dumps(row["search"], sort_keys=True))
                    if location:
                        row["map_location"] = location
                        row["map_location_method"] = DENSITY_METHOD
                        recovered.append({"id": row["id"], "map_location": location, "map_location_method": DENSITY_METHOD})
                except Exception:
                    location_errors.append(row["name"])
    if recovered and action.get("op") == "list":
        st.session_state.storage_action = {"op": "locations", "nonce": str(uuid4()), "locations": recovered}
        st.rerun()
    world, missing = overview_map(user_rows)
    map_signature = hashlib.sha256(json.dumps([(row["id"], row["name"], stored_trip_location(row)) for row in user_rows]).encode()).hexdigest()[:16]
    st_folium(world, height=430, use_container_width=True, returned_objects=[], key="trips_overview_map_" + map_signature)
    if location_errors and not missing:
        st.warning("De drukste locatie kon nog niet worden bepaald voor: " + ", ".join(location_errors) + ". De eerdere kaartlocatie blijft zichtbaar.")
        if st.button("Kaartlocaties opnieuw ophalen"):
            cached_trip_location.clear()
            st.rerun()
    if missing:
        names = ", ".join(row["name"] for row in user_rows if stored_trip_location(row) is None)
        st.caption("Nog niet op de kaart: " + names + ". Geen openbare locatie gevonden of ophalen is niet gelukt.")
        if location_errors:
            st.warning("Kaartlocaties konden niet worden opgehaald voor: " + ", ".join(location_errors))
        if st.button("Kaartlocaties opnieuw ophalen"):
            cached_trip_location.clear()
            st.rerun()
    needle = st.text_input("Zoek op tripnaam, gebied of datum", key="trip_overview_search")
    rows = [row for row in user_rows if matches_search(row, needle)]
    st.subheader(f"Tripoverzicht ({len(rows)})")
    if rows:
        sort_col, direction_col = st.columns([3, 2])
        columns = list(trip_table(rows[:1])[0])
        sort_by = sort_col.selectbox("Sorteren op", columns, index=columns.index("Van"), key="trip_sort_column")
        direction = direction_col.radio("Volgorde", ["Aflopend", "Oplopend"], horizontal=True, key="trip_sort_direction")
        rows = sorted_trips(rows, sort_by, descending=direction == "Aflopend")
        table_key = "trip_selection_" + hashlib.sha256(json.dumps([row["id"] for row in rows]).encode()).hexdigest()[:16]
        selection = st.dataframe(pd.DataFrame(trip_table(rows)), hide_index=True, use_container_width=True,
                                 key=table_key, on_select="rerun", selection_mode="single-row",
                                 column_config={"Trip": st.column_config.TextColumn("Trip", width="large", pinned=True),
                                                "Van": st.column_config.DateColumn(format="DD-MM-YYYY"),
                                                "Tot": st.column_config.DateColumn(format="DD-MM-YYYY"),
                                                "Berekend op": st.column_config.DatetimeColumn(format="DD-MM-YYYY HH:mm:ss")})
        chosen = selection.selection.rows
        if chosen and 0 <= chosen[0] < len(rows):
            row = rows[chosen[0]]
            st.subheader(row["name"])
            with st.form("rename_trip_" + row["id"]):
                new_name = st.text_input("Tripnaam wijzigen", value=row["name"], max_chars=120)
                rename_now = st.form_submit_button("Naam opslaan")
            if rename_now:
                try:
                    renamed = rename_record(row, new_name)
                    st.session_state.storage_action = {"op": "rename", "nonce": str(uuid4()),
                                                       "trip_id": row["id"], "name": renamed["name"]}
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
            recalculate_col, delete_col = st.columns(2)
            if recalculate_col.button("Opnieuw berekenen", key="recalculate_" + row["id"], type="primary"):
                open_trip(row)
            if delete_col.button("Trip verwijderen", key="delete_" + row["id"],
                                 help="Verwijdert deze trip met alle bewaarde versies uit deze browser."):
                st.session_state.storage_action = {"op": "delete", "nonce": str(uuid4()), "trip_id": row["id"]}
                st.rerun()
            st.caption("Opnieuw berekenen laadt de instellingen. Klik daarna op Tripreport maken en bewaar de berekende versie.")
            with st.expander("Versies bekijken"):
                st.dataframe(pd.DataFrame(version_table(row)), hide_index=True, use_container_width=True)
        else:
            st.caption("Kies een rij in de tabel om de trip opnieuw te berekenen, te verwijderen of de versies te bekijken.")
    else:
        st.info("Geen bewaarde trips voor deze selectie. Maak een nieuwe trip of importeer je reservekopie.")
    previous_token = st.session_state.get("report_job") or st.session_state.previous_report_token
    if previous_token:
        if st.button("Verdergaan met vorige berekening"):
            st.session_state.report_job = previous_token
            st.session_state.page = "report"
            st.query_params["report"] = previous_token
            st.rerun()
    with st.expander("Reservekopie downloaden of importeren"):
        st.caption("De reservekopie bevat alle gebruikers, trips en bewaarde versies in deze browser.")
        st.download_button("Reservekopie downloaden", json.dumps(st.session_state.saved_rows, ensure_ascii=False, indent=2).encode("utf-8"),
                           "tripreport-bewaarde-trips.json", "application/json")
        with st.form("import_saved_trips"):
            backup = st.file_uploader("Reservekopie importeren", type="json")
            import_now = st.form_submit_button("Importeren")
        if import_now and backup is not None:
            try:
                imported = validate_import(backup.getvalue().decode("utf-8"))
                merged = merge_records(st.session_state.saved_rows, imported)
                st.session_state.storage_action = {"op": "import", "nonce": str(uuid4()), "imported": merged}
                st.rerun()
            except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                st.error(f"Importeren is mislukt: {exc}")
    st.stop()

if st.button("← Mijn trips"):
    st.session_state.page = "home"
    st.session_state.pop("restored_form_token", None)
    st.query_params.pop("report", None)
    st.rerun()
st.markdown('<div class="intro"><b>Je afgeronde reis in soorten.</b> Kies je iNaturalist-gebruikersnaam en de begin- en einddatum met tijd. Het reisgebied volgt automatisch uit de locaties van je waarnemingen. De foto’s komen uit jouw openbare waarnemingen.</div>', unsafe_allow_html=True)

if restore_token:
    restored_job = report_jobs().snapshot(restore_token)
    with st.container(border=True):
        st.subheader("Je vorige berekening")
        if restored_job:
            st.write(restored_job['message'])
            if restored_job['state'] == 'running':
                st.caption("Deze berekening loopt nog. Verdergaan opent dezelfde taak; je hoeft geen nieuwe trip te starten.")
            if st.button("▶ Verdergaan met vorige berekening", type='primary'):
                try:
                    if restored_job['state'] in ('paused','error'):
                        st.session_state.report_job = report_jobs().resume(restore_token)
                    else:
                        st.session_state.report_job = restore_token
                    st.session_state.loaded_report_job = None
                    st.query_params['report'] = st.session_state.report_job
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.info("Je vorige berekening is niet meer op deze server aanwezig. Laad hieronder je herstartbestand om verder te gaan.")

with st.container(border=True):
    st.subheader("Reis instellen")
    st.text_input("Hoe heet deze trip? (verplicht)", placeholder="Bijvoorbeeld: Suriname december 2025", key='trip_name', max_chars=120)
    user_col, from_col, to_col = st.columns([2, 1, 1])
    with user_col:
        username = st.text_input("Openbare iNaturalist-gebruikersnaam", placeholder="Bijvoorbeeld: jouw_gebruikersnaam", key="trip_username").strip()
    with from_col:
        start = st.date_input("Van", min_value=EARLIEST_TRIP_DATE,
                              max_value=date.today(), key="trip_start")
        start_clock = st.time_input("Begintijd", key="trip_start_time", step=60)
    with to_col:
        end = st.date_input("Tot en met", min_value=EARLIEST_TRIP_DATE,
                            max_value=date.today(), key="trip_end")
        end_clock = st.time_input("Eindtijd", key="trip_end_time", step=60)

    st.caption("Tijden volgen de lokale tijd van iedere iNaturalist-waarneming. De eindminuut telt volledig mee. "
               "Het gebied wordt de omhullende grens van de openbare locaties met circa 1 km marge.")
    extended_checks = st.checkbox("Ook nieuw in gebied en nieuw op iNaturalist in de kaartcirkels tonen", value=False, key='map_extra_choice',
                                  help="Deze keuze geldt alleen voor de kaart en de PDF-kaart. Totalen en sterren worden altijd volledig gecontroleerd.")
    go = st.button("🔎 Tripreport maken", type="primary", use_container_width=True)

with st.expander("Berekening hervatten met een herstartbestand"):
    checkpoint_upload = st.file_uploader("Herstartbestand laden", type=['json'], key='checkpoint_upload')
    if st.button("Berekening uit bestand hervatten", disabled=checkpoint_upload is None):
        try:
            token = report_jobs().import_checkpoint(checkpoint_upload.getvalue())
            st.session_state.report_job = token
            st.session_state.loaded_report_job = None
            st.session_state.trip = None
            st.session_state.query = None
            st.query_params['report'] = token
            st.rerun()
        except Exception as exc:
            st.error(f"Hervatten is mislukt: {exc}")


if go:
    if not st.session_state.trip_name.strip():
        st.error("Vul eerst een naam voor deze trip in.")
    elif not username:
        st.error("Vul een iNaturalist-gebruikersnaam in.")
    elif datetime.combine(start, start_clock) > datetime.combine(end, end_clock):
        st.error("De einddatum en -tijd moeten op of na het begin liggen.")
    else:
        token = report_jobs().start((username, start.isoformat(), end.isoformat(),
                                     start_clock.strftime("%H:%M"), end_clock.strftime("%H:%M"), extended_checks, st.session_state.trip_name.strip()), fresh=True)
        st.session_state.report_job = token
        st.query_params["report"] = token
        st.session_state.loaded_report_job = None
        st.session_state.trip = None
        st.session_state.query = None
        st.rerun()


@st.fragment(run_every=2)
def follow_report_job(token):
    job = report_jobs().snapshot(token)
    if job is None:
        st.info("Deze berekening is niet meer op de server beschikbaar. Laad je herstartbestand of klik op Tripreport maken.")
        return
    checkpoint_data = report_jobs().export_checkpoint(token)
    if checkpoint_data:
        st.download_button("Herstartbestand downloaden", checkpoint_data, 'tripreport-herstart.json', 'application/json',
                           key='checkpoint_download_'+token)
        st.caption("Download dit bestand om na verlies van de serveropslag vanaf dit opgeslagen punt verder te gaan.")
    if job['state'] in ('paused', 'error'):
        st.warning("Laatste opgeslagen stap: " + job['message'])
        if st.button("Berekening hervatten", key='resume_'+token):
            try:
                st.session_state.report_job = report_jobs().resume(token)
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
        return
    if job["state"] == "error":
        st.error("Ophalen mislukt: " + job["message"])
        return
    if job["state"] == "running":
        st.info(job["message"])
        st.caption("De berekening gaat op de server verder als je dit scherm verlaat. Keer terug via dezelfde URL.")
        return
    if st.session_state.get("loaded_report_job") == token:
        return
    result = job["result"]
    previous = st.session_state.saved_search
    meta = result["meta"]
    if previous and not same_trip(meta, previous):
        st.session_state.saved_trip_id = None
        st.session_state.saved_search = None
    st.session_state.trip = result["frame"]
    st.session_state.query = meta
    st.session_state.novelty = result["novelty"].copy()
    st.session_state.own_first_ids = result["firsts"]
    st.session_state.report_warnings = result["warnings"]
    st.session_state.pdf_bytes = None
    st.session_state.pdf_key = None
    st.session_state.bulk_failed = False
    st.session_state.slow_mode = False
    st.session_state.loaded_report_job = token
    st.rerun()


token = st.session_state.get("report_job") or st.query_params.get("report")
if token and st.session_state.get("loaded_report_job") != token:
    follow_report_job(token)

def card_html(current):
    cards = []
    colors = {"🟡": ("yellow", "Mijn eerste waarneming"), "🟠": ("orange", "Eerste in automatisch reisgebied"), "🔴": ("red", "Eerste op iNaturalist")}
    for _, row in current.iterrows():
        sid = int(row["species_id"])
        name = html.escape(str(row["Engelse naam"] or row["Wetenschappelijke naam"]))
        scientific = html.escape(str(row["Wetenschappelijke naam"]))
        url = html.escape(str(row["iNaturalist"]), quote=True)
        photo = html.escape(str(row["Foto"] or ""), quote=True)
        record = st.session_state.novelty.get(sid) or {}
        rg = bool(row.get("Trip RG", False))
        badges = []
        for flag, symbol in (("own", "🟡"), ("area", "🟠"), ("global", "🔴")):
            if record.get(flag):
                label = colors[symbol][1]
                badges.append(f'<span class="star {colors[symbol][0]}" title="{label}" aria-label="{label}">★</span>')
        if not badges and record.get("star") == "?":
            badges.append('<span class="star" title="Controle niet gelukt">?</span>')
        badge = '<div class="stars">' + ''.join(badges) + '</div>' if badges else ''
        picture = f'<img class="species-photo" src="{photo}" alt="{name}" loading="lazy">' if photo else '<div class="photo-empty">🌿</div>'
        total = row.get("Mijn waarnemingen wereldwijd", pd.NA)
        total_text = f'{int(total):,} totaal' if pd.notna(total) else 'Totaal onbekend'
        card_class = 'species-card rg' if rg else 'species-card'
        cards.append(f'<article class="{card_class}"><a href="{url}" target="_blank" rel="noopener"><div class="photo-wrap">{picture}{badge}</div><div class="species-body"><div class="species-name">{name}</div><div class="scientific">{scientific}</div><span class="pill">{int(row["Waarnemingen in gebied"]):,} tijdens reis</span> <span class="pill">{total_text}</span></div></a></article>')
    return '<div class="species-grid">' + ''.join(cards) + '</div>'


def summary_html(all_species, meta, novelty):
    ids = all_species["species_id"]
    extended = True
    has_area = extended and bool(meta["places"] or meta["geometry"])
    counts = summary_counts(novelty, ids, has_area)
    pending = any(int(sid) not in novelty for sid in ids)
    def display(value):
        if value is None:
            return "—"
        if pending:
            return "…"
        return f"≥{value:,}" if counts["unresolved"] else f"{value:,}"
    cells = [
        (f"{meta.get('observation_total', int(all_species['Waarnemingen in gebied'].sum())):,}", "Waarnemingen"),
        (f"{meta.get('unidentified_total', 0):,}", "Nog niet op soort"),
        (f"{len(all_species):,}", "Soorten"),
        (display(counts["own"]), "Nieuw voor mij"),
        (display(counts["area"]) if extended else "—", "Nieuw in gebied" if extended else "Gebiedscontrole uit"),
        (display(counts["global"]) if extended else "—", "Nieuw op iNaturalist" if extended else "Wereldcontrole uit"),
    ]
    return '<div class="trip-summary">' + ''.join(
        f'<div class="trip-stat"><strong>{value}</strong><span>{label}</span></div>'
        for value, label in cells
    ) + '</div>'


def show_progressive_grid(current, all_species, meta, summary_slot):
    """Keep the cards in place; update only the progress bar until finished."""
    target = [int(x) for x in all_species["species_id"]]
    remaining = [row for _, row in all_species.iterrows() if int(row["species_id"]) not in st.session_state.novelty]
    summary_slot.markdown(summary_html(all_species, meta, st.session_state.novelty), unsafe_allow_html=True)
    done = len(target) - len(remaining)
    progress = st.empty()
    progress.progress(done / len(target), text=f"Sterren gecontroleerd: {done} van {len(target)}")
    grid = st.empty()
    grid.markdown(card_html(current), unsafe_allow_html=True)
    if not remaining:
        return
    if st.session_state.get("bulk_failed") and not st.session_state.get("slow_mode"):
        st.warning("De snelle groepscontrole is mislukt. Probeer het opnieuw of start de tragere controle per soort.")
        retry, slow = st.columns(2)
        if retry.button("Snelle controle opnieuw proberen"):
            st.session_state.bulk_failed = False
            st.rerun()
        if slow.button("Controle per soort starten"):
            st.session_state.slow_mode = True
            st.rerun()
        return
    if not st.session_state.get("slow_mode") and st.session_state.get("own_first_ids") is None:
        try:
            st.session_state.own_first_ids = own_firsts_in_window(
                meta.get("user_id", meta["username"]), date.fromisoformat(meta["start"]),
                date.fromisoformat(meta["end"]), target)
        except Exception:
            st.session_state.own_first_ids = {}  # The per-species fallback remains available.
    size = 2 if st.session_state.get("slow_mode") else 40
    for offset in range(0, len(remaining), size):
        batch = remaining[offset:offset + size]
        try:
            if st.session_state.get("slow_mode"):
                checked = {int(row["species_id"]): star_for(row["obs_ids"], first_record(
                    int(row["species_id"]), meta.get("user_id", meta["username"]), meta["end"], meta["places"], meta["geometry"]),
                    bool(meta["places"] or meta["geometry"])) for row in batch}
            else:
                checked = batch_stars(batch, meta.get("user_id", meta["username"]), meta["start"], meta["end"], meta["places"], meta["geometry"], st.session_state.own_first_ids)
            st.session_state.novelty.update(checked)
        except Exception as exc:
            if not st.session_state.get("slow_mode"):
                st.session_state.bulk_failed = True
                st.warning(f"Snelle controle gestopt: {exc}. Kies hieronder een vervolg.")
            else:
                for row in batch:
                    st.session_state.novelty[int(row["species_id"])] = {"own": None, "area": None, "global": None, "star": "?"}
            break
        done = len(target) - len(remaining) + min(offset + size, len(remaining))
        progress.progress(done / len(target), text=f"Sterren gecontroleerd: {done} van {len(target)}")
    # One card update after the calculation; no timed redraws or page jumps.
    grid.markdown(card_html(current), unsafe_allow_html=True)
    summary_slot.markdown(summary_html(all_species, meta, st.session_state.novelty), unsafe_allow_html=True)


frame = st.session_state.trip
meta = st.session_state.query
if frame is not None and meta:
    for warning in st.session_state.get("report_warnings", []):
        st.warning(warning)
    st.divider()
    st.subheader("Waar de waarnemingen waren")
    points = meta.get("heat_points") or []
    if points:
        st_folium(leaflet_heatmap(points, circles=meta.get("concentrations", [])),
                  height=680, use_container_width=True, returned_objects=[], key="trip_heatmap")
        st.caption(f"{len(points):,} waarnemingen met openbare locatie. Kleuren tonen de relatieve dichtheid. "
                   "Cirkels: straal 25 km, minstens 26 waarnemingen. Overlappende cirkels kunnen dezelfde waarnemingen bevatten.")
        st.caption("Cirkels tonen waarnemingen, soorten en soorten nieuw voor jou. Nieuw betekent: jouw eerste gedateerde "
                   "iNaturalist-waarneming van die soort ligt in deze cirkel. ≥ … (?) betekent dat de controle onvolledig is.")
        if meta.get('map_extended_checks'):
            st.caption("De extra cirkeltellingen tonen eerste registraties in het automatische reisgebied en op iNaturalist; "
                       "de betreffende eerste waarneming moet binnen deze cirkel liggen.")
    else:
        st.info("Deze selectie heeft geen openbare locaties; er kan geen heatmap of reisgebied worden bepaald.")
    if meta.get("missing_location_total"):
        st.caption(f"{meta['missing_location_total']:,} waarnemingen zonder openbare locatie tellen wel mee in het rapport.")
    if meta.get("unknown_time_total"):
        st.warning(f"{meta['unknown_time_total']:,} waarnemingen zonder bekend tijdstip zijn op een gedeeltelijk gekozen dag niet meegenomen.")
    st.subheader(f"Soorten van {meta['username']}")
    st.caption(f"{meta['start']} {meta.get('start_time', '00:00')} t/m {meta['end']} {meta.get('end_time', '23:59')} · {len(frame):,} soorten · {meta.get('observation_total', int(frame['Waarnemingen in gebied'].sum())):,} waarnemingen")
    active_names = [*meta.get("place_names", ()), *([meta.get("area_name") or "Getekend gebied"] if meta["geometry"] else [])]
    st.caption("Gebied: " + (" of ".join(active_names) if active_names else "wereldwijd (geen gebiedsfilter)"))
    summary_slot = st.empty()
    with st.container(border=True):
        st.caption("Berekend op: " + calculation_label(meta.get("calculated_at")))
        st.caption("Tripnaam: " + (st.session_state.trip_name or meta.get('trip_name') or 'Nog geen naam'))
        if st.button("💾 Versie bewaren", disabled=not st.session_state.trip_name.strip()):
            try:
                snapshot = summary_snapshot(frame, meta, st.session_state.novelty, summary_counts)
                if snapshot["unresolved"]:
                    st.warning("Wacht tot de stercontrole klaar is voordat je deze trip bewaart.")
                else:
                    existing = next((row for row in st.session_state.saved_rows
                                     if row["id"] == st.session_state.saved_trip_id), None)
                    # Recover the trip link after returning via a report URL or herstartbestand.
                    if existing is None:
                        existing = next((row for row in st.session_state.saved_rows
                                         if row["name"] == st.session_state.trip_name.strip()
                                         and same_trip(meta, row["search"])), None)
                    record = make_record(st.session_state.trip_name, meta, snapshot,
                                         st.session_state.saved_trip_id, existing=existing)
                    st.session_state.saved_trip_id = record["id"]
                    st.session_state.saved_search = meta.copy()
                    st.session_state.storage_action = {"op": "save", "nonce": str(uuid4()), "record": record}
                    st.rerun()
            except Exception as exc:
                st.error(f"Bewaren is mislukt: {exc}")
    if not frame.empty and st.button("RG-status actualiseren"):
        with st.spinner("Actuele RG-status van de tripwaarnemingen ophalen…"):
            try:
                st.session_state.trip = refresh_trip_rg(frame,meta.get('user_id',meta['username']),meta['start'],meta['end'])
                st.session_state.pdf_bytes = None
                st.rerun()
            except Exception as exc:
                st.error(f"RG-status kon niet worden geladen: {exc}")
    ordered = frame
    sort_by = "Aantal waarnemingen"
    download_controls = st.empty()
    if frame.empty:
        summary_slot.markdown(summary_html(frame, meta, st.session_state.novelty), unsafe_allow_html=True)
        st.info("Geen op soort geïdentificeerde waarnemingen gevonden binnen deze selectie.")
    else:
        if not meta["places"] and not meta["geometry"]:
            st.info("Zonder openbare locaties kan geen automatisch gebied worden bepaald; oranje sterren zijn dan niet beschikbaar.")
        sort_by = st.selectbox("Volgorde foto's", ["Taxonomie (rijk → soort)", "Aantal waarnemingen"], index=0)
        ordered = sort_species_overview(frame, sort_by)
        maximum = len(ordered)
        shown = st.slider("Aantal soorten tonen", 1, maximum, maximum) if maximum > 10 else maximum
        current = ordered.head(shown)
        st.markdown('<div class="legend"><span><b class="yellow">★</b> Mijn eerste waarneming</span><span><b class="orange">★</b> Eerste in automatisch reisgebied</span><span><b class="red">★</b> Eerste op iNaturalist</span><span>Groene kaartrand: minstens één tripwaarneming is nu Research Grade</span></div>', unsafe_allow_html=True)
        st.caption("Alle toepasselijke sterren staan naast elkaar, onafhankelijk van de kaartkeuze. Bij een te groot historisch kaartgebied kan de oranje ster onbekend blijven.")
        show_progressive_grid(current, ordered, meta, summary_slot)
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", meta["username"])
    completed_checkpoint = report_jobs().export_checkpoint(st.session_state.get('loaded_report_job') or '')
    if completed_checkpoint:
        st.download_button("Herstartbestand downloaden", completed_checkpoint, 'tripreport-herstart.json', 'application/json', key='completed_checkpoint')
    with download_controls.container():
        trip_title = pdf_trip_name(st.session_state.trip_name, st.session_state.saved_rows, meta, st.session_state.saved_trip_id)
        export_version = getattr(report_pdf, 'PDF_EXPORT_VERSION', None)
        export_ready = export_version == 16
        if not export_ready:
            st.error("De PDF-exportcode is nog verouderd. Vervang ook report_pdf.py door het bestand uit versie 16 en herstart de app.")
        pdf_key = (export_version, meta.get('calculated_at'), meta["username"], meta["start"], meta["end"], meta.get("start_time"), meta.get("end_time"), meta["geometry"], sort_by, trip_title)
        if st.button("📄 PDF van volledig overzicht maken", disabled=not export_ready):
            with st.spinner("PDF met heatmap en je eigen foto's maken…"):
                try:
                    st.session_state.pdf_bytes = make_trip_pdf(ordered, {**meta, 'trip_name':trip_title}, st.session_state.novelty)
                    st.session_state.pdf_key = pdf_key
                except Exception as exc:
                    st.error(f"De PDF kon niet worden gemaakt: {exc}")
        if export_ready and st.session_state.get("pdf_bytes") and st.session_state.get("pdf_key") == pdf_key:
            st.download_button("⬇️ PDF downloaden", st.session_state.pdf_bytes,
                               pdf_filename(trip_title), "application/pdf")
    unclassified = meta.get('unidentified_records') or []
    if unclassified:
        st.subheader(f"Nog niet op soort geïdentificeerd ({len(unclassified):,} waarnemingen)")
        cards=[]
        for observation in unclassified:
            photo=html.escape(str(observation.get('photo') or '').replace('medium.','small.'),quote=True)
            name=html.escape(str(observation.get('name') or 'Onbekend'))
            url=html.escape(str(observation.get('url') or ''),quote=True)
            picture=f'<img src="{photo}" loading="lazy" alt="{name}">' if photo else '<div class="photo-empty">?</div>'
            cards.append(f'<a href="{url}" target="_blank" rel="noopener">{picture}<div>{name}</div></a>')
        st.markdown('<style>.unclassified-grid{display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:6px}.unclassified-grid a{border:1px solid #d2dfd5;border-radius:6px;padding:4px;color:#173d2e;font-size:10px;overflow:hidden}.unclassified-grid img{width:100%;height:75px;object-fit:contain}.unclassified-grid .photo-empty{height:75px}</style><div class="unclassified-grid">'+''.join(cards)+'</div>',unsafe_allow_html=True)
