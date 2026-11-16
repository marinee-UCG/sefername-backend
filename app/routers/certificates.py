from fastapi import APIRouter,Depends,HTTPException,status,File,UploadFile
from app.core.downloads import file_download
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.crypto import seal,open_sealed
from app.core.storage import FileTooLargeError,UnsupportedFileTypeError,StorageQuotaError,save_upload,delete_file

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.certificate import Certificate
from app.schemas.certificate import CertificateCreate,CertificateOut,CertificateUpdate

router=APIRouter(prefix="/certificates",tags=["certificates"])

# Stored encrypted, bound to the owner (see core/crypto.py); name and dates stay plain for sorting and reminders
SEALED_FIELDS=("cert_number","issuing_inst")

def seal_fields(data:dict,user_id:int) -> dict:
    for field in SEALED_FIELDS:
        if field in data:
            data[field]=seal(data[field],user_id)
    return data

def certificate_out(certificate:Certificate) -> CertificateOut:
    """What the owner sees: sealed fields opened first, then checked against the schema."""
    fields={name:getattr(certificate,name) for name in CertificateOut.model_fields}
    for field in SEALED_FIELDS:
        fields[field]=open_sealed(getattr(certificate,field),certificate.user_id)
    return CertificateOut.model_validate(fields)

def get_user_certificate_or_404(
        certificate_id:int,
        current_user:User=Depends(get_current_user),
        db:Session=Depends(get_db)
):
    query=select(Certificate).where(Certificate.user_id==current_user.id,Certificate.id==certificate_id)
    selected_certificate=db.scalar(query)
    if  selected_certificate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificate not found"
        )
    return selected_certificate


@router.get("",response_model=list[CertificateOut])
def list_certificates(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    query=select(Certificate).where(Certificate.user_id==current_user.id).order_by(Certificate.expiry_date.asc().nulls_last())

    return [certificate_out(c) for c in db.scalars(query).all()]

@router.get("/{certificate_id}",response_model=CertificateOut)
def get_certificate_by_id(certificate:Certificate=Depends(get_user_certificate_or_404)):
    return certificate_out(certificate)

@router.delete("/{certificate_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate_by_id(certificate:Certificate=Depends(get_user_certificate_or_404),db:Session=Depends(get_db)):
    file_path=certificate.file_path
    db.delete(certificate)
    db.commit()
    if file_path is not None:
        delete_file(file_path)


@router.post("",response_model=CertificateOut,status_code=status.HTTP_201_CREATED)
def create_certificate(
    certificate_in:CertificateCreate,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    if (
        certificate_in.expiry_date is not None
        and certificate_in.issue_date is not None
        and certificate_in.expiry_date <= certificate_in.issue_date
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Expiry date must be after issue date"
        )
    certificate=Certificate(
        **seal_fields(certificate_in.model_dump(),current_user.id),
        user_id=current_user.id
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate_out(certificate)


@router.patch("/{certificate_id}",response_model=CertificateOut)
def update_certificate(
    certificate_in:CertificateUpdate,
    certificate:Certificate=Depends(get_user_certificate_or_404),
    db:Session=Depends(get_db)
):
    update_data=certificate_in.model_dump(exclude_unset=True)

    for field in ("cert_name","cert_number","issue_date","issuing_inst"):
        if field in update_data and update_data[field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{field} cannot be null"
            )
    new_issue=update_data.get("issue_date",certificate.issue_date)
    new_expire=update_data.get("expiry_date",certificate.expiry_date)
    if new_expire is not None and new_issue is not None and new_expire<=new_issue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Expiry date must be after issue date."
        )
    update_data=seal_fields(update_data,certificate.user_id)
    for key,value in update_data.items():
        setattr(certificate,key,value)
    db.commit()
    db.refresh(certificate)
    return certificate_out(certificate)


@router.post("/{certificate_id}/file",response_model=CertificateOut)
def upload_certificate_file(
    file:UploadFile=File(...),
    certificate:Certificate=Depends(get_user_certificate_or_404),
    db:Session=Depends(get_db)
):
    try:
        new_path=save_upload(file,certificate.user_id)
    except FileTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File is too large.Max size is {settings.max_upload_size_mb} mB"
        )
    except UnsupportedFileTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type.Only PDF,JPG and PNG are allowed"
        )
    except StorageQuotaError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Your storage is full ({settings.user_storage_limit_mb} MB). Delete a file you no longer need and try again."
        )
    old_path=certificate.file_path
    certificate.file_path=new_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_file(new_path)
        raise
    if old_path is not None:
        delete_file(old_path)
    db.refresh(certificate)
    return certificate_out(certificate)

@router.get("/{certificate_id}/file")
def download_certificate_file(
        certificate:Certificate=Depends(get_user_certificate_or_404),

):
    if certificate.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This certificate has no file.",
        )
    return file_download(certificate.file_path, f"certificate{Path(certificate.file_path).suffix}", certificate.user_id)




