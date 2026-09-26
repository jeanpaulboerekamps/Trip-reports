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

from taxonomy import sort_species_overview
from trip_data import first_record, normalize_geometry, search_places, species_frame, star_for, trip_observations

st.set_page_config(page_title="Tripreport Verkenner", page_icon="🧭", layout="wide")
st.markdown("""<style>
.block-container{max-width:1250px;padding-top:1.4rem;padding-bottom:3rem}
.intro{padding:1rem 1.2rem;border-radius:16px;background:#eaf4ed;border:1px solid #c6ddcc;margin:.5rem 0 1.2rem}
.species-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:1rem;margin:.8rem 0 1rem}
.species-card{border:1px solid #cad6cd;border-radius:13px;overflow:hidden;background:var(--secondary-background-color)}
.species-card a{color:inherit;text-decoration:none}.photo-wrap{position:relative}
.species-photo,.photo-empty{height:170px;width:100%;object-fit:cover;display:block;background:#e4ede7}
.photo-empty{display:flex;align-items:center;justify-content:center;font-size:2rem}
.star{position:absolute;right:10px;top:8px;font-size:2rem;line-height:1;text-shadow:0 1px 5px #343a32,0 0 2px #fff}
.star.red{color:#e3342f}.star.orange{color:#f28b24}.star.yellow{color:#f0cc24}
.species-body{padding:.8rem}.species-name{font-weight:750;line-height:1.2}.scientific{font-style:italic;opacity:.72;font-size:.9rem;margin:.18rem 0 .65rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pill{font-size:.8rem;background:rgba(58,130,79,.13);border-radius:30px;padding:.25rem .5rem}
.legend{display:flex;gap:1rem;flex-wrap:wrap;margin:.7rem 0 1.1rem}.legend span{font-size:.92rem}
.legend b{font-size:1.35rem;vertical-align:middle}.legend .red{color:#e3342f}.legend .orange{color:#f28b24}.legend .yellow{color:#e3b51e}
@media(max-width:540px){.species-grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}.species-photo,.photo-empty{height:130px}.species-body{padding:.58rem}.species-name{font-size:.95rem}}
</style>""", unsafe_allow_html=True)

for key, value in {"places": [], "geometry": None, "area_name": "", "trip": None, "query": None, "stars": {}, "place_results": [], "show_map": False}.items():
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
            st.session_state.place_results = search_places(query)
        except Exception as exc:
            st.error(str(exc))
    if st.session_state.place_results:
        choices = {f"{p['name']} · {p['id']}": p for p in st.session_state.place_results}
        pick = st.selectbox("Kies een plaats", ["— Selecteer —", *choices], key="place_pick")
        if st.button("Plaats toevoegen", disabled=pick not in choices):
            p = choices[pick]
            if p["id"] not in [x["id"] for x in st.session_state.places]:
                st.session_state.places.append(p)
            st.session_state.place_results = []
            st.rerun()
    if st.session_state.places:
        st.caption("Gekozen: " + " · ".join(p["name"] for p in st.session_state.places))
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
                st.session_state.trip = frame
                st.session_state.query = {"username": username, "start": start.isoformat(), "end": end.isoformat(),
                                          "places": places, "geometry": json.dumps(geometry, sort_keys=True) if geometry else ""}
                st.session_state.stars = {}
                status.update(label="Tripreport gereed", state="complete")
            except Exception as exc:
                status.update(label="Ophalen mislukt", state="error")
                st.error(str(exc))

frame = st.session_state.trip
meta = st.session_state.query
if frame is not None and meta:
    st.divider()
    st.subheader(f"Soorten van {meta['username']}")
    st.caption(f"{meta['start']} t/m {meta['end']} · {len(frame):,} soorten · {int(frame['Waarnemingen in gebied'].sum()) if len(frame) else 0:,} waarnemingen")
    if frame.empty:
        st.info("Geen op soort geïdentificeerde waarnemingen gevonden binnen deze selectie.")
    else:
        sort_by = st.selectbox("Volgorde foto's", ["Taxonomie (rijk → soort)", "Aantal waarnemingen"], index=0)
        ordered = sort_species_overview(frame, sort_by)
        maximum = len(ordered)
        shown = st.slider("Aantal soorten tonen", 1, maximum, min(50, maximum)) if maximum > 10 else maximum
        current = ordered.head(shown)
        untested = [r for _, r in current.iterrows() if int(r["species_id"]) not in st.session_state.stars]
        if untested:
            with st.status(f"Sterren controleren voor {len(untested)} soorten…", expanded=False) as star_status:
                for _, row in current.iterrows():
                    sid = int(row["species_id"])
                    if sid in st.session_state.stars:
                        continue
                    try:
                        first = first_record(sid, meta["username"], meta["end"], meta["places"], meta["geometry"])
                        st.session_state.stars[sid] = star_for(row["obs_ids"], first)
                    except Exception:
                        st.session_state.stars[sid] = "?"
                star_status.update(label="Sterren gecontroleerd", state="complete")
        st.markdown('<div class="legend"><span><b class="yellow">★</b> Mijn eerste waarneming</span><span><b class="orange">★</b> Eerste in gekozen gebied</span><span><b class="red">★</b> Eerste op iNaturalist</span></div>', unsafe_allow_html=True)
        st.caption("Per soort verschijnt de hoogste toepasselijke ster (rood > oranje > geel). De ster geldt als de allereerste waarneming van die soort precies één van jouw geselecteerde reiswaarnemingen is. Bij een te groot historisch kaartgebied wordt de oranje ster overgeslagen; een vraagteken betekent dat de controle niet lukte.")
        cards = []
        colors = {"🟡": ("yellow", "Mijn eerste waarneming"), "🟠": ("orange", "Eerste in gekozen gebied"), "🔴": ("red", "Eerste op iNaturalist")}
        for _, row in current.iterrows():
            sid = int(row["species_id"])
            name = html.escape(str(row["Engelse naam"] or row["Wetenschappelijke naam"]))
            scientific = html.escape(str(row["Wetenschappelijke naam"]))
            url = html.escape(str(row["iNaturalist"]), quote=True)
            photo = html.escape(str(row["Foto"] or ""), quote=True)
            star = st.session_state.stars.get(sid, "")
            badge = f'<span class="star {colors[star][0]}" title="{colors[star][1]}" aria-label="{colors[star][1]}">★</span>' if star in colors else ('<span class="star" title="Controle niet gelukt">?</span>' if star == '?' else '')
            picture = f'<img class="species-photo" src="{photo}" alt="{name}" loading="lazy">' if photo else '<div class="photo-empty">🌿</div>'
            cards.append(f'<article class="species-card"><a href="{url}" target="_blank" rel="noopener"><div class="photo-wrap">{picture}{badge}</div><div class="species-body"><div class="species-name">{name}</div><div class="scientific">{scientific}</div><span class="pill">{int(row["Waarnemingen in gebied"]):,} waarnemingen</span></div></a></article>')
        st.markdown('<div class="species-grid">'+''.join(cards)+'</div>', unsafe_allow_html=True)
        export = ordered.drop(columns=["obs_ids", "Foto"], errors="ignore").copy()
        export["Ster"] = export["species_id"].map(st.session_state.stars).fillna("").map({"🟡":"Eigen eerste", "🟠":"Eerste in gebied", "🔴":"Eerste iNaturalist", "?":"Niet gecontroleerd"}).fillna("")
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", meta["username"])
        st.download_button("⬇️ Soortenlijst als CSV", export.to_csv(index=False).encode("utf-8-sig"), f"tripreport_{safe}_{meta['start']}_{meta['end']}.csv", "text/csv")
