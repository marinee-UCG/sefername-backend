from pydantic import BaseModel,ConfigDict


class PortOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:int
    locode:str
    name:str
    country_code:str
    lat:float
    lon:float
    