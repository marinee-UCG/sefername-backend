from datetime import datetime

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.certificate import CertificateOut
from app.schemas.contract import ContractOut
from app.schemas.identity_document import IdentityDocumentOut
from app.schemas.user import UserOut
from app.schemas.voyage import VoyageOut


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=7, max_length=128)


class AccountDelete(BaseModel):
    # Asked again on purpose: an open laptop must not be enough to wipe an account.
    # With a password: the password. Without one (Google/Apple only): a fresh sign-in with that provider.
    password: str | None = Field(default=None, min_length=1, max_length=128)
    provider: Literal["google", "apple"] | None = None
    id_token: str | None = Field(default=None, min_length=1, max_length=8192)
    nonce: str | None = Field(default=None, min_length=16, max_length=128)


class IdentityOut(BaseModel):
    """A connected Google / Apple sign-in, as Settings lists it."""
    model_config = ConfigDict(from_attributes=True)

    provider: str
    email: str | None
    created_at: datetime


class AccountExport(BaseModel):
    """Everything the user entered, in the shapes the app already shows them.
    Uploaded files are not inside; they can be downloaded one by one."""
    exported_at: datetime
    profile: UserOut
    contracts: list[ContractOut]
    voyages: list[VoyageOut]
    certificates: list[CertificateOut]
    identity_documents: list[IdentityDocumentOut]
