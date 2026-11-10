from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.certificate import CertificateOut
from app.schemas.contract import ContractOut
from app.schemas.identity_document import IdentityDocumentOut
from app.schemas.user import UserOut
from app.schemas.voyage import VoyageOut


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=7, max_length=128)


class AccountDelete(BaseModel):
    # Asked again on purpose: an open laptop must not be enough to wipe an account
    password: str = Field(min_length=1, max_length=128)


class AccountExport(BaseModel):
    """Everything the user entered, in the shapes the app already shows them.
    Uploaded files are not inside; they can be downloaded one by one."""
    exported_at: datetime
    profile: UserOut
    contracts: list[ContractOut]
    voyages: list[VoyageOut]
    certificates: list[CertificateOut]
    identity_documents: list[IdentityDocumentOut]
