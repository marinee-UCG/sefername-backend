from datetime import datetime,timezone
from fastapi import APIRouter,Depends

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db

from app.core.config import settings

from app.models.user import User
from app.models.contract import Contract
from app.models.voyage import Voyage

from app.schemas.profile import ProfileStats

from app.services.routing import sea_route
from app.services.profile_stats import build_profile_stats

router=APIRouter(prefix="/profile",tags=["profile"])




@router.get("/stats",response_model=ProfileStats)
def get_profile_stats(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    contract_query=select(Contract).where(Contract.user_id==current_user.id)
    contracts=db.scalars(contract_query).all()

    voyage_query=select(Voyage).where(Voyage.user_id==current_user.id)
    voyages=db.scalars(voyage_query).all()

    now=datetime.now(timezone.utc)

    def route_for(voyage):

        return sea_route(
            (voyage.from_port.lon,voyage.from_port.lat),
            (voyage.to_port.lon,voyage.to_port.lat),
        )
    return build_profile_stats(current_user,contracts,voyages,now.date(),now,route_for,settings.promotion_service_days)


