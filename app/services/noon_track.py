"""Distances between noon positions: straight-line (great-circle) nautical miles.

Computed, not stored: editing or deleting a report changes the next one's distance, and a stored value
would go stale. A ship sails a little more than the straight line between two noons; for a daily log the
difference is small.
"""
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import NamedTuple

from app.models.noon_report import NoonReport
from app.models.voyage import Voyage
from app.services.routing import PLANNED_SPEED_KN, RouteError, progress_fraction, sea_route

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


class VoyageRoute(NamedTuple):
    """Like routing.SeaRoute (coordinates as (lon, lat), distance_nm), plus where the last noon put the ship."""
    coordinates: tuple[tuple[float, float], ...]
    distance_nm: float
    # The last noon report's time, and the miles sailed up to it; None / 0 without noon reports
    noon_at: datetime | None = None
    noon_nm: float = 0.0


def voyage_route(voyage: Voyage) -> VoyageRoute:
    """The voyage's route. Without noon reports: the planned sea route between the ports (searoute).
    With them: departure -> each noon position -> destination, each leg along the sea lanes
    (or straight when no lane is found), passing exactly through the reported positions.
    For a voyage under way the last leg, noon -> destination, is still the plan.
    Raises RouteError only when there are no noon reports and the ports have no route."""
    start = (voyage.from_port.lon, voyage.from_port.lat)
    end = (voyage.to_port.lon, voyage.to_port.lat)
    reports = list(voyage.noon_reports)
    if not reports:
        planned = sea_route(start, end)
        return VoyageRoute(planned.coordinates, planned.distance_nm)

    to_noon, noon_nm = track([start] + [(r.lon, r.lat) for r in reports])
    rest, rest_nm = track([to_noon[-1], end])
    return VoyageRoute(to_noon + rest[1:], round(noon_nm + rest_nm, 1), reports[-1].recorded_at, round(noon_nm, 1))


def track(points: list[tuple[float, float]]) -> tuple[tuple[tuple[float, float], ...], float]:
    """A line through `points` ((lon, lat)), each leg along the sea lanes, or straight when there is no lane.
    Passes exactly through every point (searoute snaps leg ends to its lanes). Returns (coordinates, nm)."""
    coordinates = [points[0]]
    distance = 0.0
    for a, b in zip(points, points[1:]):
        try:
            leg = sea_route(a, b)
            coordinates.extend(leg.coordinates)
            distance += leg.distance_nm
        except RouteError:
            distance += haversine_nm(a[1], a[0], b[1], b[0])
        coordinates.append(b)
    return tuple(coordinates), distance


def voyage_fraction(voyage: Voyage, route: VoyageRoute, now: datetime, speed_kn: float = PLANNED_SPEED_KN) -> float:
    """How far along (0 to 1) a voyage under way is. From the last noon report when there is one
    (its position is known), otherwise from COSP at the estimated speed."""
    if route.noon_at is None or route.distance_nm <= 0:
        return progress_fraction(voyage.cosp_at, route.distance_nm, now, speed_kn)
    since_noon = max(0.0, (now - route.noon_at).total_seconds() / 3600)
    return min(1.0, (route.noon_nm + speed_kn * since_noon) / route.distance_nm)


def voyage_eta(voyage: Voyage, route: VoyageRoute, speed_kn: float = PLANNED_SPEED_KN) -> datetime:
    """When the ship should arrive: from the last noon (its position and time), or from COSP."""
    if route.noon_at is None:
        return voyage.cosp_at + timedelta(hours=route.distance_nm / speed_kn)
    return route.noon_at + timedelta(hours=(route.distance_nm - route.noon_nm) / speed_kn)
