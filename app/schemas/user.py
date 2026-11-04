from datetime import datetime
from pydantic import BaseModel,ConfigDict,EmailStr,Field

class UserCreate(BaseModel):
    email:EmailStr
    password:str = Field(min_length=7,max_length=128)

class UserUpdate(BaseModel):
    full_name:str | None = Field(default=None,min_length=1,max_length=100)
    rank:str | None = Field(default=None,min_length=1,max_length=50)

class UserOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)

    id:int
    email:EmailStr
    full_name:str | None
    rank:str | None
    created_at:datetime

class Token(BaseModel):
    access_token:str
    token_type:str = "bearer"