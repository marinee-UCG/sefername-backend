from datetime import date
from pydantic import BaseModel


class SeaServiceRow(BaseModel):
    vessel_name:str
    imo:str | None
    flag:str | None
    service_type:str | None
    start_date:date
    end_date:date | None
    already_recorded:bool
    vessel_id:int | None


class CertificateRow(BaseModel):
    cert_name:str
    source_name:str
    cert_number:str
    issue_date:date
    expiry_date:date | None
    issuing_inst:str
    already_recorded:bool
