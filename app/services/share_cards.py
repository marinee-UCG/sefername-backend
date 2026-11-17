from datetime import date,timedelta
from app.models.voyage import Voyage
from app.models.contract import Contract
from datetime import datetime
from app.services.noon_track import track,voyage_route,with_distances
from app.services.sea_areas import sea_area
from app.services.routing import RouteError
from app.services.chart_render import voyages_chart,voyage_chart,departure_chart,signon_chart,underway_chart

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
         r=voyage_route(v)
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
        r=voyage_route(voyage)
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


def _deg_min(value: float, pos: str, neg: str, width: int) -> str:
    """40.966 -> "40°58′N": the port's position, as a chart would write it."""
    hemi = pos if value >= 0 else neg
    value = abs(value)
    degrees, minutes = int(value), round(value % 1 * 60)
    if minutes == 60:
        degrees, minutes = degrees + 1, 0
    return f"{degrees:0{width}d}°{minutes:02d}′{hemi}"


def cosp_card(voyage: Voyage, contract_voyages: list[Voyage]) -> dict:
    """COSP: a voyage has begun. Shows the departure port only (safety rule: no route, no destination)."""
    contract = voyage.contract
    port = voyage.from_port
    cosp_day = voyage.cosp_at.date()
    ordered = sorted(contract_voyages, key=lambda v: v.cosp_at)
    # Sea days of this contract before this voyage began (its own days are still to come)
    earlier = [v for v in ordered if v.id != voyage.id and v.eosp_at is not None and v.eosp_at <= voyage.cosp_at]
    return {
        "port": port.name,
        "position": f"{_deg_min(port.lat, 'N', 'S', 2)} · {_deg_min(port.lon, 'E', 'W', 3)}",
        "cosp_at": voyage.cosp_at,
        "contract_day": (cosp_day - contract.start_date).days + 1,
        "voyage_number": [v.id for v in ordered].index(voyage.id) + 1,
        "sea_days_before": sum(sea_days_flag(contract.start_date, cosp_day, earlier)),
        "map_svg": departure_chart({"name": port.name, "lon": port.lon, "lat": port.lat}),
    }


def _same_rank(a: str, b: str) -> bool:
    # Rank is free text: "Second Engineer" and "second  engineer" are the same rank ("2nd" is not, yet)
    return " ".join(a.lower().split()) == " ".join(b.lower().split())


def signon_card(contract: Contract, user_contracts: list[Contract]) -> dict:
    """The sign-on card: rank, port, which contract this is, and the planned length.

    `user_contracts`: all of the user's contracts (this one included), to count the ones before it.
    The vessel's name is left out on purpose: the current ship stays private until sign-off.
    """
    earlier_or_this = [c for c in user_contracts if (c.start_date, c.id) <= (contract.start_date, contract.id)]
    in_rank = [c for c in earlier_or_this if _same_rank(c.rank, contract.rank)]
    # Planned length: the planned sign-off, or the real one for a contract already ended without a plan
    planned_end = contract.planned_end_date or contract.end_date
    port = contract.sign_on_port
    return {
        "rank": contract.rank,
        "start_date": contract.start_date,
        "port": port.name if port else None,
        "position": f"{_deg_min(port.lat, 'N', 'S', 2)} · {_deg_min(port.lon, 'E', 'W', 3)}" if port else None,
        "contract_number": len(earlier_or_this),
        "rank_contract_number": len(in_rank),
        "planned_days": (planned_end - contract.start_date).days if planned_end else None,
        "planned_end_date": planned_end,
        "vessel_type": contract.vessel.vessel_type,
        "map_svg": signon_chart({"name": port.name, "lon": port.lon, "lat": port.lat}) if port else None,
    }


# The under way card shows where the ship was this long ago, never where it is now
UNDERWAY_DELAY = timedelta(hours=48)


def underway_card(voyage: Voyage, now: datetime) -> dict:
    """A voyage under way, from its noon reports. The chart and the area name use only reports at least
    48 hours old (the track's end fades out there); no destination anywhere. The numbers (miles, speed,
    wind, daily distances) come from all reports: they tell how the passage goes, not where the ship is."""
    reports = list(voyage.noon_reports)
    latest = reports[-1]
    port = voyage.from_port
    start = (port.lon, port.lat)
    # Only positions old enough to show
    shown = [(r.lon, r.lat) for r in reports if r.recorded_at <= now - UNDERWAY_DELAY]
    coords, _ = track([start] + shown) if shown else ((start,), 0.0)
    where = shown[-1] if shown else start
    # Miles and speed up to the latest noon, along the sea lanes like the rest of the app
    _, sailed_nm = track([start] + [(r.lon, r.lat) for r in reports])
    hours = (latest.recorded_at - voyage.cosp_at).total_seconds() / 3600
    daily = [d["distance_nm"] for d in with_distances(voyage, reports)]
    return {
        "from_port": port.name,
        "day_at_sea": (now - voyage.cosp_at).days + 1,
        "area": sea_area(where[1], where[0]),
        "latest_noon_at": latest.recorded_at,
        "sailed_nm": round(sailed_nm),
        "speed_kn": round(sailed_nm / hours, 1) if hours > 0 else None,
        "wind_bft": latest.wind_bft,
        # The last ten days, oldest first
        "daily_nm": [round(d) for d in daily[-10:]],
        "map_svg": underway_chart({"name": port.name, "lon": port.lon, "lat": port.lat}, coords),
    }
