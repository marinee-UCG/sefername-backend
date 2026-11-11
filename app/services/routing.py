from functools import lru_cache
from typing import NamedTuple
import math
from datetime import datetime,timezone

import searoute as sr 


PLANNED_SPEED_KN=12

class RouteError(Exception):
    """No sea route could be calculated between the two points."""


class SeaRoute(NamedTuple):
    coordinates:tuple[tuple[float,float], ...]
    distance_nm:float

@lru_cache(maxsize=2048)
def sea_route(origin:tuple[float,float], destination:tuple[float,float]) ->SeaRoute:
    try:
        feature=sr.searoute(list(origin),list(destination),units="naut")
    except Exception as exc:
        raise RouteError("No sea route between these points") from exc

    coordinates=tuple((lon,lat) for lon, lat in feature.geometry["coordinates"])
    return SeaRoute(coordinates=coordinates,distance_nm=round(feature.properties["length"],1))


def point_along_route(
    coordinates: tuple[tuple[float, float], ...], fraction: float
) -> tuple[float, float]:
    """(lon, lat) of the point at `fraction` (0 to 1) of the way along the route."""
    legs = list(zip(coordinates, coordinates[1:]))
    remaining = sum(math.dist(a, b) for a, b in legs) * fraction

    for a, b in legs:
        length = math.dist(a, b)
        if length>0 and remaining <=length:
            ratio=remaining/length
            return (a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio)
        else:
            remaining= remaining-length

    return coordinates[-1]

def progress_fraction(cosp_at:datetime,distance_nm:float,now:datetime) -> float:
    if distance_nm <= 0:
        return 0
    
    expected_hours=distance_nm /PLANNED_SPEED_KN
    elapsed_hours=(now-cosp_at).total_seconds()/3600
    fraction=min(1,max(0,elapsed_hours/expected_hours)) if expected_hours > 0 else 0

    return fraction

def route_prefix(
        coordinates:tuple[tuple[float,float],...],fraction:float
) -> tuple[tuple[float,float],...]:
    """The route from its start up to `fraction` (0 to 1) of the way: the part already sailed."""
    legs = list(zip(coordinates, coordinates[1:]))
    remaining = sum(math.dist(a, b) for a, b in legs) * fraction
    sailed = [coordinates[0]]

    for a, b in legs:
        length = math.dist(a, b)
        if remaining < length:
            # The cut falls inside this leg: end the route at that point
            sailed.append(point_along_route(coordinates, fraction))
            return tuple(sailed)
        sailed.append(b)
        remaining -= length

    return tuple(sailed)
    


