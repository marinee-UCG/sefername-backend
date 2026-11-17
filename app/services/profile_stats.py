from datetime import date,datetime,timedelta
from app.schemas.profile import Promotion
from app.schemas.profile import TypeDays,RankDays,ContractRecord,VoyageRecord,PortRecord
from app.schemas.profile import MilestoneOut,ProfileRecords,ProfileStats,ProfileTotals
from app.services.noon_track import voyage_fraction
from app.services.routing import RouteError,route_prefix
from app.services.voyage_speed import estimated_speed_kn

RANK_STEPS=[
    ("Engineer Officer",("Fourth Engineer","Third Engineer"),"Second Engineer"),
    ("Second Engineer",("Second Engineer",),"Chief Engineer"),
    ("Chief Engineer",("Chief Engineer",),None),
    ("Deck Officer",("Third Officer","Second Officer"),"Chief Officer"),
    ("Chief Officer",("Chief Officer",),"Master"),
    ("Master",("Master",),None)
]

MILESTONES = [
    # Sea time
    ("days_100", "sea_time", "100 days at sea", "sea_days", 100),
    ("days_365", "sea_time", "One year at sea", "sea_days", 365),
    ("days_1000", "sea_time", "1,000 days at sea", "sea_days", 1000),
    ("days_2000", "sea_time", "2,000 days at sea", "sea_days", 2000),
    ("days_3650", "sea_time", "Ten years at sea", "sea_days", 3650),
    # Distance
    ("nm_10k", "distance", "10,000 nm", "distance_nm", 10000),
    ("nm_world", "distance", "Once around the world", "distance_nm", 21600),
    ("nm_50k", "distance", "50,000 nm", "distance_nm", 50000),
    ("nm_100k", "distance", "100,000 nm", "distance_nm", 100000),
    # Ports and countries
    ("ports_10", "ports", "10 ports", "ports", 10),
    ("ports_25", "ports", "25 ports", "ports", 25),
    ("ports_50", "ports", "50 ports", "ports", 50),
    ("countries_10", "ports", "10 countries", "countries", 10),
    ("countries_25", "ports", "25 countries", "countries", 25),
    # Crossings
    ("cross_equator", "crossings", "Crossed the equator", "crossing:equator", 1),
    ("cross_date_line", "crossings", "Crossed the date line", "crossing:date_line", 1),
    ("cross_suez", "crossings", "Suez Canal", "crossing:suez", 1),
    ("cross_panama", "crossings", "Panama Canal", "crossing:panama", 1),
    ("cross_gibraltar", "crossings", "Strait of Gibraltar", "crossing:gibraltar", 1),
    ("cross_bosphorus", "crossings", "Bosphorus", "crossing:bosphorus", 1),
    ("cross_good_hope", "crossings", "Cape of Good Hope", "crossing:good_hope", 1),
    # Career
    ("first_contract", "career", "First contract", "contracts", 1),
    ("first_promotion", "career", "First promotion", "promotions", 1),
    ("vessels_5", "career", "Five vessels", "vessels", 5),
    ("types_3", "career", "Three vessel types", "vessel_types", 3),
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

    
def sailed_route(voyage,voyages,now:datetime,route_for):
    try:
        route=route_for(voyage)
    except RouteError:
        return None
    if voyage.eosp_at is not None:
        return route.coordinates,route.distance_nm
    ratio=voyage_fraction(voyage,route,now,estimated_speed_kn(voyage,voyages))
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
        sailed=sailed_route(voyage,voyages,now,route_for)
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
    sailed=sailed_route(longest,voyages,now,route_for)
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

def first_reached(points,target) -> date | None:
    for day,value in points:
        if value >= target:
            return day
    return None

def contract_timelines(contracts)-> dict:
    promotions=0
    highest={}
    count=0
    vessels=set()
    types=set()
    timelines = {"contracts": [], "vessels": [], "vessel_types": [],"promotions":[]}
    ordered=sorted(contracts,key=lambda c:c.start_date)
    for contract in ordered:
        count += 1
        vessels.add(contract.vessel.id)
        if contract.vessel.vessel_type is not None:
            types.add(contract.vessel.vessel_type)
        step=find_step(contract.rank)
        if step is not None:
            index=RANK_STEPS.index(step)
            department="engine" if index <3 else "deck"
            if department in highest and index > highest[department]:
                promotions+=1
            highest[department]=max(highest.get(department,index),index)
        timelines["contracts"].append((contract.start_date, count))
        timelines["vessels"].append((contract.start_date, len(vessels)))
        timelines["vessel_types"].append((contract.start_date, len(types)))
        timelines["promotions"].append((contract.start_date,promotions))
    return timelines

def voyage_timelines(voyages,today:date,now:datetime,route_for) -> dict:

    ordered=sorted(voyages,key=lambda v:v.cosp_at)
    distance=0.0
    ports=set()
    countries=set()
    timelines={"distance_nm":[],"ports":[],"countries":[]}
    for voyage in ordered:
        day=voyage.eosp_at.date() if voyage.eosp_at is not None else today
        ports.add(voyage.from_port.id)
        ports.add(voyage.to_port.id)
        countries.add(voyage.from_port.country_code)
        countries.add(voyage.to_port.country_code)
        sailed=sailed_route(voyage,voyages,now,route_for)
        if sailed is not None:
            coordinates,nm=sailed
            distance += nm
            for name in route_crossings(coordinates):
                key="crossing:" + name
                if key not in timelines:
                    timelines[key]=[(day,1)]
        timelines["distance_nm"].append((day,round(distance,1)))
        timelines["ports"].append((day,len(ports)))
        timelines["countries"].append((day,len(countries)))
    return timelines

def sea_days_reached(contracts,today:date,target:int) -> date | None:
    """The day the sea time first reached `target` days. Sea time grows every day of a
    contract, so the day can fall in the middle of one."""
    ordered=sorted(contracts,key=lambda c:c.start_date)
    before=0
    for contract in ordered:
        days=contract_days(contract,today)
        if before + days >= target:
            return contract.start_date + timedelta(days=target - before)
        before += days
    return None

def build_milestones(values:dict,timelines:dict,contracts,today:date) -> list[MilestoneOut]:
    """One MilestoneOut for every line of MILESTONES.

    values: the current value of every metric ("sea_days": 412, "crossing:suez": 1 ...)
    timelines: the (date, value) logs from contract_timelines and voyage_timelines
    """
    result=[]
    for key,category,title,metric,target in MILESTONES:
        value=values.get(metric,0)
        earned=value >= target

        if not earned:
            earned_on=None
        elif metric == "sea_days":
            earned_on=sea_days_reached(contracts,today,target)
        else:
            earned_on=first_reached(timelines.get(metric,[]),target)

        result.append(MilestoneOut(
            key=key,
            category=category,
            title=title,
            earned=earned,
            earned_on=earned_on,
            progress=min(int(value),target),
            target=target,
        ))
    return result

def build_profile_stats(user,contracts,voyages,today:date,now:datetime,route_for,required:int) -> ProfileStats:
    """Everything the profile page shows, in one answer.

    required: the sea service days needed for the next exam (settings.promotion_service_days)
    """
    # Contracts
    sea_days=sum(contract_days(c,today) for c in contracts)
    vessels={c.vessel.id for c in contracts}
    vessel_types={c.vessel.vessel_type for c in contracts if c.vessel.vessel_type is not None}
    companies={c.company.strip().lower() for c in contracts}
    first_sign_on=min((c.start_date for c in contracts),default=None)

    # How much of the time since the first sign-on was spent at sea
    sea_ratio=None
    if first_sign_on is not None:
        span=(today-first_sign_on).days
        if span > 0:
            sea_ratio=round(min(1,sea_days/span),3)

    # Voyages
    voyage_sums=voyage_totals(voyages,now,route_for)

    # Current value of every milestone metric
    values={
        "sea_days":sea_days,
        "distance_nm":voyage_sums["distance_nm"],
        "ports":voyage_sums["ports"],
        "countries":voyage_sums["countries"],
        "contracts":len(contracts),
        "vessels":len(vessels),
        "vessel_types":len(vessel_types),
    }
    timelines=contract_timelines(contracts)
    timelines.update(voyage_timelines(voyages,today,now,route_for))
    promotions=timelines["promotions"]
    values["promotions"]=promotions[-1][1] if promotions else 0
    for name in voyage_sums["crossings"]:
        values["crossing:" + name]=1

    return ProfileStats(
        full_name=user.full_name,
        rank=user.rank,
        first_sign_on=first_sign_on,
        sea_years=round(sea_days/365.25,1),
        sea_ratio=sea_ratio,
        totals=ProfileTotals(
            sea_days=sea_days,
            home_days=home_days(contracts,today),
            contracts=len(contracts),
            vessels=len(vessels),
            companies=len(companies),
            voyages=len(voyages),
            distance_nm=voyage_sums["distance_nm"],
            ports=voyage_sums["ports"],
            countries=voyage_sums["countries"],
        ),
        by_vessel_type=days_by_vessel_type(contracts,today),
        by_rank=days_by_rank(contracts,today),
        records=ProfileRecords(
            longest_contract=longest_contract(contracts,today),
            longest_voyage=longest_voyage(voyages,now,route_for),
            most_visited_port=most_visited_port(voyages),
        ),
        promotion=promotion_progress(user.rank,contracts,today,required),
        milestones=build_milestones(values,timelines,contracts,today),
    )
        


