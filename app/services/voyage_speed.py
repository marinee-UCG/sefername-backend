from app.models.voyage import Voyage
from app.services.routing import PLANNED_SPEED_KN,RouteError,sea_route

def estimated_speed_kn(voyage:Voyage,voyages:list[Voyage]) -> float:
    total_nm=0.0
    total_time=0.0
    vessel=voyage.contract.vessel
    if vessel.service_speed_kn is not None:
        return vessel.service_speed_kn
    for past in voyages:
        if past.is_active:
            continue
        if past.contract.vessel_id != vessel.id:
            continue
        try:
            total_nm+=sea_route(
                (past.from_port.lon,past.from_port.lat),
                (past.to_port.lon,past.to_port.lat)
                ).distance_nm
        except RouteError:
            continue
        total_time+=(past.eosp_at-past.cosp_at).total_seconds()/3600
    if total_time > 0:
        return total_nm/total_time
    return PLANNED_SPEED_KN
