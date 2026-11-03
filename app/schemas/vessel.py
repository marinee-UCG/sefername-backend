from pydantic import BaseModel,ConfigDict,Field

class VesselCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    imo: str | None = Field(default=None, pattern=r"^\d{7}$")
    vessel_type: str | None = Field(default=None, max_length=50)
    flag: str | None = Field(default=None, max_length=50)
    dwt: int | None = Field(default=None, ge=0)
    gt: int | None = Field(default=None, ge=0)
    main_engine: str | None = Field(default=None, max_length=100)
    kw: int | None = Field(default=None, ge=0)

class VesselOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    name:str
    imo:str | None
    vessel_type:str| None
    flag:str| None
    dwt:int| None
    gt:int| None
    main_engine:str| None
    kw:int| None


class VesselUpdate(BaseModel):
    name:str | None=Field(default=None,min_length=1,max_length=100)
    imo: str | None = Field(default=None, pattern=r"^\d{7}$")
    vessel_type: str | None = Field(default=None, max_length=50)
    flag: str | None = Field(default=None, max_length=50)
    dwt: int | None = Field(default=None, ge=0)
    gt: int | None = Field(default=None, ge=0)
    main_engine: str | None = Field(default=None, max_length=100)
    kw: int | None = Field(default=None, ge=0)