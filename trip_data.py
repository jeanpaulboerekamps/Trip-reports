"""iNaturalist access and trip/first-record calculations."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from functools import lru_cache
import math
import threading
import time

import pandas as pd
import requests
from shapely.geometry import Point, shape
from taxonomy import load_leaf_taxonomy, rank_id, enrich_species_taxonomy, sort_species_overview

API = "https://api.inaturalist.org/v1"
_lock = threading.Lock()
_last_request = 0.0


def get(path, params=None):
    global _last_request
    error = None
    for attempt in range(4):
        try:
            with _lock:
                wait = 1.02 - (time.monotonic() - _last_request)
                if wait > 0:
                    time.sleep(wait)
                _last_request = time.monotonic()
            response = requests.get(API + path, params=params or {}, timeout=(10, 45),
                                    headers={"User-Agent": "Tripreport-Verkenner/1.0"})
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            error = exc
            time.sleep(.5 * 2 ** attempt)
    raise RuntimeError(f"iNaturalist kon niet worden bereikt: {error}")


def search_places(query):
    if len(query.strip()) < 2:
        return []
    data = get("/places/autocomplete", {"q": query.strip(), "per_page": 15})
    return [{"id": int(p["id"]), "name": p.get("display_name") or p.get("name")}
            for p in data.get("results", []) if p.get("id")]


def normalize_geometry(geometry):
    """Normalize Leaflet longitudes after wrapping over the dateline."""
    if not geometry or geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return None
    def ring(points):
        return [[((float(p[0]) + 180) % 360) - 180, float(p[1])] for p in points]
    try:
        coords = geometry["coordinates"]
        converted = [list(map(ring, polygon)) for polygon in coords] if geometry["type"] == "MultiPolygon" else list(map(ring, coords))
        result = {"type": geometry["type"], "coordinates": converted}
        return result if shape(result).is_valid and not shape(result).is_empty else None
    except (ValueError, TypeError, KeyError, IndexError):
        return None


def _pages(params):
    """Fetch all pages. Split dense date windows so the API's 10k cap is explicit."""
    first = get("/observations", {**params, "page": 1, "per_page": 200})
    total = int(first.get("total_results") or 0)
    if total > 10000:
        start, end = date.fromisoformat(params["d1"]), date.fromisoformat(params["d2"])
        if start >= end:
            raise RuntimeError("Meer dan 10.000 waarnemingen op één dag. Verklein het gebied of kies een kleinere soortgroep.")
        mid = start + timedelta(days=(end - start).days // 2)
        a = _pages({**params, "d2": mid.isoformat()})
        b = _pages({**params, "d1": (mid + timedelta(days=1)).isoformat()})
        return a + b
    pages = [first.get("results", [])]
    count = math.ceil(total / 200)
    if count > 1:
        with ThreadPoolExecutor(max_workers=min(4, count - 1)) as pool:
            jobs = {pool.submit(get, "/observations", {**params, "page": page, "per_page": 200}): page
                    for page in range(2, count + 1)}
            fetched = {page: future.result().get("results", []) for future, page in jobs.items()}
        pages += [fetched[page] for page in range(2, count + 1)]
    return [row for page in pages for row in page]


def trip_observations(username, start, end, place_ids=(), geometry=None):
    base = {"user_id": username, "d1": start.isoformat(), "d2": end.isoformat(),
            "order_by": "observed_on", "order": "asc", "locale": "en"}
    collected = {}
    if not place_ids and not geometry:
        collected = {int(o["id"]): o for o in _pages(base)}
    for place_id in place_ids:
        for o in _pages({**base, "place_id": place_id}):
            collected[int(o["id"])] = o
    if geometry:
        polygon = shape(geometry)
        west, south, east, north = polygon.bounds
        if west < east and east - west < 350:
            spatial = {"swlat": south, "swlng": west, "nelat": north, "nelng": east, "geo": "true"}
        else:
            spatial = {"geo": "true", "swlat": south, "nelat": north}
        for o in _pages({**base, **spatial}):
            coords = (o.get("geojson") or {}).get("coordinates") or []
            if len(coords) >= 2 and polygon.covers(Point(coords[0], coords[1])):
                collected[int(o["id"])] = o
    return sorted(collected.values(), key=lambda o: (o.get("observed_on") or "", o["id"]))


def _compact_taxon(t):
    t = t or {}
    return {"id": t.get("id"), "rank": t.get("rank"), "name": t.get("name"),
            "preferred_common_name": t.get("preferred_common_name"),
            "ancestor_ids": [int(x) for x in t.get("ancestor_ids") or [] if str(x).isdigit()],
            "photo": (t.get("default_photo") or {}).get("medium_url") or
                     (t.get("default_photo") or {}).get("url") or ""}


def taxonomy(ids):
    def fetch(batch, locale):
        data = get("/taxa/" + ",".join(map(str, batch)), {"locale": locale, "per_page": len(batch)})
        return [{**_compact_taxon(t), "ancestors": [_compact_taxon(a) for a in t.get("ancestors") or []]}
                for t in data.get("results", [])]
    return load_leaf_taxonomy(tuple(ids), fetch, "en")


def species_frame(observations):
    taxa = [o.get("taxon") or {} for o in observations]
    ids = {int(t["id"]) for t in taxa if t.get("id") and str(t["id"]).isdigit()}
    lookup = taxonomy(ids)
    rows = {}
    for o in observations:
        t = _compact_taxon(o.get("taxon"))
        sid = rank_id(t, lookup, "species")
        if not sid:
            continue
        taxon = lookup.get(sid, {})
        row = rows.setdefault(sid, {"species_id": sid, "Engelse naam": taxon.get("preferred_common_name") or taxon.get("name") or t.get("name") or "Onbekend",
                                    "Wetenschappelijke naam": taxon.get("name") or t.get("name") or "",
                                    "Waarnemingen in gebied": 0, "Foto": taxon.get("photo") or t.get("photo") or "",
                                    "iNaturalist": f"https://www.inaturalist.org/taxa/{sid}", "obs_ids": set(),
                                    "Trip RG": False})
        row["Waarnemingen in gebied"] += 1
        row["obs_ids"].add(int(o["id"]))
        row["Trip RG"] = row["Trip RG"] or o.get("quality_grade") == "research"
        photos = o.get("photos") or []
        if photos and not row["Foto"]:
            row["Foto"] = photos[0].get("url", "").replace("square", "medium")
    if not rows:
        return pd.DataFrame(columns=["species_id", "Engelse naam", "Wetenschappelijke naam", "Waarnemingen in gebied", "Foto", "iNaturalist", "obs_ids", "Trip RG"])
    frame = pd.DataFrame(rows.values())
    return enrich_species_taxonomy(frame, lookup)


def personal_species_counts(username, species_ids):
    """Count all of the observer's records for trip species with a few pages."""
    wanted = {int(x) for x in species_ids}
    if not wanted:
        return {}

    def page(params, number):
        return get("/observations/species_counts", {**params, "page": number, "per_page": 500})

    def collect(params):
        first = page(params, 1)
        total = int(first.get("total_results") or 0)
        if total > 10000:
            raise RuntimeError("Meer dan 10.000 taxa in de persoonlijke soortenlijst")
        count = math.ceil(total / 500)
        results = list(first.get("results", []))
        if count > 1:
            with ThreadPoolExecutor(max_workers=min(4, count - 1)) as pool:
                pages = list(pool.map(lambda n: page(params, n), range(2, count + 1)))
            results.extend(row for data in pages for row in data.get("results", []))
        return results

    try:
        rows = collect({"user_id": username, "locale": "en"})
    except RuntimeError as exc:
        if "10.000 taxa" not in str(exc):
            raise
        rows = []
        # Only extremely long personal life lists need targeted requests.
        ids = sorted(wanted)
        for start in range(0, len(ids), 40):
            rows.extend(collect({"user_id": username,
                                 "taxon_ids": ",".join(map(str, ids[start:start + 40]))}))
    counts = {sid: 0 for sid in wanted}
    for item in rows:
        taxon = item.get("taxon") or {}
        lineage = {int(x) for x in [taxon.get("id"), *(taxon.get("ancestor_ids") or [])]
                   if x and str(x).isdigit()}
        matching = wanted & lineage
        if len(matching) == 1:
            counts[next(iter(matching))] += int(item.get("count") or 0)
    return counts


def _first(params, geometry=None):
    """Find earliest exact match. For a polygon, inspect pages until inside."""
    if not geometry:
        rows = get("/observations", {**params, "per_page": 1, "page": 1, "order_by": "observed_on", "order": "asc"})
        return (rows.get("results") or [None])[0]
    polygon = shape(geometry)
    west, south, east, north = polygon.bounds
    bbox = {"swlat": south, "nelat": north, "geo": "true"}
    if west < east and east - west < 350:
        bbox.update({"swlng": west, "nelng": east})
    query = {**params, **bbox, "per_page": 200, "order_by": "observed_on", "order": "asc"}
    first = get("/observations", {**query, "page": 1})
    total = int(first.get("total_results") or 0)
    if total > 10000:
        return None, False
    for page in range(1, math.ceil(total / 200) + 1):
        items = first.get("results", []) if page == 1 else get("/observations", {**query, "page": page}).get("results", [])
        for o in items:
            c = (o.get("geojson") or {}).get("coordinates") or []
            if len(c) >= 2 and polygon.covers(Point(c[0], c[1])):
                return o, True
    return None, True


@lru_cache(maxsize=15000)
def first_record(species_id, username, end, place_ids, geometry_json):
    """Return earliest IDs (own, area, global) and whether area is verifiable."""
    import json
    own = _first({"taxon_id": species_id, "user_id": username, "d2": end})
    global_first = _first({"taxon_id": species_id, "d2": end})
    candidates = []
    complete = True
    for pid in place_ids:
        item = _first({"taxon_id": species_id, "place_id": pid, "d2": end})
        if item:
            candidates.append(item)
    if geometry_json:
        item, exact = _first({"taxon_id": species_id, "d2": end}, json.loads(geometry_json))
        complete = exact
        if item:
            candidates.append(item)
    area = min(candidates, key=lambda o: (o.get("observed_on") or "9999", o["id"])) if candidates else None
    return (own or {}).get("id"), (area or {}).get("id"), (global_first or {}).get("id"), complete


def star_for(ids, first):
    """Highest priority star, awarded only for an exact trip observation ID."""
    own, area, global_id, complete = first
    if global_id in ids:
        return "🔴"
    if complete and area in ids:
        return "🟠"
    if own in ids:
        return "🟡"
    return ""


def _prior_species(ids, cutoff, **filters):
    """Get prior species in one aggregated request per small taxon batch."""
    if not ids:
        return set()
    wanted = set(map(int, ids))
    params = {"taxon_ids": ",".join(map(str, sorted(wanted))), "d2": cutoff,
              "per_page": 500, **filters}
    first = get("/observations/species_counts", {**params, "page": 1})
    total = int(first.get("total_results") or 0)
    if total > 10000:
        raise RuntimeError("Te veel historische taxa voor een betrouwbare groepscontrole")
    present = set()
    for page in range(1, math.ceil(total / 500) + 1):
        result = first if page == 1 else get("/observations/species_counts", {**params, "page": page})
        for item in result.get("results", []):
            taxon = item.get("taxon") or {}
            lineage = {int(x) for x in [taxon.get("id"), *(taxon.get("ancestor_ids") or [])]
                       if x and str(x).isdigit()}
            present.update(wanted & lineage)
    return present


def batch_stars(rows, username, start, end, place_ids=(), geometry_json=""):
    """Eliminate own, then area, then global prior records in that order."""
    ids = [int(row["species_id"]) for row in rows]
    cutoff = (date.fromisoformat(start) - timedelta(days=1)).isoformat()
    own_prior = _prior_species(ids, cutoff, user_id=username)
    own_new = [sid for sid in ids if sid not in own_prior]
    if not own_new:
        return {sid: "" for sid in ids}

    area_prior = set()
    area_uncertain = set()
    if place_ids:
        with ThreadPoolExecutor(max_workers=min(4, len(place_ids))) as pool:
            jobs = [pool.submit(_prior_species, own_new, cutoff, place_id=pid)
                    for pid in place_ids]
            area_prior = set().union(*(job.result() for job in jobs))
    if geometry_json:
        import json
        geometry = json.loads(geometry_json)
        def check_prior_polygon(sid):
            item, complete = _first({"taxon_id": sid, "d2": cutoff}, geometry)
            return sid, bool(item), complete
        with ThreadPoolExecutor(max_workers=4) as pool:
            for sid, found, complete in pool.map(
                check_prior_polygon, (sid for sid in own_new if sid not in area_prior)
            ):
                if found:
                    area_prior.add(sid)
                elif not complete:
                    area_uncertain.add(sid)

    # A prior record in the selected area rules out a worldwide first.
    global_candidates = [sid for sid in own_new if sid not in area_prior]
    global_prior = _prior_species(global_candidates, cutoff) if global_candidates else set()

    def check_one(row):
        sid = int(row["species_id"])
        observed = row["obs_ids"]
        # A global first is necessarily an own first and an area first.
        if sid in own_prior:
            return sid, ""
        if sid not in area_prior and sid not in global_prior:
            candidate = _first({"taxon_id": sid, "d2": end})
            if candidate and candidate.get("id") in observed:
                return sid, "🔴"
        if (place_ids or geometry_json) and sid not in area_prior and sid not in area_uncertain:
            first_area = []
            for pid in place_ids:
                candidate = _first({"taxon_id": sid, "place_id": pid, "d2": end})
                if candidate:
                    first_area.append(candidate)
            complete = True
            if geometry_json:
                import json
                candidate, complete = _first({"taxon_id": sid, "d2": end}, json.loads(geometry_json))
                if candidate:
                    first_area.append(candidate)
            if complete and first_area:
                earliest = min(first_area, key=lambda o: (o.get("observed_on") or "9999", o["id"]))
                if earliest["id"] in observed:
                    return sid, "🟠"
        if sid not in own_prior:
            if not place_ids and not geometry_json:
                return sid, "🟡"
            candidate = _first({"taxon_id": sid, "user_id": username, "d2": end})
            if candidate and candidate.get("id") in observed:
                return sid, "🟡"
        return sid, ""

    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(pool.map(check_one, rows))
