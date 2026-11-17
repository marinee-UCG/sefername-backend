from pydantic import BaseModel
from datetime import date

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