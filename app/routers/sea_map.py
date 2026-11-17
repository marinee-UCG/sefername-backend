from datetime import datetime,timezone

from fastapi import APIRouter,Depends
from sqlalchemy import select
from sqlalchemy.orm import Session,selectinload

from app.core.deps import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.models.voyage import Voyage
from app.schemas.map import MapOut,MapTotals,MapPosition,MapVoyage
from app.schemas.port import PortOut
from app.services.noon_track import VoyageRoute,voyage_eta,voyage_fraction,voyage_route
from app.services.routing import RouteError,point_along_route
from app.services.voyage_speed import estimated_speed_kn

router=APIRouter(prefix="/map",tags=["map"])



def approximate_position(voyage:Voyage,route:VoyageRoute,speed_kn:float) -> MapPosition:
    # From the last noon report when there is one, otherwise from COSP at the estimated speed
    fraction=voyage_fraction(voyage,route,datetime.now(timezone.utc),speed_kn)
    lon,lat=point_along_route(route.coordinates,fraction)


    return MapPosition(
        lat=round(lat),
        lon=round(lon),
        progress=round(fraction*100),
        eta=voyage_eta(voyage,route,speed_kn),
    )


@router.get("",response_model=MapOut)
def get_map(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    query=select(Voyage).where(Voyage.user_id==current_user.id).options(selectinload(Voyage.from_port),selectinload(Voyage.to_port),selectinload(Voyage.contract).selectinload(Contract.vessel),selectinload(Voyage.noon_reports)).order_by(Voyage.cosp_at.desc())
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
            # Through the noon positions when there are any, otherwise the planned route
            route=voyage_route(voyage)
        except RouteError:
            map_voyages.append(item)
            continue
        item.distance_nm=route.distance_nm
        item.coordinates=list(route.coordinates)
        total_nm +=route.distance_nm

        if voyage.is_active:
            position=approximate_position(voyage,route,estimated_speed_kn(voyage,voyages))
        map_voyages.append(item)
    return MapOut(
    voyages=map_voyages,
    ports=[PortOut.model_validate(port) for port in ports.values()],
    position=position,
    totals=MapTotals(voyages=len(voyages), distance_nm=round(total_nm, 1), ports=len(ports)),
    )


        
        
        
