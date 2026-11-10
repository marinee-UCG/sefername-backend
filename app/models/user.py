from datetime import datetime,date

from sqlalchemy import String,DateTime,func
from sqlalchemy.orm import Mapped,mapped_column

from app.database import Base

class User(Base):
    __tablename__="users"

    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(255),unique=True,index=True)
    hashed_password:Mapped[str]=mapped_column(String(255))
    full_name:Mapped[str | None]=mapped_column(String(100))
    rank:Mapped[str|None]=mapped_column(String(50))
    department:Mapped[str | None]=mapped_column(String(10))
    at_sea:Mapped[bool | None ]
    status_since:Mapped[date | None ]
    planned_sign_on:Mapped[date | None]
    onboarded_at:Mapped[datetime | None ]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),server_default=func.now()
    )
