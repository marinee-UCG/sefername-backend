from pydantic import BaseModel
from datetime import date,datetime
from typing import Literal

class HomewardCardOut(BaseModel):
    vessel_name:str
    rank:str
    start_date:date
    end_date:date
    days_on_board:int
    sea_days:int
    sailed_nm:int
    ports:int
    days:list[bool]
    map_svg:str | None

class EospCardOut(BaseModel):
    from_port:str
    to_port:str
    cosp_at:datetime
    eosp_at:datetime
    distance_nm:int | None
    hours:float
    speed_kn:float | None
    voyage_number:int
    contract_day:int
    days:list[Literal["this","sea","port"]]
    map_svg:str | None

class CospCardOut(BaseModel):
    port:str
    position:str
    cosp_at:datetime
    contract_day:int
    voyage_number:int
    sea_days_before:int
    map_svg:str


class SignOnCardOut(BaseModel):
    rank:str
    start_date:date
    port:str | None
    position:str | None
    contract_number:int
    rank_contract_number:int
    planned_days:int | None
    planned_end_date:date | None
    vessel_type:str | None
    map_svg:str | None
