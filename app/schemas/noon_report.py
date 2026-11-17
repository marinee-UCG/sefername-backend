from datetime import date,datetime

from pydantic import AwareDatetime,BaseModel,ConfigDict,Field

class NoonReportCreate(BaseModel):
    recorded_at:AwareDatetime
    lat:float=Field(ge=-90,le=90)
    lon:float=Field(ge=-180,le=180)
    note:str | None =Field(default=None,max_length=280)

class NoonReportUpdate(BaseModel):
    recorded_at:AwareDatetime | None = None
    lat:float | None=Field(default=None,ge=-90,le=90)
    lon:float | None=Field(default=None,ge=-180,le=180)
    note:str | None=Field(default=None,max_length=280)

class NoonReportOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    voyage_id:int
    recorded_at:datetime
    ship_date:date
    lat:float
    lon:float
    note:str | None
    wind_bft:int | None
    wind_dir_deg:int | None
    wave_m:float | None
    distance_nm:float | None

