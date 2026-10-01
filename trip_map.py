"""Time selection, inferred trip area and shared heatmap locations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time
from functools import lru_cache
from io import BytesIO
import math
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import numpy as np
import requests
from PIL import Image, ImageDraw
from shapely.geometry import MultiPoint, box, mapping
from shapely.ops import transform


def local_observation_time(observation):
    raw = observation.get('time_observed_at')
    if not raw:
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace('Z', '+00:00'))
        zone = observation.get('observed_time_zone') or observation.get('time_zone')
        if zone and stamp.tzinfo:
            try:
                stamp = stamp.astimezone(ZoneInfo(zone))
            except (ZoneInfoNotFoundError, ValueError):
                pass
        return stamp.replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def select_time_window(observations, start, end, start_time=time(0, 0), end_time=time(23, 59)):
    """Inclusive end minute; date-only observations require a full boundary day."""
    lower = datetime.combine(start, start_time.replace(second=0, microsecond=0))
    upper = datetime.combine(end, end_time.replace(second=59, microsecond=999999))
    if lower > upper:
        raise ValueError('Het einde moet op of na het begin liggen.')
    selected, unknown = [], 0
    for observation in observations:
        stamp = local_observation_time(observation)
        if stamp is not None:
            if lower <= stamp <= upper:
                selected.append(observation)
            continue
        try:
            day = datetime.fromisoformat(observation.get('observed_on') or '').date()
        except (ValueError, TypeError):
            unknown += 1
            continue
        if start <= day <= end:
            if (day == start and start_time != time(0, 0)) or (day == end and end_time != time(23, 59)):
                unknown += 1
            else:
                selected.append(observation)
    return selected, unknown


def observation_points(observations):
    points = []
    for observation in observations:
        coords = (observation.get('geojson') or {}).get('coordinates') or []
        if len(coords) < 2:
            continue
        try:
            lon, lat = float(coords[0]), float(coords[1])
            if math.isfinite(lon) and math.isfinite(lat) and -90 <= lat <= 90:
                points.append([lat, (lon + 180) % 360 - 180])
        except (ValueError, TypeError):
            pass
    return points


def unwrapped_points(points):
    """Find the shortest longitude interval, including trips across the date line."""
    if not points:
        return []
    longitudes = sorted(set(point[1] % 360 for point in points))
    gaps = [(longitudes[(i+1) % len(longitudes)] + (360 if i == len(longitudes)-1 else 0) - lon, i)
            for i, lon in enumerate(longitudes)]
    _, index = max(gaps)
    origin = longitudes[(index+1) % len(longitudes)]
    result = [[lat, origin + (lon-origin) % 360] for lat, lon in points]
    midpoint = (min(p[1] for p in result) + max(p[1] for p in result)) / 2
    shift = 360 * math.floor((midpoint+180)/360)
    return [[lat, lon-shift] for lat, lon in result]


def infer_trip_area(points):
    if not points:
        return None
    unwrapped = unwrapped_points(points)
    mean_lat = sum(p[0] for p in unwrapped) / len(unwrapped)
    scale_x = 111320 * max(.05, math.cos(math.radians(mean_lat)))
    hull = MultiPoint([(lon*scale_x, lat*111320) for lat, lon in unwrapped]).convex_hull.buffer(1000)
    polygon = transform(lambda x, y, z=None: (x/scale_x, y/111320), hull)
    west, _, east, _ = polygon.bounds
    pieces = []
    for band in range(math.floor((west+180)/360), math.floor((east+180)/360)+1):
        clipped = polygon.intersection(box(-180+360*band, -90, 180+360*band, 90))
        if not clipped.is_empty:
            moved = transform(lambda x, y, z=None: (x-360*band, y), clipped)
            pieces.extend([moved] if moved.geom_type == 'Polygon' else list(moved.geoms))
    if len(pieces) == 1:
        return mapping(pieces[0])
    from shapely.geometry import MultiPolygon
    return mapping(MultiPolygon(pieces))


def display_geometry(geometry, points):
    """Place date-line polygons next to the points in the displayed world copy."""
    unwrapped = unwrapped_points(points)
    centre_lon = sum(p[1] for p in unwrapped)/len(unwrapped)
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    result = [[[[lon+360*round((centre_lon-lon)/360), lat] for lon,lat in ring]
               for ring in polygon] for polygon in polygons]
    return {'type': geometry['type'], 'coordinates': result[0] if geometry['type'] == 'Polygon' else result}


def circle_ring(circle):
    """Geodesic 25 km circumference, including near poles and the date line."""
    lat, lon = math.radians(circle['lat']), math.radians(circle['lon'])
    distance = 25/6371.0088
    ring = []
    for bearing in np.linspace(0, 2*math.pi, 97):
        latitude = math.asin(math.sin(lat)*math.cos(distance)+math.cos(lat)*math.sin(distance)*math.cos(bearing))
        longitude = lon+math.atan2(math.sin(bearing)*math.sin(distance)*math.cos(lat), math.cos(distance)-math.sin(lat)*math.sin(latitude))
        ring.append([math.degrees(latitude), math.degrees(longitude)])
    return ring


def leaflet_heatmap(points, geometry=None, circles=None):
    import folium
    from html import escape
    from concentrations import circle_lines
    from folium.plugins import HeatMap
    unwrapped = unwrapped_points(points)
    centre = [sum(p[0] for p in unwrapped)/len(unwrapped), sum(p[1] for p in unwrapped)/len(unwrapped)]
    result = folium.Map(location=centre, zoom_start=13, tiles='OpenStreetMap', control_scale=True)
    HeatMap(unwrapped, radius=18, blur=15, min_opacity=.25).add_to(result)
    bounds = list(unwrapped)
    for circle in circles or []:
        lon = circle['lon']+360*round((centre[1]-circle['lon'])/360)
        location = [circle['lat'], lon]
        bounds.extend([[lat, lng+360*round((centre[1]-lng)/360)] for lat,lng in circle_ring(circle)])
        lines = '<br>'.join(escape(line) for line in circle_lines(circle))
        folium.Circle(location, radius=25000, color='#5634a5', weight=2, fill=True, fill_opacity=.04,
                      tooltip=f"Concentratie {circle['number']} · 25 km",
                      popup=escape(circle.get('countries') or 'Land onbekend')+'<br>'+lines).add_to(result)
        folium.Marker(location, icon=folium.DivIcon(icon_size=(172,96), icon_anchor=(86,48), html=
                      '<div style="background:rgba(255,255,255,.88);border:1px solid #5634a5;border-radius:12px;'
                      'padding:5px;text-align:center;font:12px/16px sans-serif;color:#251745;white-space:nowrap">'
                      +lines+'</div>')).add_to(result)
    result.fit_bounds([[min(p[0] for p in bounds), min(p[1] for p in bounds)],
                       [max(p[0] for p in bounds), max(p[1] for p in bounds)]], max_zoom=14, padding=[20,20])
    return result


@lru_cache(maxsize=96)
def _tile(zoom, x, y):
    try:
        response = requests.get(f'https://tile.openstreetmap.org/{zoom}/{x % (2**zoom)}/{y}.png',
                                headers={'User-Agent': 'Tripreport-Verkenner/2.0 (PDF map)'}, timeout=(3, 5))
        response.raise_for_status()
        return response.content
    except requests.RequestException:
        return None


def heatmap_image(points, width=1000, height=600, tile_loader=None, circles=None):
    """Return compact PNG and tile-failure count. Same observations as Leaflet."""
    unwrapped = unwrapped_points(points)
    if not unwrapped:
        return None, 0
    geometry = display_geometry(infer_trip_area(points), points)
    polygons = [geometry['coordinates']] if geometry['type'] == 'Polygon' else geometry['coordinates']
    bounds = [[lat,lon] for polygon in polygons for ring in polygon for lon,lat in ring]
    centre_lon = sum(p[1] for p in unwrapped)/len(unwrapped)
    for circle in circles or []:
        bounds.extend([[lat, lon+360*round((centre_lon-lon)/360)] for lat,lon in circle_ring(circle)])
    def project(lat, lon, zoom):
        lat = max(-85.05112878, min(85.05112878, lat))
        side = 256 * 2**zoom
        return ((lon+180)/360*side,
                (1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*side)
    zoom = 14
    while zoom > 0:
        xy = [project(lat, lon, zoom) for lat, lon in bounds]
        if max(p[0] for p in xy)-min(p[0] for p in xy) < width*.75 and max(p[1] for p in xy)-min(p[1] for p in xy) < height*.75:
            break
        zoom -= 1
    bound_xy = [project(lat, lon, zoom) for lat, lon in bounds]
    xy = [project(lat, lon, zoom) for lat, lon in unwrapped]
    left = (min(p[0] for p in bound_xy)+max(p[0] for p in bound_xy)-width)/2
    top = (min(p[1] for p in bound_xy)+max(p[1] for p in bound_xy)-height)/2
    image = Image.new('RGB', (width, height), '#edf1ed')
    tiles = [(x, y) for x in range(math.floor(left/256), math.floor((left+width)/256)+1)
             for y in range(math.floor(top/256), math.floor((top+height)/256)+1) if 0 <= y < 2**zoom]
    loader = tile_loader or _tile
    with ThreadPoolExecutor(max_workers=2) as pool:
        data = list(pool.map(lambda tile: loader(zoom, *tile), tiles))
    missing = 0
    for (x, y), content in zip(tiles, data):
        if content:
            try:
                with Image.open(BytesIO(content)) as tile:
                    image.paste(tile.convert('RGB'), (round(x*256-left), round(y*256-top)))
            except (OSError, ValueError):
                missing += 1
        else:
            missing += 1
    density = np.zeros((height, width), dtype=np.float32)
    for x, y in xy:
        px, py = round(x-left), round(y-top)
        if 0 <= px < width and 0 <= py < height:
            density[py, px] += 1
    # Float convolution avoids losing isolated points when blurring an 8-bit image.
    kernel = np.exp(-np.arange(-36,37, dtype=float)**2/(2*12**2))
    for axis in (0,1):
        density = np.apply_along_axis(lambda row: np.convolve(row, kernel, mode='same'), axis, density)
    density /= max(float(density.max()), 1e-9)
    level = np.sqrt(density)
    overlay = np.zeros((height, width, 4), dtype=np.uint8)
    overlay[:,:,0] = (np.minimum(1, level*2)*255).astype('uint8')
    overlay[:,:,1] = (np.maximum(0, 1-np.abs(level-.5)*2)*230).astype('uint8')
    overlay[:,:,2] = (np.maximum(0,1-level*2)*255).astype('uint8')
    overlay[:,:,3] = (np.minimum(.82,level)*255).astype('uint8')
    image = Image.alpha_composite(image.convert('RGBA'), Image.fromarray(overlay)).convert('RGB')
    draw = ImageDraw.Draw(image)
    from concentrations import circle_lines
    from PIL import ImageFont
    font = ImageFont.load_default(size=14)
    for circle in circles or []:
        outline = []
        for lat, lon in circle_ring(circle):
            lon += 360*round((centre_lon-lon)/360)
            px, py = project(lat, lon, zoom)
            outline.append((round(px-left), round(py-top)))
        draw.line(outline, fill='#5634a5', width=2)
        lon = circle['lon']+360*round((centre_lon-circle['lon'])/360)
        x,y = project(circle['lat'], lon, zoom)
        x,y = x-left,y-top
        lines = circle_lines(circle)
        box_width = max(draw.textlength(line, font=font) for line in lines)+12
        draw.rounded_rectangle((x-box_width/2,y-48,x+box_width/2,y+48), radius=10, fill='white', outline='#5634a5')
        for i,line in enumerate(lines):
            draw.text((x-draw.textlength(line,font=font)/2,y-43+i*18),line,fill='#251745',font=font)
    draw.rectangle((0,height-25,width,height), fill='white')
    draw.text((8,height-19), '(c) OpenStreetMap contributors | Blauw: lage dichtheid - rood: hoge dichtheid', fill='#304a39')
    if missing:
        draw.text((8,8), 'Achtergrondkaart deels niet beschikbaar', fill='#304a39')
    output = BytesIO()
    image.save(output, 'PNG', optimize=True)
    return output.getvalue(), missing
