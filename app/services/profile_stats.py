from datetime import date,datetime
from app.schemas.profile import Promotion
from app.schemas.profile import TypeDays,RankDays,ContractRecord,VoyageRecord,PortRecord
from app.services.routing import RouteError,progress_fraction,route_prefix

RANK_STEPS=[
    ("Engineer Officer",("Fourth Engineer","Third Engineer"),"Second Engineer"),
    ("Second Engineer",("Second Engineer",),"Chief Engineer"),
    ("Chief Engineer",("Chief Engineer",),None),
    ("Deck Officer",("Third Officer","Second Officer"),"Chief Officer"),
    ("Chief Officer",("Chief Officer",),"Master"),
    ("Master",("Master",),None)
]


def find_step(rank: str | None) -> tuple[str, tuple[str, ...], str | None] | None:
    if rank is None:
        return None

    wanted = rank.strip().lower()
    for step in RANK_STEPS:
        _, ranks, _ = step
        if wanted in (r.lower() for r in ranks):
            return step
    return None

def contract_days(contract,today:date) ->int:
    start_date=contract.start_date
    end_date=contract.end_date if contract.end_date is not None else today
    difference=(end_date-start_date)
    days=max(0,difference.days)
    return days

def promotion_progress(rank: str | None, contracts, today: date, required: int) -> Promotion | None:
    step=find_step(rank)
    if step is None:
        return None
    
    name,ranks,next_rank=step
    total=0

    for contract in contracts:
        if contract.rank.strip().lower() in (r.lower() for r in ranks):
            total += contract_days(contract,today)
    return Promotion(step=name,days=total,required=required,next_rank=next_rank)

CROSSING_BOXES = {
    "suez": (32.2, 32.7, 29.8, 31.4),
    "panama": (-80.1, -79.4, 8.8, 9.5),
    "gibraltar": (-6.0, -5.2, 35.7, 36.2),
    "bosphorus": (28.9, 29.2, 40.95, 41.3),
    "good_hope": (17.5, 21.5, -36.5, -34.0),
}


def route_crossings(coordinates) -> set[str]:
    """Names of the places a route passes: the equator, the date line and the CROSSING_BOXES."""
    found = set()

    # Boxes: one point inside the box is enough
    for lon, lat in coordinates:
        for name, (lon_min, lon_max, lat_min, lat_max) in CROSSING_BOXES.items():
            if lon_min <= lon <= lon_max and lat_min <= lat <= lat_max:
                found.add(name)

    # Lines: compare each point with the next one
    for (lon_a, lat_a), (lon_b, lat_b) in zip(coordinates, coordinates[1:]):
        if lat_a * lat_b <= 0:
            found.add("equator")
        if abs(lon_b - lon_a) > 180:
            found.add("date_line")

    return found

def days_by_vessel_type(contracts,today:date) -> list[TypeDays]:
    totals={}
    for contract in contracts:
        key=contract.vessel.vessel_type
        totals[key]=totals.get(key,0)+ contract_days(contract,today)
    ordered=sorted(totals.items(),key=lambda item:item[1],reverse=True)

    result=[]
    for vessel_type,days in ordered:
        result.append(TypeDays(type=vessel_type,days=days))
    return result

def days_by_rank(contracts,today:date) -> list[RankDays]:
    totals={}
    for contract in contracts:
        key=contract.rank.strip()
        totals[key]=totals.get(key,0) + contract_days(contract,today)
    ordered=sorted(totals.items(),key=lambda item:item[1],reverse=True)

    result=[]
    for rank,days in ordered:
        result.append(RankDays(rank=rank,days=days))
    return result

def home_days(contracts,today:date) ->int:
    if not contracts:
        return 0
    ordered=sorted(contracts,key=lambda c:c.start_date)

    total=0
    # Gaps between one sign-off and the next sign-on
    for previous,following in zip(ordered,ordered[1:]):
        total += max(0,(following.start_date-previous.end_date).days)

    # At home now: count from the last sign-off until today
    last=ordered[-1]
    if last.end_date is not None:
        total += max(0,(today-last.end_date).days)

    return total

    
def sailed_route(voyage,now:datetime,route_for):
    try:
        route=route_for(voyage)
    except RouteError:
        return None
    if voyage.eosp_at is not None:
        return route.coordinates,route.distance_nm
    ratio=progress_fraction(voyage.cosp_at,route.distance_nm,now)
    prefix=route_prefix(route.coordinates,ratio)
    sailed=route.distance_nm * ratio

    return (prefix,sailed)

def voyage_totals(voyages,now:datetime,route_for)-> dict:

    distance=0.0
    ports=set()
    countries=set()
    crossings=set()
    for voyage in voyages:
        ports.add(voyage.from_port.id)
        ports.add(voyage.to_port.id)
        countries.add(voyage.from_port.country_code)
        countries.add(voyage.to_port.country_code)
        sailed=sailed_route(voyage,now,route_for)
        if sailed is None:
            continue
        coordinates,nm=sailed
        distance += nm
        crossings.update(route_crossings(coordinates))
    return {
        "distance_nm":round(distance,1),
        "ports":len(ports),
        "countries":len(countries),
        "crossings":crossings
    }

def longest_contract(contracts,today:date) -> ContractRecord | None:
    if not contracts:
        return None
    
    longest=max(contracts,key=lambda c:contract_days(c,today))

    return ContractRecord(vessel=longest.vessel.name,days=contract_days(longest,today))

def voyage_days(voyage,now:datetime) -> int:
    start_date=voyage.cosp_at
    end_date=voyage.eosp_at if voyage.eosp_at is not None else now
    total_days=(end_date-start_date).days
    return total_days

def longest_voyage(voyages,now:datetime,route_for) -> VoyageRecord | None:
    if not voyages:
        return None
    longest=max(voyages,key=lambda v:voyage_days(v,now))
    sailed=sailed_route(longest,now,route_for)
    if sailed is None:
        distance=None
    else:
        coordinates,nm=sailed
        distance=round(nm,1)
    return VoyageRecord(from_port=longest.from_port.name,to_port=longest.to_port.name,days=voyage_days(longest,now),distance_nm=distance)

def most_visited_port(voyages) -> PortRecord | None:
    calls={}
    ports={}
    if not voyages:
        return None
    ordered=sorted(voyages,key=lambda v:v.cosp_at)
    for voyage in ordered:
        port=voyage.to_port
        calls[port.id]=calls.get(port.id,0)+1
        ports[port.id]=port
    best_id=max(calls,key=lambda port_id:calls[port_id])
    best=ports[best_id]
    return PortRecord(name=best.name,country_code=best.country_code,calls=calls[best_id])
    
