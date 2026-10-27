from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session


from app.core.deps import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.models.vessel import Vessel
from app.schemas.contract import ContractCreate,ContractOut,ContractUpdate


router=APIRouter(prefix="/contracts",tags=["contracts"])


@router.get("",response_model=list[ContractOut])
def get_contract(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=select(Contract).where(Contract.user_id==current_user.id).order_by(Contract.start_date.desc())

    return db.scalars(query).all()

@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
def create_contract(
    contract_in: ContractCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if contract_in.vessel is not None and contract_in.vessel_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide either vessel_id or vessel, not both.",
        )
    if contract_in.vessel is None and contract_in.vessel_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Provide vessel_id for an existing vessel or vessel details for a new one.",
        )
    if contract_in.end_date is not None and contract_in.end_date <= contract_in.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End date must be after start date.",
        )

    if contract_in.end_date is None:
        active_contract = db.scalar(
            select(Contract).where(Contract.user_id == current_user.id, Contract.end_date.is_(None))
        )
        if active_contract is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active contract. Please complete it first.",
            )

    if contract_in.vessel_id is not None:
        vessel = db.scalar(
            select(Vessel).where(Vessel.id == contract_in.vessel_id, Vessel.user_id == current_user.id)
        )
        if vessel is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vessel not found.")
    else:
        vessel = Vessel(**contract_in.vessel.model_dump(), user_id=current_user.id)
        db.add(vessel)
        db.flush()

    contract = Contract(
        company=contract_in.company,
        rank=contract_in.rank,
        start_date=contract_in.start_date,
        end_date=contract_in.end_date,
        vessel_id=vessel.id,
        user_id=current_user.id,
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract


 



