from pydantic import BaseModel
from datetime import datetime

class NewsItem(BaseModel):
    title:str
    url:str
    published_at:datetime | None
    