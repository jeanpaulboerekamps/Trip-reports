"""Versioned trip summaries, including migration of browser backups from v16."""
from copy import deepcopy
from datetime import date, datetime, timezone
from uuid import uuid4
import json

SUMMARY_KEYS = ("observations", "unidentified", "species", "own", "area", "global")


def version_key(version):
    stamp = version.get("calculated_at")
    if not stamp:
        return datetime.min.replace(tzinfo=timezone.utc)
    if not isinstance(stamp, str):
        raise ValueError("Ongeldige berekendatum.")
    parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def normalize_record(row):
    """Keep an undated legacy snapshot, without inventing a calculation date."""
    row = deepcopy(row)
    if not row.get("versions"):
        row["versions"] = [{"id": "legacy-" + row["id"],
                            "calculated_at": row["search"].get("calculated_at"),
                            "search": deepcopy(row["search"]), "summary": deepcopy(row["summary"])}]
    latest = max(row["versions"], key=version_key)
    row["search"] = deepcopy(latest["search"])
    row["summary"] = deepcopy(latest["summary"])
    return row


def same_trip(search, other):
    """The automatically inferred area may change when new locations arrive."""
    return (str(search["username"]).strip().casefold() == str(other["username"]).strip().casefold()
            and all(search.get(key, default) == other.get(key, default)
                    for key, default in (("start", ""), ("end", ""),
                                         ("start_time", "00:00"), ("end_time", "23:59"))))


def make_record(name, search, summary, trip_id=None, existing=None):
    name = name.strip()
    if not name or len(name) > 120:
        raise ValueError("Geef de trip een naam van maximaal 120 tekens.")
    start, end = date.fromisoformat(search["start"]), date.fromisoformat(search["end"])
    if start > end or not search["username"].strip():
        raise ValueError("Ongeldige reisperiode of gebruikersnaam.")
    if existing and not same_trip(search, existing["search"]):
        raise ValueError("De gebruiker of reisperiode is gewijzigd. Bewaar dit als een nieuwe trip.")
    names = [*search.get("place_names", []),
             *([search.get("area_name") or "Automatisch reisgebied"] if search.get("geometry") else [])]
    # Geometry is enough for the overview map; do not store all observation locations.
    # Retain a real observation location as compact metadata for future maps.
    from trip_locations import valid_location
    location = next((valid_location(point) for point in search.get("heat_points", [])
                     if valid_location(point)), None)
    search = {**search, **({"map_location": location} if location else {})}
    search = deepcopy({k: v for k, v in search.items()
                       if k not in ("heat_points", "concentrations", "unidentified_records")})
    stamp = search.get("calculated_at")
    if not stamp:
        raise ValueError("De berekendatum ontbreekt. Bereken de trip opnieuw voordat je een versie bewaart.")
    version = {"id": stamp, "calculated_at": stamp, "search": search, "summary": deepcopy(summary)}
    version_key(version)  # Validate the timestamp before writing to browser storage.
    record = normalize_record(existing) if existing else {"id": trip_id or str(uuid4()), "versions": []}
    # Saving the same calculation twice is idempotent and never changes an old snapshot.
    if not any(v["id"] == version["id"] for v in record["versions"]):
        record["versions"].append(version)
    record["versions"].sort(key=version_key)
    record.update(name=name, username=search["username"], start_date=start.isoformat(), end_date=end.isoformat(),
                  area_label=" of ".join(names) if names else "Geen openbaar reisgebied")
    return normalize_record(record)


def merge_records(existing, incoming):
    """Import backups without removing versions that are already stored."""
    by_id = {r["id"]: normalize_record(r) for r in existing}
    for raw in incoming:
        row = normalize_record(raw)
        old = by_id.get(row["id"])
        if old:
            if not same_trip(row["search"], old["search"]):
                raise ValueError("Een trip-ID heeft verschillende gebruikers of reisperiodes.")
            versions = {v["id"]: v for v in old["versions"]}
            for version in row["versions"]:
                versions.setdefault(version["id"], version)
            row["versions"] = sorted(versions.values(), key=version_key)
        by_id[row["id"]] = normalize_record(row)
    return list(by_id.values())


def summary_snapshot(frame, meta, novelty, summary_counts):
    counts = summary_counts(novelty, frame["species_id"], bool(meta["places"] or meta["geometry"]))
    return {"observations": int(meta["observation_total"]),
            "unidentified": int(meta.get("unidentified_total", 0)),
            "species": len(frame), "own": counts["own"], "area": counts["area"],
            "global": counts["global"], "unresolved": counts["unresolved"]}


def matches_search(row, text):
    haystack = " ".join(str(row.get(k) or "") for k in
                        ("name", "username", "area_label", "start_date", "end_date")).casefold()
    return all(term in haystack for term in text.casefold().split())


def validate_import(raw):
    records = json.loads(raw)
    if not isinstance(records, list) or len(records) > 1000:
        raise ValueError("Het bestand bevat geen geldige lijst met trips.")
    seen = set()
    for row in records:
        if not isinstance(row, dict) or not all(k in row for k in
               ("id", "name", "username", "start_date", "end_date", "area_label", "search", "summary")):
            raise ValueError("Het bestand bevat een ongeldige trip.")
        if (not isinstance(row["id"], str) or not row["id"] or row["id"] in seen
                or not isinstance(row["name"], str) or not row["name"].strip() or len(row["name"]) > 120
                or not isinstance(row["username"], str) or not row["username"].strip()):
            raise ValueError("Het bestand bevat een ongeldige of dubbele trip.")
        seen.add(row["id"])
        start, end = date.fromisoformat(row["start_date"]), date.fromisoformat(row["end_date"])
        if start > end:
            raise ValueError("Ongeldige reisperiode.")
        versions = row.get("versions")
        if versions is not None and (not isinstance(versions, list) or not versions):
            raise ValueError("Ongeldige versiegeschiedenis.")
        snapshots = [{"search": row["search"], "summary": row["summary"]}, *(versions or [])]
        ids = set()
        for snapshot in snapshots:
            if not isinstance(snapshot, dict):
                raise ValueError("Ongeldige versie.")
            search, summary = snapshot.get("search"), snapshot.get("summary")
            if (not isinstance(search, dict) or not isinstance(summary, dict)
                    or not all(k in search for k in ("username", "start", "end", "places", "geometry"))
                    or not all(k in summary for k in SUMMARY_KEYS)):
                raise ValueError("Het bestand mist zoekkenmerken of samenvattingsaantallen.")
            if (not isinstance(search["username"], str)
                    or search["username"].strip().casefold() != row["username"].strip().casefold()
                    or search["start"] != row["start_date"] or search["end"] != row["end_date"]
                    or not same_trip(search, row["search"])):
                raise ValueError("Een versie hoort niet bij deze trip.")
            for key in SUMMARY_KEYS:
                value = summary[key]
                if value is None and key in ("area", "global"):
                    continue
                if type(value) is not int or value < 0:
                    raise ValueError("Ongeldige samenvattingsaantallen.")
            if "id" in snapshot:
                if not isinstance(snapshot["id"], str) or not snapshot["id"] or snapshot["id"] in ids:
                    raise ValueError("Ongeldige of dubbele versie-ID.")
                ids.add(snapshot["id"])
                version_key(snapshot)
            elif snapshot is not snapshots[0]:
                raise ValueError("Versie-ID ontbreekt.")
    return [normalize_record(row) for row in records]
