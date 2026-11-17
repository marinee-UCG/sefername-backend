"""Turn Natural Earth's land GeoJSON into the compact file the share cards draw coastlines from.

Natural Earth is public domain (naturalearthdata.com), so the data can ship with the app.
Run once from the backend folder, with the downloaded file's path:
    python -m app.scripts.build_land path/to/ne_10m_land.geojson

Writes app/data/land_10m.json.gz: a list of rings, each [min_lon, min_lat, max_lon, max_lat, lon, lat, lon, lat, ...].
Coordinates are rounded to 4 decimals (about 11 m, finer than any card shows) and repeated points dropped;
the bounding box lets a card skip every ring outside its view without looking at its points.
"""
import gzip
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "land_10m.json.gz"
DECIMALS = 4


def rings(geometry: dict):
    polygons = geometry["coordinates"] if geometry["type"] == "MultiPolygon" else [geometry["coordinates"]]
    for polygon in polygons:
        # Only the outer ring: lakes and other holes are not drawn on a sea chart card
        yield polygon[0]


def compact(ring: list) -> list | None:
    points = []
    for lon, lat, *_ in ring:
        p = (round(lon, DECIMALS), round(lat, DECIMALS))
        if not points or p != points[-1]:
            points.append(p)
    if len(points) < 4:
        return None
    lons = [p[0] for p in points]
    lats = [p[1] for p in points]
    flat = [v for p in points for v in p]
    return [min(lons), min(lats), max(lons), max(lats), *flat]


def main(source: str) -> None:
    data = json.loads(Path(source).read_text(encoding="utf-8"))
    out = [r for f in data["features"] for ring in rings(f["geometry"]) if (r := compact(ring))]
    OUT.parent.mkdir(exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(out, fh, separators=(",", ":"))
    points = sum((len(r) - 4) // 2 for r in out)
    print(f"{len(out)} rings, {points} points -> {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
