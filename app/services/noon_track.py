"""Distances between noon positions: straight-line (great-circle) nautical miles.

Computed, not stored: editing or deleting a report changes the next one's distance, and a stored value
would go stale. A ship sails a little more than the straight line between two noons; for a daily log the
difference is small.
"""
from math import asin, cos, radians, sin, sqrt

from app.models.noon_report import NoonReport
from app.models.voyage import Voyage

EARTH_RADIUS_NM = 3440.065


def haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_NM * asin(sqrt(a))


def with_distances(voyage: Voyage, reports: list[NoonReport]) -> list[dict]:
    """The voyage's noon reports, oldest first, each with `distance_nm` from the one before
    (the first one from the departure port). Ready for NoonReportOut."""
    out = []
    previous = (voyage.from_port.lat, voyage.from_port.lon)
    for report in sorted(reports, key=lambda r: r.recorded_at):
        out.append({
            "id": report.id,
            "voyage_id": report.voyage_id,
            "recorded_at": report.recorded_at,
            "ship_date": report.ship_date,
            "lat": report.lat,
            "lon": report.lon,
            "note": report.note,
            "wind_bft": report.wind_bft,
            "wind_dir_deg": report.wind_dir_deg,
            "wave_m": report.wave_m,
            "distance_nm": round(haversine_nm(*previous, report.lat, report.lon), 1),
        })
        previous = (report.lat, report.lon)
    return out
