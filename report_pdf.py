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


def pdf_trip_name(entered_name, saved_rows, meta, saved_id=None):
    """Resolve the saved name when returning without Streamlit Session State."""
    if str(entered_name or '').strip():
        return str(entered_name).strip()
    if saved_id:
        for row in saved_rows:
            if row.get('id') == saved_id:
                return row['name']
    for row in reversed(saved_rows):
        search = row.get('search') or {}
        if (str(search.get('username','')).casefold() == str(meta.get('username','')).casefold()
                and all(search.get(key) == meta.get(key) for key in ('start','end','geometry'))
                and search.get('start_time','00:00') == meta.get('start_time','00:00')
                and search.get('end_time','23:59') == meta.get('end_time','23:59')):
            return row['name']
    return 'Tripreport'


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
    c.drawString(tx, y + 13, _fit(f"Reis: {int(row['Waarnemingen in gebied'])} · Totaal: {total_text}", width-18, size=7.5))
    url = str(row.get("iNaturalist") or "")
    if url.startswith("https://"):
        c.linkURL(url, (x, y, x + width, y + height), relative=0)


def make_trip_pdf(frame, meta, novelty):
    """Return PDF bytes for the full sorted report, including own thumbnails."""
    out = BytesIO()
    c = canvas.Canvas(out, pagesize=A4, pageCompression=1)
    title = str(meta.get('trip_name') or 'Tripreport').strip()
    c.setTitle(title)
    page_w, page_h = A4
    margin, gutter, card_h = 35, 8, 161
    card_w = (page_w - 2 * margin - 3 * gutter) / 4
    rows = list(frame.to_dict("records"))
    unclassified = meta.get('unidentified_records') or []
    with ThreadPoolExecutor(max_workers=8) as pool:
        photos = list(pool.map(_photo, [str(row.get("Foto") or "") for row in rows]))
        extra_photos = list(pool.map(_photo, [str(row.get('photo') or '') for row in unclassified]))
    extended = True
    counts = summary_counts(novelty, frame["species_id"], extended and bool(meta["places"] or meta["geometry"]))

    def page_header(page_no, with_summary=False):
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 20 if with_summary else 13)
        heading = title if with_summary else f"{title} · {meta['username']}"
        heading_size = 20 if with_summary else 13
        while heading_size > 9 and stringWidth(heading, 'Helvetica-Bold', heading_size) > page_w-2*margin:
            heading_size -= .5
        c.setFont('Helvetica-Bold', heading_size)
        c.drawString(margin, page_h - 49, _fit(heading, page_w-2*margin, 'Helvetica-Bold', heading_size))
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
                (counts["global"] if extended else "-", "Nieuw op iNaturalist" if extended else "Wereldcontrole uit"),
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
            c.drawString(margin, page_h - 235, "Ster: geel = eigen eerste · oranje = eerste in gebied · rood = eerste op iNaturalist" if extended
                         else "Ster: geel = jouw eerste. Uitgebreide gebieds- en wereldcontroles staan uit.")
            c.drawString(margin, page_h - 247, "Rode rand om geel = Research Grade tijdens de reis. Foto's komen uit de eigen waarnemingen.")
        c.setStrokeColor(BORDER)
        c.line(margin, 27, page_w - margin, 27)
        c.setFont("Helvetica", 8)
        c.setFillColor(MUTED)
        c.drawRightString(page_w - margin, 15, f"Pagina {page_no}")

    # First page: saved trip name, summary, then the map.
    page_header(1, with_summary=True)
    points = meta.get('heat_points') or []
    map_bytes, _ = heatmap_image(points, width=1200, height=1160, circles=meta.get('concentrations', []))
    if map_bytes:
        c.drawImage(ImageReader(BytesIO(map_bytes)), margin, 50,
                    width=page_w-2*margin, height=page_h-320)
    else:
        c.setFillColor(MUTED)
        c.drawString(margin, page_h-290, "Geen openbare locaties beschikbaar voor deze selectie.")
    # Species cards start on page two, four columns and four rows per full page.
    if rows:
        c.showPage()
        page_no = 2
        page_header(page_no)
        start_y = page_h - 72
        for i, row in enumerate(rows):
            if i and i % 4 == 0:
                start_y -= card_h + gutter
            if start_y - card_h < 40:
                c.showPage()
                page_no += 1
                page_header(page_no)
                start_y = page_h - 72
            col = i % 4
            x = margin + col * (card_w + gutter)
            _draw_card(c, row, novelty, photos[i], x, start_y - card_h, card_w, card_h)
    if unclassified:
        page_no = (page_no if rows else 1) + 1
        c.showPage()
        page_header(page_no)
        c.setFont('Helvetica-Bold',11)
        c.drawString(margin,page_h-68,'Nog niet op soort geïdentificeerd')
        small_gutter, small_h = 5, 82
        small_w = (page_w-2*margin-7*small_gutter)/8
        top = page_h-80
        for i, observation in enumerate(unclassified):
            if i and i%8==0:
                top -= small_h+small_gutter
            if top-small_h<40:
                c.showPage()
                page_no += 1
                page_header(page_no)
                c.setFont('Helvetica-Bold',11)
                c.drawString(margin,page_h-68,'Nog niet op soort geïdentificeerd')
                top=page_h-80
            x=margin+(i%8)*(small_w+small_gutter)
            y=top-small_h
            c.setFillColor(colors.white); c.setStrokeColor(BORDER)
            c.roundRect(x,y,small_w,small_h,4,fill=1,stroke=1)
            if extra_photos[i]:
                try:
                    c.drawImage(ImageReader(BytesIO(extra_photos[i])),x+3,y+24,small_w-6,55,preserveAspectRatio=True,anchor='c',mask='auto')
                except (ValueError,OSError):
                    pass
            c.setFillColor(INK); c.setFont('Helvetica',6)
            c.drawString(x+3,y+14,_fit(observation.get('name') or 'Onbekend',small_w-6,size=6))
            c.setFillColor(MUTED); c.setFont('Helvetica',5.5)
            c.drawString(x+3,y+5,_fit(observation.get('date') or '',small_w-6,size=5.5))
            if str(observation.get('url') or '').startswith('https://'):
                c.linkURL(observation['url'],(x,y,x+small_w,y+small_h),relative=0)
    c.save()
    return out.getvalue()
