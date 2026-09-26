"""Validation and search for trips stored in this browser."""
from datetime import date
from uuid import uuid4
import json


def make_record(name, search, summary, trip_id=None):
    name = name.strip()
    if not name or len(name) > 120:
        raise ValueError("Geef de trip een naam van maximaal 120 tekens.")
    start, end = date.fromisoformat(search["start"]), date.fromisoformat(search["end"])
    if start > end or not search["username"].strip():
        raise ValueError("Ongeldige reisperiode of gebruikersnaam.")
    names = [*search.get("place_names", []),
             *([search.get("area_name") or "Getekend gebied"] if search.get("geometry") else [])]
    return {"id": trip_id or str(uuid4()), "name": name, "username": search["username"],
            "start_date": start.isoformat(), "end_date": end.isoformat(),
            "area_label": " of ".join(names) if names else "Wereldwijd",
            "search": search, "summary": summary}


def summary_snapshot(frame, meta, novelty, summary_counts):
    counts = summary_counts(novelty, frame["species_id"], bool(meta["places"] or meta["geometry"]))
    return {"observations": int(meta["observation_total"]),
            "unidentified": int(meta.get("unidentified_total", 0)),
            "species": len(frame), "own": counts["own"], "area": counts["area"],
            "global": counts["global"], "unresolved": counts["unresolved"]}


def matches_search(row, text):
    terms = text.casefold().split()
    haystack = " ".join(str(row.get(k) or "") for k in
                        ("name", "username", "area_label", "start_date", "end_date")).casefold()
    return all(term in haystack for term in terms)


def validate_import(raw):
    records = json.loads(raw)
    if not isinstance(records, list) or len(records) > 1000:
        raise ValueError("Het bestand bevat geen geldige lijst met trips.")
    for row in records:
        if not isinstance(row, dict) or not all(k in row for k in
               ("id", "name", "username", "start_date", "end_date", "area_label", "search", "summary")):
            raise ValueError("Het bestand bevat een ongeldige trip.")
        if not isinstance(row["id"], str) or not isinstance(row["search"], dict) or not isinstance(row["summary"], dict):
            raise ValueError("Het bestand bevat een ongeldige trip.")
        if not all(key in row["search"] for key in ("username", "start", "end", "places", "geometry")) or not all(
                key in row["summary"] for key in ("observations", "species", "unidentified", "own", "area", "global")):
            raise ValueError("Het bestand mist zoekkenmerken of samenvattingsaantallen.")
        date.fromisoformat(row["start_date"])
        date.fromisoformat(row["end_date"])
    return records
