from fastapi import APIRouter,Depends,HTTPException,status,File,Form,UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path

from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.identity_document import IdentityDocument
from app.schemas.identity_document import IdentityDocumentCreate,IdentityDocumentOut,IdentityDocumentUpdate,DocType
from app.core.storage import FileTooLargeError,UnsupportedFileTypeError,save_upload,delete_file

router=APIRouter(prefix="/identity-documents",tags=["identity-documents"])

def get_user_identity_document_or_404(
        document_id:int,
        current_user:User=Depends(get_current_user),
        db:Session=Depends(get_db)
):
    query=select(IdentityDocument).where(IdentityDocument.id==document_id,IdentityDocument.user_id==current_user.id)
    selected_document=db.scalar(query)
    if selected_document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Document not found")
    return selected_document

@router.get("",response_model=list[IdentityDocumentOut])
def get_identity_document(
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    query=select(IdentityDocument).where(IdentityDocument.user_id==current_user.id).order_by(IdentityDocument.doc_type,IdentityDocument.expiry_date.desc())
    return db.scalars(query).all()

@router.post("",response_model=IdentityDocumentOut,status_code=status.HTTP_201_CREATED)
def create_identity_documents(
    document_in:IdentityDocumentCreate,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
   if (
      document_in.issue_date is not None
      and document_in.expiry_date is not None
      and document_in.expiry_date <= document_in.issue_date
   ):
    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,detail="Expiry date must be after issue date")
   document=IdentityDocument(
      **document_in.model_dump(),
      user_id=current_user.id,
      verified=True
   )
   db.add(document)
   db.commit()
   db.refresh(document)
   return document

@router.get("/{document_id}",response_model=IdentityDocumentOut)
def get_document_by_id(document:IdentityDocument=Depends(get_user_identity_document_or_404)):
   
   return document

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_identity_document(
    document: IdentityDocument = Depends(get_user_identity_document_or_404),
    db: Session = Depends(get_db),
):
    file_path = document.file_path

    db.delete(document)
    db.commit()

    if file_path is not None:
        delete_file(file_path)
   
@router.patch("/{document_id}", response_model=IdentityDocumentOut)
def update_identity_document(
    document_in: IdentityDocumentUpdate,
    document: IdentityDocument = Depends(get_user_identity_document_or_404),
    db: Session = Depends(get_db),
):
    update_data = document_in.model_dump(exclude_unset=True)

    # verified zorunlu bir alan: null gönderilemez
    if "verified" in update_data and update_data["verified"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="verified cannot be null.",
        )

    # Tarih kontrolü: güncelleme sonrası oluşacak değerlerle
    new_issue = update_data.get("issue_date", document.issue_date)
    new_expiry = update_data.get("expiry_date", document.expiry_date)
    if new_issue is not None and new_expiry is not None and new_expiry <= new_issue:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Expiry date must be after issue date.",
        )

    for key, value in update_data.items():
        setattr(document, key, value)
    db.commit()
    db.refresh(document)
    return document


@router.post("/upload", response_model=IdentityDocumentOut, status_code=status.HTTP_201_CREATED)
def upload_identity_document(
    doc_type: DocType = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 1. Dosyayı kaydet; storage'ın hatalarını HTTP koduna çevir
    try:
        file_path = save_upload(file, current_user.id)
    except FileTooLargeError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"File is too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )
    except UnsupportedFileTypeError:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type. Only PDF, JPG and PNG are allowed.",
        )

    # 2. Kaydı oluştur: veri henüz okunmadı, onaylanmadı
    document = IdentityDocument(
        doc_type=doc_type,
        file_path=file_path,
        user_id=current_user.id,
        verified=False,
    )

    # 3. Kaydet; başarısız olursa diske yazılan dosyayı temizle
    db.add(document)
    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_file(file_path)
        raise

    db.refresh(document)
    return document


MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".png": "image/png",
}


@router.get("/{document_id}/file")
def download_identity_document_file(
    document: IdentityDocument = Depends(get_user_identity_document_or_404),
):
    if document.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This document has no file.",
        )

    path = Path(document.file_path)
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )

    return FileResponse(
        path,
        media_type=MEDIA_TYPES.get(path.suffix, "application/octet-stream"),
        filename=f"{document.doc_type}{path.suffix}",
    )


   
