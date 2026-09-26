"""Tripreport Verkenner — afgeronde reizen met openbare iNaturalist-gegevens."""
from datetime import date, timedelta
import html
import json
import re

import folium
import pandas as pd
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium

from report_pdf import make_trip_pdf
from taxonomy import sort_species_overview
from trip_data import batch_stars, exact_place_match, first_record, normalize_geometry, own_firsts_in_window, personal_species_counts, search_places, species_frame, star_for, summary_counts, trip_observations

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
.star.yellow.rg{-webkit-text-stroke:1.8px #d22e32;paint-order:stroke fill}
.species-body{padding:.8rem}.species-name{font-weight:750;line-height:1.2}.scientific{font-style:italic;opacity:.72;font-size:.9rem;margin:.18rem 0 .65rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pill{font-size:.8rem;background:rgba(58,130,79,.13);border-radius:30px;padding:.25rem .5rem}
.legend{display:flex;gap:1rem;flex-wrap:wrap;margin:.7rem 0 1.1rem}.legend span{font-size:.92rem}
.legend b{font-size:1.35rem;vertical-align:middle}.legend .red{color:#e3342f}.legend .orange{color:#f28b24}.legend .yellow{color:#e3b51e}.legend .yellow.rg{-webkit-text-stroke:1.5px #d22e32;paint-order:stroke fill}
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

st.title("🧭 Tripreport Verkenner")
st.markdown('<div class="intro"><b>Je afgeronde reis in soorten.</b> Kies je iNaturalist-gebruikersnaam, reisdatums en een gebied. De foto’s komen uit jouw openbare waarnemingen.</div>', unsafe_allow_html=True)

with st.container(border=True):
    st.subheader("Reis instellen")
    user_col, from_col, to_col = st.columns([2, 1, 1])
    with user_col:
        username = st.text_input("Openbare iNaturalist-gebruikersnaam", placeholder="Bijvoorbeeld: jouw_gebruikersnaam").strip()
    with from_col:
        start = st.date_input("Van", value=date.today() - timedelta(days=7), max_value=date.today())
    with to_col:
        end = st.date_input("Tot en met", value=date.today() - timedelta(days=1), max_value=date.today())

    st.markdown("**Land of streek toevoegen**")
    with st.form("place_search", clear_on_submit=False):
        pc, bc = st.columns([4, 1])
        with pc:
            query = st.text_input("Zoek een iNaturalist-plaats", placeholder="Bijvoorbeeld: Nederland, Gelderland of Noord-Holland", label_visibility="collapsed")
        with bc:
            search = st.form_submit_button("Zoeken", use_container_width=True)
    if search:
        try:
            found = search_places(query)
            exact = exact_place_match(query, found)
            if exact:
                if exact["id"] not in [p["id"] for p in st.session_state.places]:
                    st.session_state.places.append(exact)
                st.session_state.place_results = []
                st.success(f"{exact['name']} is toegevoegd als actief gebied.")
            else:
                st.session_state.place_results = found
                if not found:
                    st.warning("Geen iNaturalist-plaats gevonden. Probeer een andere naam.")
        except Exception as exc:
            st.error(str(exc))
    if st.session_state.place_results:
        st.warning("De zoektekst is nog geen gebiedsfilter. Kies hieronder een resultaat en klik op ‘Plaats toevoegen’.")
        choices = {f"{p['name']} · {p['id']}": p for p in st.session_state.place_results}
        pick = st.selectbox("Kies een plaats", ["— Selecteer —", *choices], key="place_pick")
        if st.button("Plaats toevoegen", type="primary", disabled=pick not in choices):
            p = choices[pick]
            if p["id"] not in [x["id"] for x in st.session_state.places]:
                st.session_state.places.append(p)
            st.session_state.place_results = []
            st.rerun()
    if st.session_state.places:
        st.success("Actief gebied: " + " · ".join(p["name"] for p in st.session_state.places))
        remove = st.selectbox("Plaats verwijderen", ["— Geen —", *[p["name"] for p in st.session_state.places]])
        if remove != "— Geen —" and st.button("Verwijder plaats"):
            st.session_state.places = [p for p in st.session_state.places if p["name"] != remove]
            st.rerun()
    st.caption("Meerdere plaatsen en een getekend gebied vormen samen één gebied (vereniging).")

    if st.button("🗺️ Gebied tekenen" if not st.session_state.show_map else "Kaart sluiten"):
        st.session_state.show_map = not st.session_state.show_map
    if st.session_state.show_map:
        name = st.text_input("Naam voor getekend gebied", value=st.session_state.area_name or "Mijn reisgebied")
        m = folium.Map(location=[20, 5], zoom_start=2, tiles="OpenStreetMap", control_scale=True)
        Draw(export=False, draw_options={"polyline":False,"circle":False,"circlemarker":False,"marker":False,
                                         "polygon":{"allowIntersection":False},"rectangle":True},
             edit_options={"edit":True,"remove":True}).add_to(m)
        state = st_folium(m, height=430, use_container_width=True, key="trip_map", returned_objects=["all_drawings"])
        drawings = state.get("all_drawings") or []
        if st.button("Getekend gebied gebruiken", disabled=not drawings):
            geometry = normalize_geometry(drawings[-1].get("geometry"))
            if geometry:
                st.session_state.geometry = geometry
                st.session_state.area_name = name.strip() or "Mijn reisgebied"
                st.session_state.show_map = False
                st.rerun()
            st.error("Dit gebied heeft geen geldige vorm. Teken een nieuwe veelhoek of rechthoek.")
    if st.session_state.geometry:
        c1, c2 = st.columns([3, 1])
        c1.success(f"Getekend gebied actief: {st.session_state.area_name}")
        if c2.button("Wis tekening"):
            st.session_state.geometry = None
            st.session_state.area_name = ""
            st.rerun()
    st.caption("Zonder gebied zoeken we wereldwijd. Bij een tekening tellen alleen waarnemingen met openbare coördinaten binnen de exacte grens.")
    if not st.session_state.places and not st.session_state.geometry:
        st.info("Er is nog geen gebied gekozen. Voeg een zoekresultaat toe met ‘Plaats toevoegen’ of teken een gebied om oranje sterren te berekenen.")
    go = st.button("🔎 Tripreport maken", type="primary", use_container_width=True)

if go:
    if not username:
        st.error("Vul een iNaturalist-gebruikersnaam in.")
    elif start > end:
        st.error("De einddatum moet op of na de begindatum liggen.")
    else:
        places = tuple(p["id"] for p in st.session_state.places)
        geometry = st.session_state.geometry
        with st.status("Reisgegevens ophalen…", expanded=True) as status:
            try:
                obs = trip_observations(username, start, end, places, geometry)
                st.write(f"{len(obs):,} openbare waarnemingen gevonden; soorten en taxonomie opbouwen…")
                frame = species_frame(obs)
                if not frame.empty:
                    st.write("Je totale aantallen per soort ophalen…")
                    try:
                        counts = personal_species_counts(username, frame["species_id"])
                        frame["Mijn waarnemingen wereldwijd"] = frame["species_id"].map(counts).fillna(0).astype(int)
                    except Exception as exc:
                        frame["Mijn waarnemingen wereldwijd"] = pd.NA
                        st.warning(f"De totale aantallen konden niet worden geladen: {exc}")
                st.session_state.trip = frame
                st.session_state.query = {"username": username, "start": start.isoformat(), "end": end.isoformat(),
                                          "places": places, "geometry": json.dumps(geometry, sort_keys=True) if geometry else "",
                                          "place_names": tuple(p["name"] for p in st.session_state.places),
                                          "area_name": st.session_state.area_name if geometry else "",
                                          "observation_total": len(obs),
                                          "unidentified_total": len(obs) - int(frame["Waarnemingen in gebied"].sum())}
                st.session_state.novelty = {}
                st.session_state.own_first_ids = None
                st.session_state.pdf_bytes = None
                st.session_state.pdf_key = None
                st.session_state.bulk_failed = False
                st.session_state.slow_mode = False
                status.update(label="Tripreport gereed", state="complete")
            except Exception as exc:
                status.update(label="Ophalen mislukt", state="error")
                st.error(str(exc))

def card_html(current):
    cards = []
    colors = {"🟡": ("yellow", "Mijn eerste waarneming"), "🟠": ("orange", "Eerste in gekozen gebied"), "🔴": ("red", "Eerste op iNaturalist")}
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
                outline = " rg" if flag == "own" and rg else ""
                label = colors[symbol][1] + (" · rode rand: Research Grade tijdens deze reis" if outline else "")
                badges.append(f'<span class="star {colors[symbol][0]}{outline}" title="{label}" aria-label="{label}">★</span>')
        if not badges and record.get("star") == "?":
            badges.append('<span class="star" title="Controle niet gelukt">?</span>')
        badge = '<div class="stars">' + ''.join(badges) + '</div>' if badges else ''
        picture = f'<img class="species-photo" src="{photo}" alt="{name}" loading="lazy">' if photo else '<div class="photo-empty">🌿</div>'
        total = row.get("Mijn waarnemingen wereldwijd", pd.NA)
        total_text = f'{int(total):,} totaal' if pd.notna(total) else 'Totaal onbekend'
        cards.append(f'<article class="species-card"><a href="{url}" target="_blank" rel="noopener"><div class="photo-wrap">{picture}{badge}</div><div class="species-body"><div class="species-name">{name}</div><div class="scientific">{scientific}</div><span class="pill">{int(row["Waarnemingen in gebied"]):,} tijdens reis</span> <span class="pill">{total_text}</span></div></a></article>')
    return '<div class="species-grid">' + ''.join(cards) + '</div>'


def summary_html(all_species, meta, novelty):
    ids = all_species["species_id"]
    has_area = bool(meta["places"] or meta["geometry"])
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
        (display(counts["area"]), "Nieuw in gebied" if has_area else "Geen gebied gekozen"),
        (display(counts["global"]), "Nieuw op iNaturalist"),
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
                meta["username"], date.fromisoformat(meta["start"]),
                date.fromisoformat(meta["end"]), target)
        except Exception:
            st.session_state.own_first_ids = {}  # The per-species fallback remains available.
    size = 2 if st.session_state.get("slow_mode") else 40
    for offset in range(0, len(remaining), size):
        batch = remaining[offset:offset + size]
        try:
            if st.session_state.get("slow_mode"):
                checked = {int(row["species_id"]): star_for(row["obs_ids"], first_record(
                    int(row["species_id"]), meta["username"], meta["end"], meta["places"], meta["geometry"]),
                    bool(meta["places"] or meta["geometry"])) for row in batch}
            else:
                checked = batch_stars(batch, meta["username"], meta["start"], meta["end"], meta["places"], meta["geometry"], st.session_state.own_first_ids)
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
    st.divider()
    st.subheader(f"Soorten van {meta['username']}")
    st.caption(f"{meta['start']} t/m {meta['end']} · {len(frame):,} soorten · {meta.get('observation_total', int(frame['Waarnemingen in gebied'].sum())):,} waarnemingen")
    active_names = [*meta.get("place_names", ()), *([meta.get("area_name") or "Getekend gebied"] if meta["geometry"] else [])]
    st.caption("Gebied: " + (" of ".join(active_names) if active_names else "wereldwijd (geen gebiedsfilter)"))
    summary_slot = st.empty()
    if frame.empty:
        summary_slot.markdown(summary_html(frame, meta, st.session_state.novelty), unsafe_allow_html=True)
        st.info("Geen op soort geïdentificeerde waarnemingen gevonden binnen deze selectie.")
    else:
        if not meta["places"] and not meta["geometry"]:
            st.info("Oranje sterren zijn pas mogelijk na het toevoegen van een land of streek, of het tekenen van een gebied. Maak daarna het tripreport opnieuw.")
        sort_by = st.selectbox("Volgorde foto's", ["Taxonomie (rijk → soort)", "Aantal waarnemingen"], index=0)
        ordered = sort_species_overview(frame, sort_by)
        maximum = len(ordered)
        shown = st.slider("Aantal soorten tonen", 1, maximum, maximum) if maximum > 10 else maximum
        current = ordered.head(shown)
        st.markdown('<div class="legend"><span><b class="yellow">★</b> Mijn eerste waarneming</span><span><b class="yellow rg">★</b> Eigen eerste met Research Grade tijdens reis</span><span><b class="orange">★</b> Eerste in gekozen gebied</span><span><b class="red">★</b> Eerste op iNaturalist</span></div>', unsafe_allow_html=True)
        st.caption("Alle toepasselijke sterren staan naast elkaar. Eigen en gebiedseerste worden onafhankelijk gecontroleerd. Bij een te groot historisch kaartgebied kan de oranje ster onbekend blijven.")
        download_controls = st.empty()
        show_progressive_grid(current, ordered, meta, summary_slot)
        export = ordered.drop(columns=["obs_ids", "Foto"], errors="ignore").copy()
        export["Ster"] = export["species_id"].map(lambda sid: (st.session_state.novelty.get(int(sid)) or {}).get("star", ""))
        for column, flag in [("Nieuw voor mij", "own"), ("Nieuw in gebied", "area"), ("Nieuw op iNaturalist", "global")]:
            export[column] = export["species_id"].map(lambda sid: (st.session_state.novelty.get(int(sid)) or {}).get(flag))
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", meta["username"])
        with download_controls.container():
            csv_col, pdf_col = st.columns(2)
            with csv_col:
                st.download_button("⬇️ Soortenlijst als CSV", export.to_csv(index=False).encode("utf-8-sig"), f"tripreport_{safe}_{meta['start']}_{meta['end']}.csv", "text/csv")
            with pdf_col:
                pdf_key = (meta["username"], meta["start"], meta["end"], meta["places"], meta["geometry"], sort_by)
                if st.button("📄 PDF van volledig overzicht maken"):
                    with st.spinner("PDF met je eigen foto's maken…"):
                        try:
                            st.session_state.pdf_bytes = make_trip_pdf(ordered, meta, st.session_state.novelty)
                            st.session_state.pdf_key = pdf_key
                        except Exception as exc:
                            st.error(f"De PDF kon niet worden gemaakt: {exc}")
                if st.session_state.get("pdf_bytes") and st.session_state.get("pdf_key") == pdf_key:
                    st.download_button("⬇️ PDF downloaden", st.session_state.pdf_bytes,
                                       f"tripreport_{safe}_{meta['start']}_{meta['end']}.pdf", "application/pdf")
