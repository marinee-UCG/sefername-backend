from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import open_sealed
from app.core.deps import get_current_user
from app.database import get_db
from app.models.certificate import Certificate
from app.models.contract import Contract
from app.models.user import User
from app.models.vessel import Vessel
from app.schemas.imports import CertificateRow,SeaServiceRow
from app.services.certificate_import import parse_certificates
from app.services.sea_service_import import ImportFormatError, parse_sea_service


router=APIRouter(prefix="/imports",tags=["imports"])


def read_upload(file:UploadFile,parse):
    """Reads the uploaded xlsx in memory (never saved to disk) and parses it.
    Nothing is stored: the app shows the rows, the user picks, the usual endpoints save them."""
    max_bytes=settings.max_upload_size_mb*1024*1024
    content=file.file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too large"
        )
    try:
        return parse(content)
    except ImportFormatError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,detail=str(err))

@router.post("/sea-service",response_model=list[SeaServiceRow])
def preview_sea_service(
    file:UploadFile=File(...),
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    services=read_upload(file,parse_sea_service)
    contracts=db.scalars(select(Contract).where(Contract.user_id==current_user.id)).all()
    vessels=db.scalars(select(Vessel).where(Vessel.user_id==current_user.id)).all()
    rows=[]
    for service in services:
        # Already in the record: overlaps a contract (same rule as check_no_overlap, touching is fine)
        already_recorded=False
        for contract in contracts:
            if contract.start_date<service["end_date"] and (contract.end_date is None or contract.end_date>service["start_date"]):
                already_recorded=True
                break
        # A vessel the user already has: same IMO, or the same name
        vessel_id=None
        for vessel in vessels:
            same_imo=service["imo"] is not None and vessel.imo==service["imo"]
            if same_imo or vessel.name.lower()==service["vessel_name"].lower():
                vessel_id=vessel.id
                break
        rows.append({**service,"already_recorded":already_recorded,"vessel_id":vessel_id})
    return rows

@router.post("/certificates",response_model=list[CertificateRow])
def preview_certificates(
    file:UploadFile=File(...),
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    certificates=read_upload(file,parse_certificates)
    # Numbers are stored sealed: open them to see which certificates the user already has
    existing=db.scalars(select(Certificate).where(Certificate.user_id==current_user.id)).all()
    known_numbers={open_sealed(c.cert_number,c.user_id) for c in existing}
    known_pairs={(c.cert_name,c.issue_date) for c in existing}
    rows=[]
    for certificate in certificates:
        already_recorded=(
            certificate["cert_number"] in known_numbers
            or (certificate["cert_name"],certificate["issue_date"]) in known_pairs
        )
        rows.append({**certificate,"already_recorded":already_recorded})
    return rows
