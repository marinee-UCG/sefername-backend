from datetime import date,timedelta

from fastapi import APIRouter,Depends,HTTPException,status,UploadFile,File
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy import or_,select
from sqlalchemy.orm import Session,selectinload


from app.core.deps import get_current_user
from app.core.storage import save_upload,delete_file,FileTooLargeError,UnsupportedFileTypeError
from app.core.config import settings
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

def check_not_in_future(
        day:date | None,
        label:str
):
    if day is not None and day > date.today() + timedelta(days=1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{label} cannot be in the future"
        )
    


def check_no_overlap(db:Session,user_id:int,start:date,end:date | None,exclude_id:int | None=None) -> None:
    """One person, one ship at a time. Touching is fine: signing off one ship and
    joining the next on the same day is a normal handover."""
    query=select(Contract).where(
        Contract.user_id==user_id,
        Contract.start_date<(end or date.max),
        or_(Contract.end_date.is_(None),Contract.end_date>start),
    )
    if exclude_id is not None:
        query=query.where(Contract.id!=exclude_id)
    other=db.scalars(query.order_by(Contract.start_date)).first()
    if other is not None:
        until=other.end_date.isoformat() if other.end_date else "now"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"These dates overlap your contract on {other.vessel.name} ({other.start_date.isoformat()} to {until}). ",
        )


@router.get("",response_model=list[ContractOut])
def get_contract(current_user:User=Depends(get_current_user),db:Session=Depends(get_db)):
    query=select(Contract).where(Contract.user_id==current_user.id).options(selectinload(Contract.vessel)).order_by(Contract.start_date.desc())

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
    check_not_in_future(contract_in.start_date,"Sign-on date")
    check_not_in_future(contract_in.end_date,"Sign-off date")
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

    check_no_overlap(db,current_user.id,contract_in.start_date,contract_in.end_date)

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
    file_path=contract.service_doc_path
    db.delete(contract)
    db.commit()
    if file_path is not None:
        delete_file(file_path)

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

    # Checked only for dates that really change, so fixing the company name never trips on old data
    start_changed=new_start!=contract.start_date
    end_changed=new_end!=contract.end_date
    if start_changed:
        check_not_in_future(new_start,"Sign-on date")
    if end_changed:
        check_not_in_future(new_end,"Sign-off date")
    if start_changed or end_changed:
        check_no_overlap(db,contract.user_id,new_start,new_end,exclude_id=contract.id)

    # The contract must still hold its voyages: none before sign-on, none after sign-off
    if start_changed or end_changed:
        voyages=db.scalars(select(Voyage).where(Voyage.contract_id==contract.id)).all()
        if voyages:
            first_cosp=min(v.cosp_at for v in voyages)
            if start_changed and first_cosp.date()<new_start:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=f"Sign-on cannot be after your first voyage (COSP {first_cosp.date().isoformat()}).",
                )
            if end_changed and new_end is not None:
                if any(v.eosp_at is None for v in voyages):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A voyage is still under way. Give EOSP before signing off.",
                    )
                last_eosp=max(v.eosp_at for v in voyages)
                if last_eosp.date()>new_end:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        detail=f"Sign-off cannot be before your last voyage ended (EOSP {last_eosp.date().isoformat()}).",
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
                detail="You already have an active contract. Complete it before reopening this one. ",
            )

    for key, value in update_data.items():
        setattr(contract, key, value)
    db.commit()
    db.refresh(contract)
    return contract

@router.post("/{contract_id}/service-doc",response_model=ContractOut)
def upload_service_doc(
    file:UploadFile=File(...),
    contract:Contract=Depends(get_user_contract_or_404),
    db:Session=Depends(get_db)
):
    if contract.end_date is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your contract is still active.Sign off first"
        )
    try:
        new_path=save_upload(file,contract.user_id)
    except FileTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File is too large.Max size is {settings.max_upload_size_mb} mB"
        )
    except UnsupportedFileTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Only PDF,JPG and PNG are allowed. "
        )
    old_path=contract.service_doc_path
    contract.service_doc_path=new_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_file(new_path)
        raise
    if old_path is not None:
        delete_file(old_path)
    db.refresh(contract)
    return contract

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}

@router.get("/{contract_id}/service-doc")
def download_service_doc(
    contract:Contract=Depends(get_user_contract_or_404)
):
    if contract.service_doc_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This contract has no service doc."
        )
    path=Path(contract.service_doc_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    return FileResponse(
        path,
        media_type=MEDIA_TYPES.get(path.suffix, "application/octet-stream"),
        filename=f"Sea Service {contract.start_date}-{contract.end_date}{path.suffix}"
    )
    
@router.delete("/{contract_id}/service-doc",status_code=status.HTTP_204_NO_CONTENT)
def delete_service_doc(
    contract:Contract=Depends(get_user_contract_or_404),
    db:Session=Depends(get_db)
):
    if contract.service_doc_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This contract has no service doc"
        )
    old_path=contract.service_doc_path
    contract.service_doc_path=None
    db.commit()
    delete_file(old_path)

    



 



