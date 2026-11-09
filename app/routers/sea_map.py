from datetime import datetime,timezone

from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.voyage import Voyage
from app.schemas.map import MapOut,MapTotals,MapPosition,MapVoyage
from app.schemas.port import PortOut
from app.services.routing import RouteError,SeaRoute,point_along_route,sea_route

router=APIRouter(prefix="/map",tags=["map"])
PLANNED_SPEED_KN=12

def approximate_position(voyage:Voyage,route:SeaRoute) -> MapPosition:
    expected_hours=route.distance_nm/PLANNED_SPEED_KN
    elapsed_hours=(datetime.now(timezone.utc)-voyage.cosp_at).total_seconds()/3600
    fraction=min(1,max(0,elapsed_hours/expected_hours)) if expected_hours > 0 else 0
    lon,lat=point_along_route(route.coordinates,fraction)


    return MapPosition(lat=round(lat),lon=round(lon))

@router.get("",response_model=MapOut)
def get_map(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    query=select(Voyage).where(Voyage.user_id==current_user.id).order_by(Voyage.cosp_at.desc())
    voyages=db.scalars(query).all()

    map_voyages=[]
    ports={}
    position=None
    total_nm=0.0

    for voyage in voyages:
        ports[voyage.from_port_id]=voyage.from_port
        ports[voyage.to_port_id]=voyage.to_port
        item=MapVoyage.model_validate(voyage)
        try:
            route=sea_route(
                (voyage.from_port.lon,voyage.from_port.lat),
                (voyage.to_port.lon,voyage.to_port.lat),
            )
        except RouteError:
            map_voyages.append(item)
            continue
        item.distance_nm=route.distance_nm
        item.coordinates=list(route.coordinates)
        total_nm +=route.distance_nm

        if voyage.is_active:
            position=approximate_position(voyage,route)
        map_voyages.append(item)
    return MapOut(
    voyages=map_voyages,
    ports=[PortOut.model_validate(port) for port in ports.values()],
    position=position,
    totals=MapTotals(voyages=len(voyages), distance_nm=round(total_nm, 1), ports=len(ports)),
    )


        
        
        
