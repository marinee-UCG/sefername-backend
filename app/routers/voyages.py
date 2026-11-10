from fastapi import APIRouter,Depends,Query,HTTPException,status

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.port import Port
from app.models.voyage import Voyage
from app.schemas.voyage import VoyageCreate,VoyageEosp,VoyageOut,VoyageUpdate
from app.models.contract import Contract


from app.services.routing import RouteError,sea_route


router=APIRouter(prefix="/voyages",tags=["voyages"])

def get_user_voyage_or_404(
        voyage_id:int,
        db:Session=Depends(get_db),
        current_user:User=Depends(get_current_user)
):
    query=select(Voyage).where(Voyage.id==voyage_id,Voyage.user_id==current_user.id)
    selected_voyage=db.scalar(query)
    if selected_voyage is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No voyage found"
        )
    return selected_voyage
def voyage_out(voyage:Voyage)-> VoyageOut:
    out=VoyageOut.model_validate(voyage)
    try:
        route=sea_route(
            (voyage.from_port.lon,voyage.from_port.lat),
            (voyage.to_port.lon,voyage.to_port.lat),
        )
        out.distance_nm=route.distance_nm
    except RouteError:
        pass
    return out

@router.post("",response_model=VoyageOut,status_code=status.HTTP_201_CREATED)
def create_voyage(
    voyage_in:VoyageCreate,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    contract=db.scalar(
        select(Contract).where(Contract.id==voyage_in.contract_id,Contract.user_id==current_user.id)
    )
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    if voyage_in.from_port_id == voyage_in.to_port_id :
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Departure and arrival ports must be different "
        )
    from_port=db.get(Port,voyage_in.from_port_id)
    to_port=db.get(Port,voyage_in.to_port_id)
    if from_port is None or to_port is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unknown Port"
        )
    if voyage_in.cosp_at.date() < contract.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="COSP cannot be before the contract start date."
        )
    if contract.end_date is not None and voyage_in.cosp_at.date() > contract.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="COSP cannot be after the contract end date."
        )
    if voyage_in.eosp_at is not None and voyage_in.eosp_at <= voyage_in.cosp_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="EOSP must be after COSP"
        )
    if voyage_in.eosp_at is None:
        active_voyage=db.scalar(
            select(Voyage).where(Voyage.user_id==current_user.id,Voyage.eosp_at.is_(None))
        )
        if active_voyage is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
             detail="You already have an active voyage.Give EOSP first."
          )
    voyage=Voyage(
        user_id=current_user.id,
        contract_id=contract.id,
        from_port_id=voyage_in.from_port_id,
        to_port_id=voyage_in.to_port_id,
        cosp_at=voyage_in.cosp_at,
        eosp_at=voyage_in.eosp_at,
    )
    db.add(voyage)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active voyage.Give EOSP first."
        )
    db.refresh(voyage)
    return voyage_out(voyage)

@router.post("/{voyage_id}/eosp",response_model=VoyageOut)
def end_voyage(
    eosp_in:VoyageEosp,
    voyage:Voyage=Depends(get_user_voyage_or_404),
    db:Session=Depends(get_db)
):
    if voyage.eosp_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This voyage has already ended."
        )
    if eosp_in.eosp_at <= voyage.cosp_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="EOSP must be after COSP."
        )
    if voyage.contract.end_date is not None and eosp_in.eosp_at.date()>voyage.contract.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="EOSP cannot be after the contract end date."
        )

    voyage.eosp_at=eosp_in.eosp_at

    db.commit()
    db.refresh(voyage)
    return voyage_out(voyage)

@router.patch("/{voyage_id}",response_model=VoyageOut)
def update_voyage(
    voyage_in:VoyageUpdate,
    voyage:Voyage=Depends(get_user_voyage_or_404),
    db:Session=Depends(get_db)
):
    update_data=voyage_in.model_dump(exclude_unset=True)

    # Every field is required on the model; eosp_at cannot be cleared either
    # (reopening a voyage would clash with the "one active voyage" rule)
    for field in ("from_port_id","to_port_id","cosp_at","eosp_at"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null."
            )
    if "eosp_at" in update_data and voyage.eosp_at is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="This voyage is still under way. Give EOSP to end it."
        )

    # Rules checked with the values the voyage will have after the update
    new_from=update_data.get("from_port_id",voyage.from_port_id)
    new_to=update_data.get("to_port_id",voyage.to_port_id)
    new_cosp=update_data.get("cosp_at",voyage.cosp_at)
    new_eosp=update_data.get("eosp_at",voyage.eosp_at)

    if new_from==new_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Departure and arrival ports must be different."
        )
    for field in ("from_port_id","to_port_id"):
        if field in update_data and db.get(Port,update_data[field]) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Unknown port."
            )
    contract=voyage.contract
    if new_cosp.date()<contract.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="COSP cannot be before the contract start date."
        )
    if contract.end_date is not None and new_cosp.date()>contract.end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="COSP cannot be after the contract end date."
        )
    if new_eosp is not None:
        if new_eosp<=new_cosp:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="EOSP must be after COSP."
            )
        if contract.end_date is not None and new_eosp.date()>contract.end_date:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="EOSP cannot be after the contract end date."
            )

    for key,value in update_data.items():
        setattr(voyage,key,value)
    try:
        db.commit()
    except IntegrityError:
        # The database's own checks caught something the rules above missed
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="These voyage details are not valid."
        )
    db.refresh(voyage)
    return voyage_out(voyage)

@router.get("",response_model=list[VoyageOut])
def list_voyages(
    contract_id:int | None =None,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    query=select(Voyage).where(Voyage.user_id==current_user.id)
    if contract_id is not None:
        query=query.where(Voyage.contract_id==contract_id)
    query=query.order_by(Voyage.cosp_at.desc())
    voyages=db.scalars(query).all()

    return [voyage_out(v) for v in voyages]

@router.delete("/{voyage_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_voyage_by_id(
    voyage:Voyage=Depends(get_user_voyage_or_404),
    db:Session=Depends(get_db)
):
    db.delete(voyage)
    db.commit()


    


