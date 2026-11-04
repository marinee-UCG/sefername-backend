from datetime import datetime,date
from pydantic import BaseModel,ConfigDict,EmailStr,Field
from typing import Literal

class UserCreate(BaseModel):
    email:EmailStr
    password:str = Field(min_length=7,max_length=128)

class UserUpdate(BaseModel):
    full_name:str | None = Field(default=None,min_length=1,max_length=100)
    rank:str | None = Field(default=None,min_length=1,max_length=50)


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
    onboarded_at:datetime | None

class Token(BaseModel):
    access_token:str
    token_type:str = "bearer"