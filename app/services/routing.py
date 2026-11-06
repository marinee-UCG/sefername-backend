from functools import lru_cache
from typing import NamedTuple

import searoute as sr 


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
    
