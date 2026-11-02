from fastapi import APIRouter,Depends,HTTPException,status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.certificate import Certificate
from app.schemas.certificate import CertificateCreate,CertificateOut,CertificateUpdate

router=APIRouter(prefix="/certificates",tags=["certificates"])

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

    return db.scalars(query).all()

@router.get("/{certificate_id}",response_model=CertificateOut)
def get_certificate_by_id(certificate:Certificate=Depends(get_user_certificate_or_404)):
    return certificate

@router.delete("/{certificate_id}",status_code=status.HTTP_204_NO_CONTENT)
def delete_certificate_by_id(certificate:Certificate=Depends(get_user_certificate_or_404),db:Session=Depends(get_db)):
    db.delete(certificate)
    db.commit()


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
        **certificate_in.model_dump(),
        user_id=current_user.id
    )
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    return certificate


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
    for key,value in update_data.items():
        setattr(certificate,key,value)
    db.commit()
    db.refresh(certificate)
    return certificate






