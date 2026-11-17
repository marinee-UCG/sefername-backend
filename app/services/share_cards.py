from datetime import date,timedelta
from app.models.voyage import Voyage
from app.models.contract import Contract
from app.services.routing import RouteError,sea_route
from app.services.chart_render import voyages_chart,voyage_chart

def sea_days_flag(start:date,end:date,voyages:list[Voyage]) -> list[bool]:
    total_days=(end-start).days
    flags=[]
    for i in range(total_days):
        day=start +timedelta(days=i)
        at_sea=any(v.cosp_at.date() <= day <= v.eosp_at.date() for v in voyages)
        flags.append(at_sea)
    return flags

def homeward_card(contract:Contract,voyages:list[Voyage]) -> dict:
    voyages=sorted(voyages,key=lambda v:v.cosp_at)
    flags=sea_days_flag(contract.start_date,contract.end_date,voyages)
    legs=[]
    sailed_nm=0.0
    ports=set()
    for v in voyages:
        ports.add(v.from_port_id)
        ports.add(v.to_port_id)
        try:
         r=sea_route(
             (v.from_port.lon,v.from_port.lat),
             (v.to_port.lon,v.to_port.lat),
         )
        except RouteError:
            continue
        sailed_nm +=r.distance_nm
        legs.append((
            {"name": v.from_port.name, "lon": v.from_port.lon, "lat": v.from_port.lat},
            {"name": v.to_port.name, "lon": v.to_port.lon, "lat": v.to_port.lat},
            r.coordinates,
        ))
    return {
        "vessel_name":contract.vessel.name,
        "rank":contract.rank,
        "start_date":contract.start_date,
        "end_date":contract.end_date,
        "days_on_board":len(flags),
        "sea_days":sum(flags),
        "sailed_nm":round(sailed_nm),
        "ports":len(ports),
        "days":flags,
        "map_svg":voyages_chart(legs) if legs else None,
    }

def eosp_card(voyage:Voyage,contract_voyages:list[Voyage]) -> dict:
    contract=voyage.contract
    try:
        r=sea_route(
            (voyage.from_port.lon,voyage.from_port.lat),
            (voyage.to_port.lon,voyage.to_port.lat),
        )
    except RouteError:
        r=None
    hours=(voyage.eosp_at-voyage.cosp_at).total_seconds()/3600
    if r is None:
        speed=None
    else:
        speed=r.distance_nm/hours
    until=voyage.eosp_at.date() + timedelta(days=1)
    any_sea=sea_days_flag(contract.start_date,until,contract_voyages)
    this_sea=sea_days_flag(contract.start_date,until,[voyage])
    days=[]
    for a,t in zip(any_sea,this_sea):
        if t:
            days.append("this")
        elif a:
            days.append("sea")
        else:
            days.append("port")
    ordered=sorted(contract_voyages,key=lambda v:v.cosp_at)
    return {
        "from_port": voyage.from_port.name,
        "to_port": voyage.to_port.name,
        "cosp_at": voyage.cosp_at,
        "eosp_at": voyage.eosp_at,
        "distance_nm": round(r.distance_nm) if r else None,
        "hours": round(hours, 1),
        "speed_kn": round(speed, 1) if speed else None,
        "voyage_number": [v.id for v in ordered].index(voyage.id) + 1,
        "contract_day": len(days),
        "days": days,
        "map_svg": voyage_chart(
            {"name": voyage.from_port.name, "lon": voyage.from_port.lon, "lat": voyage.from_port.lat},
            {"name": voyage.to_port.name, "lon": voyage.to_port.lon, "lat": voyage.to_port.lat},
            r.coordinates,
        ) if r else None,
    }