from datetime import datetime,date
from pydantic import BaseModel,ConfigDict,EmailStr,Field,field_validator
from typing import Literal
from zoneinfo import available_timezones

class UserCreate(BaseModel):
    email:EmailStr
    password:str = Field(min_length=7,max_length=128)

class UserUpdate(BaseModel):
    full_name:str | None = Field(default=None,min_length=1,max_length=100)
    rank:str | None = Field(default=None,min_length=1,max_length=50)
    planned_sign_on:date | None = None
    home_timezone:str | None = Field(default=None,max_length=64)

    @field_validator("home_timezone")
    @classmethod
    def known_timezone(cls,value:str | None) -> str | None:
        # Only names from the time zone database: no free text reaches the column
        if value is not None and value not in available_timezones():
            raise ValueError("Unknown time zone.")
        return value


class OnboardingIn(BaseModel):
    full_name:str=Field(min_length=1,max_length=100)
    department:Literal ["deck","engine"]
    rank:str=Field(min_length=1,max_length=50)
    at_sea:bool
    status_since:date
    
class UserOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:int
    email:EmailStr
    full_name:str | None
    rank:str | None
    created_at:datetime
    department:str | None
    at_sea:bool | None
    status_since:date | None
    planned_sign_on:date | None
    home_timezone:str | None
    onboarded_at:datetime | None

class Token(BaseModel):
    access_token:str
    token_type:str = "bearer"