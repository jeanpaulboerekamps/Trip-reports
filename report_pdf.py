"""Printable trip report with the observer's photos and complete species list."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import math

import requests
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from trip_data import summary_counts
from trip_map import heatmap_image

INK = colors.HexColor("#173d2e")
MUTED = colors.HexColor("#607468")
PALE = colors.HexColor("#edf5ef")
BORDER = colors.HexColor("#d2dfd5")


def _photo(url):
    if not url:
        return None
    # iNaturalist's small derivative is sufficient for a printable thumbnail.
    thumb = url.replace("medium.", "small.")
    try:
        response = requests.get(thumb, timeout=(5, 12), headers={"User-Agent": "Tripreport-Verkenner/1.0"})
        response.raise_for_status()
        if len(response.content) > 3_000_000:
            return None
        return response.content
    except requests.RequestException:
        return None


def _fit(text, width, font="Helvetica", size=9):
    text = str(text or "")
    while text and stringWidth(text, font, size) > width:
        text = text[:-1]
    return text if not text or stringWidth(text, font, size) <= width else text + "…"


def _draw_star(c, cx, cy, fill, outline=None):
    outer, inner = 9, 4
    points = []
    for i in range(10):
        radius = outer if i % 2 == 0 else inner
        angle = math.pi / 2 + i * math.pi / 5
        points.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    path = c.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    path.close()
    c.setFillColor(fill)
    c.setStrokeColor(outline or fill)
    c.setLineWidth(1.8 if outline else 0.6)
    c.drawPath(path, fill=1, stroke=1)


def _draw_card(c, row, novelty, photo_bytes, x, y, width, height):
    c.setFillColor(colors.white)
    c.setStrokeColor(BORDER)
    c.roundRect(x, y, width, height, 8, fill=1, stroke=1)
    image_h = 98
    c.setFillColor(PALE)
    c.roundRect(x + 5, y + height - image_h - 5, width - 10, image_h, 5, fill=1, stroke=0)
    if photo_bytes:
        try:
            image = ImageReader(BytesIO(photo_bytes))
            iw, ih = image.getSize()
            box_w, box_h = width - 10, image_h
            scale = min(box_w / iw, box_h / ih)
            draw_w, draw_h = iw * scale, ih * scale
            c.drawImage(image, x + (width - draw_w) / 2,
                        y + height - 5 - (box_h + draw_h) / 2,
                        draw_w, draw_h, mask="auto")
        except Exception:
            pass
    record = novelty.get(int(row["species_id"])) or {}
    star_colors = (("own", colors.HexColor("#f0c824")),
                   ("area", colors.HexColor("#ef8a24")),
                   ("global", colors.HexColor("#df3f39")))
    active = [(flag, color) for flag, color in star_colors if record.get(flag)]
    for i, (flag, color) in enumerate(active):
        _draw_star(c, x + width - 17 - (len(active) - 1 - i) * 21,
                   y + height - 17, color,
                   colors.HexColor("#d22e32") if flag == "own" and row.get("Trip RG") else None)
    tx = x + 9
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(tx, y + 43, _fit(row.get("Engelse naam") or row.get("Wetenschappelijke naam"), width - 18,
                                  "Helvetica-Bold", 9))
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(MUTED)
    c.drawString(tx, y + 29, _fit(row.get("Wetenschappelijke naam"), width - 18,
                                  "Helvetica-Oblique", 8))
    total = row.get("Mijn waarnemingen wereldwijd")
    total_text = str(int(total)) if total is not None and str(total) not in ("<NA>", "nan") else "?"
    c.setFont("Helvetica", 7.5)
    c.drawString(tx, y + 13, f"Reis: {int(row['Waarnemingen in gebied'])}   Mijn totaal: {total_text}")
    url = str(row.get("iNaturalist") or "")
    if url.startswith("https://"):
        c.linkURL(url, (x, y, x + width, y + height), relative=0)


def make_trip_pdf(frame, meta, novelty):
    """Return PDF bytes for the full sorted report, including own thumbnails."""
    out = BytesIO()
    c = canvas.Canvas(out, pagesize=A4, pageCompression=1)
    c.setTitle(f"Tripreport {meta['username']} {meta['start']} - {meta['end']}")
    page_w, page_h = A4
    margin, gutter, card_h = 35, 8, 161
    card_w = (page_w - 2 * margin - 2 * gutter) / 3
    rows = list(frame.to_dict("records"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        photos = list(pool.map(_photo, [str(row.get("Foto") or "") for row in rows]))
    counts = summary_counts(novelty, frame["species_id"], bool(meta["places"] or meta["geometry"]))

    def page_header(page_no, with_summary=False):
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 20 if with_summary else 13)
        c.drawString(margin, page_h - 49, "Tripreport" if with_summary else f"Tripreport · {meta['username']}")
        if with_summary:
            c.setFont("Helvetica", 10)
            c.setFillColor(MUTED)
            c.drawString(margin, page_h - 67, f"{meta['username']} · {meta['start']} {meta.get('start_time', '00:00')} t/m {meta['end']} {meta.get('end_time', '23:59')}")
            area = [*meta.get("place_names", ()), *([meta.get("area_name") or "Getekend gebied"] if meta.get("geometry") else [])]
            c.setFont("Helvetica", 8)
            c.drawString(margin, page_h - 80, _fit("Gebied: " + (" of ".join(area) if area else "wereldwijd"),
                                                   page_w - 2 * margin, "Helvetica", 8))
            values = [
                (meta.get("observation_total", sum(int(r["Waarnemingen in gebied"]) for r in rows)), "Waarnemingen"),
                (meta.get("unidentified_total", 0), "Nog niet op soort"),
                (len(rows), "Soorten"),
                (counts["own"], "Nieuw voor mij"),
                (counts["area"] if counts["area"] is not None else "-", "Nieuw in gebied"),
                (counts["global"], "Nieuw op iNaturalist"),
            ]
            box_w = (page_w - 2 * margin - 10) / 3
            for i, (value, label) in enumerate(values):
                col, row_idx = i % 3, i // 3
                x, y = margin + col * (box_w + 5), page_h - 142 - row_idx * 48
                c.setFillColor(PALE)
                c.roundRect(x, y, box_w, 43, 6, fill=1, stroke=0)
                c.setFillColor(INK)
                c.setFont("Helvetica-Bold", 15)
                c.drawString(x + 9, y + 21, str(value))
                c.setFont("Helvetica", 8)
                c.drawString(x + 9, y + 8, label)
            c.setFillColor(MUTED)
            c.setFont("Helvetica", 8)
            c.drawString(margin, page_h - 235, "Ster: geel = eigen eerste · oranje = eerste in gebied · rood = eerste op iNaturalist")
            c.drawString(margin, page_h - 247, "Rode rand om geel = Research Grade tijdens de reis. Foto's komen uit de eigen waarnemingen.")
        c.setStrokeColor(BORDER)
        c.line(margin, 27, page_w - margin, 27)
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawRightString(page_w - margin, 15, f"Pagina {page_no}")

    # The map is the first output page, ahead of summary and species photos.
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(margin, page_h - 49, "Waar de waarnemingen waren")
    c.setFont("Helvetica", 10)
    c.setFillColor(MUTED)
    c.drawString(margin, page_h - 69, _fit(f"{meta['username']} · {meta['start']} {meta.get('start_time', '00:00')} t/m {meta['end']} {meta.get('end_time', '23:59')}", page_w-2*margin, size=10))
    points = meta.get('heat_points') or []
    map_bytes, missing_tiles = heatmap_image(points, circles=meta.get('concentrations', []))
    if map_bytes:
        c.drawImage(ImageReader(BytesIO(map_bytes)), margin, page_h-410,
                    width=page_w-2*margin, height=(page_w-2*margin)*.6)
    else:
        c.drawString(margin, page_h-120, "Geen openbare locaties beschikbaar voor deze selectie.")
    notes = [f"{len(points):,} waarnemingen met openbare locatie. Kleuren tonen relatieve dichtheid.",
             f"{meta.get('missing_location_total', 0):,} waarnemingen zonder openbare locatie tellen wel mee in het rapport.",
             "Cirkels: straal 25 km, minimaal 26 waarnemingen. Overlap kan dezelfde waarnemingen bevatten.",
             "Nieuw: eerste gedateerde waarneming in de cirkel voor jouw account, het land of iNaturalist.",
             "Bij meerdere landen telt een nieuwe soort eenmaal. >= ... (?) betekent: controle onvolledig.",
             "Tijden zijn de lokale waarnemingstijden; de gekozen eindminuut telt volledig mee."]
    if meta.get('unknown_time_total'):
        notes.append(f"{meta['unknown_time_total']:,} waarnemingen zonder tijdstip op een gedeeltelijke dag niet meegenomen.")
    if missing_tiles:
        notes.append("De achtergrondkaart kon niet volledig worden opgehaald; de heatmap is wel compleet.")
    c.setFont('Helvetica', 8)
    for i, note in enumerate(notes):
        c.drawString(margin, page_h-435-i*15, _fit(note, page_w-2*margin, size=8))
    c.drawRightString(page_w-margin, 15, 'Pagina 1')
    c.showPage()
    page_no = 2
    page_header(page_no, with_summary=True)
    start_y = page_h - 270
    for i, row in enumerate(rows):
        if i and i % 3 == 0:
            start_y -= card_h + gutter
        if start_y - card_h < 40:
            c.showPage()
            page_no += 1
            page_header(page_no)
            start_y = page_h - 72
        col = i % 3
        x = margin + col * (card_w + gutter)
        _draw_card(c, row, novelty, photos[i], x, start_y - card_h, card_w, card_h)
    c.save()
    return out.getvalue()
