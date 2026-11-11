from pydantic import BaseModel
from datetime import date 

class ProfileTotals(BaseModel):
    sea_days:int
    home_days:int
    contracts:int
    vessels:int
    companies:int
    voyages:int
    distance_nm:float
    ports:int
    countries:int
class TypeDays(BaseModel):
    type:str | None
    days:int
class RankDays(BaseModel):
    rank:str
    days:int
class ContractRecord(BaseModel):
    vessel:str
    days:int
class VoyageRecord(BaseModel):
    from_port:str
    to_port:str
    days:int
    distance_nm:float | None
class PortRecord(BaseModel):
    name:str
    country_code:str
    calls:int
class ProfileRecords(BaseModel):
    longest_contract:ContractRecord | None
    longest_voyage:VoyageRecord | None
    most_visited_port:PortRecord | None
class Promotion(BaseModel):
    step:str
    days:int
    required:int
    next_rank:str | None
class MilestoneOut(BaseModel):
    key:str
    category:str
    title:str
    earned:bool
    earned_on:date | None
    progress:int
    target:int
class ProfileStats(BaseModel):
    full_name:str | None
    rank:str| None
    first_sign_on:date| None
    sea_years:float
    sea_ratio:float| None
    totals:ProfileTotals
    by_vessel_type:list[TypeDays]
    by_rank:list[RankDays]
    records:ProfileRecords
    promotion:Promotion | None
    milestones:list[MilestoneOut]