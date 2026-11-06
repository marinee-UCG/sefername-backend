from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session


from app.core.deps import get_current_user
from app.database import get_db
from app.models.contract import Contract
from app.models.user import User
from app.models.vessel import Vessel
from app.models.voyage import Voyage
from app.schemas.contract import ContractCreate,ContractOut,ContractUpdate


router=APIRouter(prefix="/contracts",tags=["contracts"])

def get_user_contract_or_404(
        contract_id:int,
        db:Session=Depends(get_db),
        current_user:User=Depends(get_current_user),
):
    query=select(Contract).where(Contract.id==contract_id,Contract.user_id==current_user.id)
    selected_contract=db.scalar(query)
    if selected_contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    return selected_contract




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
    if contract_in.planned_end_date is not None and contract_in.planned_end_date <= contract_in.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Planned end date must be after start date"
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
        planned_end_date=contract_in.planned_end_date
    )
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return contract

@router.get("/{contract_id}",response_model=ContractOut)
def get_contract_by_id(contract:Contract=Depends(get_user_contract_or_404)):
    return contract
@router.delete("/{contract_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_contract_by_id(contract:Contract=Depends(get_user_contract_or_404),db:Session=Depends(get_db)):
    has_voyages=db.scalar(
        select(Voyage.id).where(Voyage.contract_id==contract.id).limit(1)
    )
    if has_voyages is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This contract has voyages.Delete them first"
        )
    db.delete(contract)
    db.commit()

@router.patch("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_in: ContractUpdate,
    contract: Contract = Depends(get_user_contract_or_404),
    db: Session = Depends(get_db),
):
    update_data = contract_in.model_dump(exclude_unset=True)

    # Açık 1: zorunlu alanlara null gönderilmesin
    for field in ("company", "rank", "start_date"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null.",
            )

    # Tarih kontrolü: güncelleme sonrası oluşacak değerlerle
    new_start = update_data.get("start_date", contract.start_date)
    new_end = update_data.get("end_date", contract.end_date)
    if new_end is not None and new_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="End date must be after start date.",
        )
    new_planned_end=update_data.get("planned_end_date",contract.planned_end_date)
    if new_planned_end is not None and new_planned_end <= new_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Planned end date must be after start date",
        )

    # Açık 2: bitmiş kontrat yeniden açılıyorsa başka aktif kontrat olmasın
    reopening = (
        "end_date" in update_data
        and update_data["end_date"] is None
        and contract.end_date is not None
    )
    if reopening:
        other_active = db.scalar(
            select(Contract).where(
                Contract.user_id == contract.user_id,
                Contract.end_date.is_(None),
                Contract.id != contract.id,
            )
        )
        if other_active is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have an active contract. Complete it before reopening this one.",
            )

    for key, value in update_data.items():
        setattr(contract, key, value)
    db.commit()
    db.refresh(contract)
    return contract

    



 



