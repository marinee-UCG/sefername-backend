"""The sea chart at the top of a share card, as SVG: coastlines, graticule, routes, ports, labels.

The Python twin of design/share-cards/make.py, so a card looks like its design. The card is 1080 x 1920;
the chart layer is the top 1080 x 1200 (the app fades its lower edge into the card).
Colours are CSS variables (var(--land), var(--acc)...) and text uses classes (t, ts, deg), so one SVG
serves both themes; the app's stylesheet sets them.

Coastlines: Natural Earth 10 m (public domain), see app/data/NOTICE.txt.
"""
import gzip
import json
import math
from functools import lru_cache
from html import escape
from pathlib import Path

W = 1080
CHART_H = 1200
LAND_FILE = Path(__file__).resolve().parent.parent / "data" / "land_10m.json.gz"


@lru_cache(maxsize=1)
def _land() -> list:
    # ~440 000 points, read once per process and kept in memory
    with gzip.open(LAND_FILE, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def _merc_y(lat: float) -> float:
    lat = max(-80.0, min(80.0, lat))
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


class Projection:
    """Mercator that fits a lon/lat box into a pixel box on the card, keeping the aspect."""

    def __init__(self, lon0: float, lon1: float, lat0: float, lat1: float, box: tuple[float, float, float, float]):
        x0, x1 = math.radians(lon0), math.radians(lon1)
        y_top, y_bottom = _merc_y(lat1), _merc_y(lat0)
        self.scale = min((box[2] - box[0]) / (x1 - x0), (box[3] - box[1]) / (y_top - y_bottom))
        self.cx, self.cy = (x0 + x1) / 2, (y_top + y_bottom) / 2
        self.ox, self.oy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2

    def __call__(self, lon: float, lat: float) -> tuple[float, float]:
        return (self.ox + (math.radians(lon) - self.cx) * self.scale, self.oy - (_merc_y(lat) - self.cy) * self.scale)

    def lon_at(self, x: float) -> float:
        return math.degrees((x - self.ox) / self.scale + self.cx)

    def lat_at(self, y: float) -> float:
        return math.degrees(2 * math.atan(math.exp(self.cy - (y - self.oy) / self.scale)) - math.pi / 2)


def text(cls: str, x: float, y: float, s: str, anchor: str = "start", halo: bool = True) -> str:
    # Port names come from data: always escaped, the SVG is put into the page as markup
    h = ' style="paint-order:stroke;stroke:var(--halo);stroke-width:7px;stroke-linejoin:round"' if halo else ""
    return f'<text class="{cls}" x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}"{h}>{escape(s)}</text>'


def land(P: Projection, step: float = 1.0) -> str:
    """Every coastline that shows in the chart area, as one path. `step` (px) drops points closer than that."""
    lon_min, lon_max = P.lon_at(-60), P.lon_at(W + 60)
    lat_min, lat_max = P.lat_at(CHART_H + 160), P.lat_at(-60)
    # A view across 180° also needs the world's copies on either side
    shifts = [s for s in (-360, 0, 360) if lon_min < 180 + s and lon_max > -180 + s]
    parts = []
    for shift in shifts:
        for ring in _land():
            if ring[2] + shift < lon_min or ring[0] + shift > lon_max or ring[3] < lat_min or ring[1] > lat_max:
                continue
            keep = []
            for i in range(4, len(ring), 2):
                x, y = P(ring[i] + shift, ring[i + 1])
                x, y = min(max(x, -60), W + 60), min(max(y, -60), CHART_H + 160)
                if not keep or abs(x - keep[-1][0]) + abs(y - keep[-1][1]) >= step:
                    keep.append((x, y))
            if len(keep) >= 3:
                parts.append("M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in keep) + "Z")
    return f'<path d="{"".join(parts)}" fill="var(--land)" stroke="var(--coast)" stroke-width="1.2" stroke-linejoin="round"/>'


def _nice_step(span: float) -> float:
    for step in (0.5, 1, 2, 5, 10, 20, 30):
        if span / step <= 7:
            return step
    return 45


def _deg(value: float, pos: str, neg: str, width: int) -> str:
    hemi = pos if value >= 0 else neg
    value = abs(value)
    if value != int(value):
        return f"{int(value):0{width}d}°{round(value % 1 * 60):02d}′{hemi}"
    return f"{int(value):0{width}d}°{hemi}"


def graticule(P: Projection) -> str:
    lon0, lon1 = P.lon_at(0), P.lon_at(W)
    lat0, lat1 = P.lat_at(CHART_H), P.lat_at(0)
    lon_step, lat_step = _nice_step(lon1 - lon0), _nice_step(lat1 - lat0)
    d, labels = [], ""
    lon = math.ceil(lon0 / lon_step) * lon_step
    while lon <= lon1:
        x = P(lon, 0)[0]
        shown = ((lon + 180) % 360) - 180
        d.append(f"M{x:.1f} 0V{CHART_H}")
        labels += text("deg", x + 8, 34, _deg(shown, "E", "W", 3), halo=False)
        lon += lon_step
    lat = math.ceil(lat0 / lat_step) * lat_step
    while lat <= lat1:
        y = P(0, lat)[1]
        d.append(f"M0 {y:.1f}H{W}")
        labels += text("deg", 22, y - 9, _deg(lat, "N", "S", 1), halo=False)
        lat += lat_step
    return f'<path d="{"".join(d)}" stroke="var(--grat)" stroke-width="1.5" fill="none"/>' + labels


def unwrap(coords) -> list[tuple[float, float]]:
    """Longitudes made continuous across 180° (a Pacific route must not jump across the whole map)."""
    out = []
    for lon, lat in coords:
        if out:
            while lon - out[-1][0] > 180:
                lon -= 360
            while lon - out[-1][0] < -180:
                lon += 360
        out.append((lon, lat))
    return out


def fit_view(points: list[tuple[float, float]], box: tuple[float, float, float, float], min_span: float = 4.0) -> Projection:
    """A projection that shows every point with some sea around it, never zoomed in past `min_span` degrees."""
    lons, lats = [p[0] for p in points], [p[1] for p in points]
    lon0, lon1, lat0, lat1 = min(lons), max(lons), min(lats), max(lats)
    pad_lon = max((lon1 - lon0) * 0.12, (min_span - (lon1 - lon0)) / 2, 0.5)
    pad_lat = max((lat1 - lat0) * 0.12, (min_span - (lat1 - lat0)) / 2, 0.5)
    P = Projection(lon0 - pad_lon, lon1 + pad_lon, max(-75, lat0 - pad_lat), min(78, lat1 + pad_lat), box)
    # Use the whole width: the box above keeps the aspect, so widen the view to the card's edges
    return Projection(P.lon_at(0), P.lon_at(W), P.lat_at(CHART_H), P.lat_at(0), (0, 0, W, CHART_H))


def route(P: Projection, coords: list[tuple[float, float]], width: float = 4.5) -> str:
    d = "M" + "L".join(f"{x:.1f} {y:.1f}" for x, y in (P(lon, lat) for lon, lat in coords))
    return (
        f'<path d="{d}" fill="none" stroke="var(--halo)" stroke-width="{width + 6.5}" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path d="{d}" fill="none" stroke="var(--acc)" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
    )


def port_marker(P: Projection, lon: float, lat: float, filled: bool = False) -> str:
    x, y = P(lon, lat)
    fill = "var(--acc)" if filled else "var(--halo)"
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{13 if filled else 10}" fill="{fill}" stroke="var(--acc)" stroke-width="5"/>'


def port_label(P: Projection, lon: float, lat: float, name: str, taken: list) -> str:
    """Upper-case name beside its port, on the side with room; skipped when it would sit on another label."""
    x, y = P(lon, lat)
    label = name.upper()
    width = 15 * len(label) + 10        # letter-spaced 23 px capitals, near enough to avoid overlaps
    right = x + 26 + width < W - 20
    lx = x + 26 if right else x - 26
    anchor = "start" if right else "end"
    for ly in (y - 18, y + 44):
        box = (lx if right else lx - width, ly - 24, (lx + width) if right else lx, ly + 6)
        if all(box[2] < t[0] or box[0] > t[2] or box[3] < t[1] or box[1] > t[3] for t in taken):
            taken.append(box)
            return text("t", lx, ly, label, anchor)
    return ""


def voyages_chart(legs: list[tuple[dict, dict, list]]) -> str:
    """Every voyage of a contract on one chart: the Homeward bound card.

    `legs`: (from_port, to_port, route coordinates) in sailing order; a port is {"name", "lon", "lat"}.
    The first departure port is drawn filled (where the contract's sailing began).
    """
    # One continuous longitude line through all legs, so a contract across the Pacific stays in one piece
    joined, prev = [], None
    for _, _, coords in legs:
        part = unwrap(([prev] if prev else []) + list(coords))
        part = part[1:] if prev else part
        joined.append(part)
        prev = part[-1] if part else prev
    points = [p for part in joined for p in part]
    P = fit_view(points, (70, 250, 1010, 1075))

    svg = graticule(P) + land(P, 1.1)
    svg += "".join(route(P, part) for part in joined if len(part) >= 2)
    # Ports at the unwrapped longitude of the route that reaches them
    seen, markers, labels, taken = set(), "", "", []
    for (start, end, _), part in zip(legs, joined):
        if not part:
            continue
        for port, (lon, lat) in ((start, part[0]), (end, part[-1])):
            if port["name"] in seen:
                continue
            first = not seen
            seen.add(port["name"])
            markers += port_marker(P, lon, lat, filled=first)
            labels += port_label(P, lon, lat, port["name"], taken)
    return svg + markers + labels


def _end_label(P: Projection, lon: float, lat: float, name: str, tag: str, taken: list) -> str:
    """Port name with COSP / EOSP under it, on the side of the port with room."""
    x, y = P(lon, lat)
    label = name.upper()
    width = max(15 * len(label), 12 * len(tag)) + 10
    right = x + 28 + width < W - 20
    lx, anchor = (x + 28, "start") if right else (x - 28, "end")
    for ly in (y - 4, y + 52, y - 60):
        box = (lx if right else lx - width, ly - 24, (lx + width) if right else lx, ly + 34)
        if all(box[2] < t[0] or box[0] > t[2] or box[3] < t[1] or box[1] > t[3] for t in taken):
            taken.append(box)
            return text("t", lx, ly, label, anchor) + text("ts", lx, ly + 28, tag, anchor)
    return ""


def voyage_chart(start: dict, end: dict, coords) -> str:
    """One finished voyage: the EOSP card. Departure as an open ring, arrival filled with a soft halo.

    `start` / `end`: {"name", "lon", "lat"}; `coords`: the sea route between them.
    Times are not drawn here: the app writes them in the user's own time zone.
    """
    line = unwrap(coords)
    P = fit_view(line, (120, 250, 960, 1075))
    (sx, sy), (ex, ey) = P(*line[0]), P(*line[-1])
    svg = graticule(P) + land(P, 1.1) + route(P, line, width=5.5)
    svg += f'<circle cx="{sx:.1f}" cy="{sy:.1f}" r="13" fill="var(--halo)" stroke="var(--acc)" stroke-width="5.5"/>'
    svg += f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="26" fill="var(--acc)" fill-opacity=".22"/>'
    svg += f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="13" fill="var(--acc)"/>'
    taken = []
    svg += _end_label(P, *line[-1], end["name"], "EOSP", taken)
    svg += _end_label(P, *line[0], start["name"], "COSP", taken)
    return svg
