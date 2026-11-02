
from datetime import date

from pydantic import BaseModel,ConfigDict,Field

class CertificateCreate(BaseModel):
    cert_name:str = Field(max_length=150,min_length=1)
    cert_number:str= Field(max_length=50,min_length=1)
    issue_date:date
    expiry_date:date | None=None
    issuing_inst:str =Field(max_length=100,min_length=1)

class CertificateOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:int
    cert_name:str
    cert_number:str
    issue_date:date
    expiry_date:date |None 
    issuing_inst:str

class CertificateUpdate(BaseModel):

    cert_name:str |None = Field(default=None,max_length=150,min_length=1)
    cert_number:str|None = Field(default=None,max_length=50,min_length=1)
    issue_date:date|None = None
    expiry_date:date|None = None
    issuing_inst:str|None = Field(default=None,max_length=100,min_length=1)