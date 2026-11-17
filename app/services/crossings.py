"""Where a route passes the places the profile counts as crossings, as points to mark on the chart.

The boxes are the same as profile_stats.CROSSING_BOXES (a canal, strait or cape is marked at its box's
middle); the equator and the date line are marked where the route meets them.
"""
from app.services.profile_stats import CROSSING_BOXES

NAMES = {
    "equator": "Equator",
    "date_line": "Date line",
    "suez": "Suez Canal",
    "panama": "Panama Canal",
    "gibraltar": "Strait of Gibraltar",
    "bosphorus": "Bosphorus",
    "good_hope": "Cape of Good Hope",
}


def crossing_points(coordinates) -> list[dict]:
    """[{"key", "name", "lat", "lon"}] for one route, each place once."""
    found = {}
    for lon, lat in coordinates:
        for key, (lon0, lon1, lat0, lat1) in CROSSING_BOXES.items():
            if key not in found and lon0 <= lon <= lon1 and lat0 <= lat <= lat1:
                found[key] = ((lat0 + lat1) / 2, (lon0 + lon1) / 2)
    for (lon_a, lat_a), (lon_b, lat_b) in zip(coordinates, coordinates[1:]):
        if "equator" not in found and lat_a * lat_b <= 0 and lat_a != lat_b:
            t = lat_a / (lat_a - lat_b)
            found["equator"] = (0.0, lon_a + (lon_b - lon_a) * t)
        if "date_line" not in found and abs(lon_b - lon_a) > 180:
            found["date_line"] = ((lat_a + lat_b) / 2, 180.0)
    return [{"key": k, "name": NAMES[k], "lat": round(lat, 3), "lon": round(lon, 3)} for k, (lat, lon) in found.items()]
