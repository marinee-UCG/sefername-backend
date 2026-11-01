from pydantic import BaseModel,ConfigDict,Field
from datetime import date
from app.schemas.vessel import VesselCreate,VesselOut



class ContractCreate(BaseModel):

    company:str=Field(min_length=1,max_length=100)
    rank:str=Field(min_length=1,max_length=50)
    start_date:date
    end_date:date | None= None
    vessel_id:int |None = None
    vessel:VesselCreate | None = None

class ContractOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:int
    company:str
    rank:str
    start_date:date
    end_date:date |None = None
    vessel:VesselOut

class ContractUpdate(BaseModel):
    company:str=Field(default=None,min_length=1,max_length=100)
    rank:str=Field(default=None,min_length=1,max_length=50)
    start_date:date |None = None
    end_date:date | None= None




