from fastapi import APIRouter,Depends,HTTPException,status,File,Form,UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session
from pathlib import Path
from datetime import date


from app.core.crypto import seal,seal_json,open_sealed,open_json
from app.core.config import settings
from app.core.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.identity_document import IdentityDocument
from app.schemas.identity_document import IdentityDocumentCreate,IdentityDocumentOut,IdentityDocumentUpdate,DocType
from app.core.storage import FileTooLargeError,UnsupportedFileTypeError,save_upload,delete_file,StorageQuotaError,FileDecryptError,read_upload
from app.core.downloads import file_download
from app.core.rate_limit import extract_throttle
from app.core.audit import security_event
from app.services.mrz import MRZError
from app.services.mrz_ocr import extract_passport_data

router=APIRouter(prefix="/identity-documents",tags=["identity-documents"])

SEALED_FIELDS=("document_number","issuing_country")

def seal_fields(data:dict,user_id:int) -> dict:
    for field in SEALED_FIELDS:
        if field in data:
            data[field]=seal(data[field],user_id)
    return data

def document_out(document:IdentityDocument) ->IdentityDocumentOut:
    """What the owner sees: sealed fields opened first, then checked against the schema."""
    # Every field the schema has, read from the model (getattr(document, "doc_type") == document.doc_type)
    fields={name:getattr(document,name) for name in IdentityDocumentOut.model_fields}
    fields["document_number"]=open_sealed(document.document_number,document.user_id)
    fields["issuing_country"]=open_sealed(document.issuing_country,document.user_id)
    fields["extracted_data"]=open_json(document.extracted_data,document.user_id)
    return IdentityDocumentOut.model_validate(fields)

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
    query=select(IdentityDocument).where(IdentityDocument.user_id==current_user.id).order_by(IdentityDocument.doc_type,IdentityDocument.expiry_date.desc().nulls_last())
    return [document_out(d) for d in db.scalars(query).all()]

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
      **seal_fields(document_in.model_dump(),current_user.id),
      user_id=current_user.id,
      verified=True
   )
   db.add(document)
   db.commit()
   db.refresh(document)
   return document_out(document)

@router.get("/{document_id}",response_model=IdentityDocumentOut)
def get_document_by_id(document:IdentityDocument=Depends(get_user_identity_document_or_404)):
   
   return document_out(document)

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
    update_data=seal_fields(update_data,document.user_id)

    for key, value in update_data.items():
        setattr(document, key, value)

    # Data minimisation: once the user confirms, the raw MRZ read (name, birth date,
    # nationality...) has done its job; only the confirmed fields stay
    if update_data.get("verified") is True:
        document.extracted_data = None

    db.commit()
    db.refresh(document)
    return document_out(document)


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
    except StorageQuotaError:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Your storage is full ({settings.user_storage_limit_mb} MB). Delete a file you no longer need and try again."
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
    return document_out(document)


@router.get("/{document_id}/file")
def download_identity_document_file(
    document: IdentityDocument = Depends(get_user_identity_document_or_404),
):
    if document.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This document has no file.",
        )
    return file_download(document.file_path, f"{document.doc_type}{Path(document.file_path).suffix}", document.user_id)


@router.post("/{document_id}/extract",response_model=IdentityDocumentOut)
def extract_identity_document_data(
    document:IdentityDocument=Depends(get_user_identity_document_or_404),
    db:Session=Depends(get_db),
):
    # 1. Ucuz kontroller: OCR'dan (yavaş) önce
    if document.doc_type != "passport":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="MRZ extraction is only supported for passports."
        )
    if document.file_path is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="This document has no file to read. Upload a passport first."
        )
    if not Path(document.file_path).exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found."
        )
    if document.verified:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document is already verified. Set verified to false to read it again."
        )

    # Only reads that will really reach the OCR count against the hourly allowance
    key = f"extract:{document.user_id}"
    wait = extract_throttle.retry_after(key, settings.extract_per_hour)
    if wait:
        security_event("extract_limited", user_id=document.user_id, retry_after=wait)
        minutes = max(1, round(wait / 60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many passport reads. Try again in {minutes} minute{'s' if minutes > 1 else ''}, or enter the details manually.",
            headers={"Retry-After": str(wait)},
        )
    extract_throttle.record_failure(key)

    # 2. OCR: MRZ'yi oku; services'in hatasini HTTP koduna cevir
    # The file is decrypted only in memory: the plain scan never touches the disk
    try:
        content = read_upload(document.file_path, document.user_id)
    except FileDecryptError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="The file could not be opened. Please try again later.",
        )
    try:
        result = extract_passport_data(content, Path(document.file_path).suffix)
    except MRZError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Could not read the passport MRZ. Make sure the two lines at the bottom "
                   "are clearly visible, or enter the details manually."
        )

    # 3. Veri minimizasyonu: TC kimlik no (kisisel no) saklanmaz
    result.pop("personal_number", None)

    # 4. Alanlari doldur; kullanici onaylayana kadar verified=False
    document.extracted_data = seal_json(result, document.user_id)
    document.document_number = seal(result["document_number"], document.user_id)
    document.issuing_country = seal(result["issuing_country"], document.user_id)
    document.expiry_date = date.fromisoformat(result["expiry_date"]) if result["expiry_date"] else None
    document.verified = False

    db.commit()
    db.refresh(document)
    return document_out(document)
