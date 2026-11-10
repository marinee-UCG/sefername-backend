from typing import Literal
from datetime import date,datetime

from pydantic import BaseModel,ConfigDict,Field

DocType=Literal["passport","seaman_book","medical"]


class IdentityDocumentCreate(BaseModel):
    doc_type:DocType
    document_number:str | None=Field(max_length=50,default=None,min_length=1)
    issuing_country:str | None=Field(max_length=50,default=None,min_length=1)
    issue_date:date | None=None
    expiry_date:date | None=None

class IdentityDocumentUpdate(BaseModel):
    verified:bool |None = None
    document_number:str | None=Field(max_length=50,default=None,min_length=1)
    issuing_country:str | None=Field(max_length=50,default=None,min_length=1)
    issue_date:date | None=None
    expiry_date:date | None=None

class IdentityDocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    doc_type: DocType
    document_number: str | None
    issuing_country: str | None
    issue_date: date | None
    expiry_date: date | None
    extracted_data: dict | None
    verified: bool
    has_file:bool
    created_at: datetime


