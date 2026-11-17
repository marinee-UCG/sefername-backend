from datetime import datetime,timezone
from fastapi import APIRouter,Depends

from sqlalchemy import select
from sqlalchemy.orm import Session,selectinload

from app.core.deps import get_current_user
from app.database import get_db

from app.core.config import settings

from app.models.user import User
from app.models.contract import Contract
from app.models.voyage import Voyage

from app.schemas.profile import ProfileStats

from app.services.noon_track import voyage_route
from app.services.profile_stats import build_profile_stats

router=APIRouter(prefix="/profile",tags=["profile"])




@router.get("/stats",response_model=ProfileStats)
def get_profile_stats(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    contract_query=select(Contract).where(Contract.user_id==current_user.id).options(selectinload(Contract.vessel))
    contracts=db.scalars(contract_query).all()

    voyage_query=select(Voyage).where(Voyage.user_id==current_user.id).options(selectinload(Voyage.from_port),selectinload(Voyage.to_port),selectinload(Voyage.contract).selectinload(Contract.vessel),selectinload(Voyage.noon_reports))
    voyages=db.scalars(voyage_query).all()

    now=datetime.now(timezone.utc)

    def route_for(voyage):
        # Through the noon positions when the voyage has them
        return voyage_route(voyage)
    return build_profile_stats(current_user,contracts,voyages,now.date(),now,route_for,settings.promotion_service_days)


