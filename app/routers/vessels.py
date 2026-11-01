from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.vessel import Vessel
from app.schemas.vessel import VesselOut,VesselUpdate


router=APIRouter(prefix="/vessels",tags=["vessels"])

def get_user_vessel_or_404(
        vessel_id:int,
        db:Session=Depends(get_db),
        current_user:User=Depends(get_current_user)
):
    query=select(Vessel).where(Vessel.id==vessel_id,Vessel.user_id==current_user.id)
    selected_vessel=db.scalar(query)
    
    if selected_vessel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Vessel not found")
    return selected_vessel



@router.get("",response_model=list[VesselOut])
def list_vessels(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=select(Vessel).where(Vessel.user_id==current_user.id).order_by(Vessel.name)
    return db.scalars(query).all()

@router.patch("/{vessel_id}",response_model=VesselOut)
def update_vessel(
    vessel_in:VesselUpdate,
    vessel:Vessel=Depends(get_user_vessel_or_404),
    db:Session=Depends(get_db)
):
    update_data=vessel_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,detail="Name cannot be null")
    for key,value in update_data.items():
        setattr(vessel,key,value)
    db.commit()
    db.refresh(vessel)
    return vessel