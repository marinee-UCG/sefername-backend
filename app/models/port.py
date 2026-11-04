from sqlalchemy import String
from sqlalchemy.orm import Mapped,mapped_column

from app.database import Base

class Port(Base):
    __tablename__="ports"

    id:Mapped[int]=mapped_column(primary_key=True)
    locode:Mapped[str]=mapped_column(String(5),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(100))
    country_code:Mapped[str]=mapped_column(String(2))
    lat:Mapped[float]
    lon:Mapped[float]