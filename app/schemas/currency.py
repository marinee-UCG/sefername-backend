from pydantic import BaseModel
from datetime import date
class CurrencyRate(BaseModel):
    code:str
    name:str
    buying:float

class CurrencyRateOut(BaseModel):
    date:date
    rates:list[CurrencyRate]