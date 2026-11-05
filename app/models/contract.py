from datetime import date

from sqlalchemy import ForeignKey,String
from sqlalchemy.orm import Mapped,mapped_column,relationship

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.vessel import Vessel


from app.database import Base

class Contract(Base):
    __tablename__="contracts"

    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    vessel_id:Mapped[int]=mapped_column(ForeignKey("vessels.id",ondelete="RESTRICT"),index=True)
    company:Mapped[str]=mapped_column(String(100))
    rank:Mapped[str]=mapped_column(String(50))
    start_date:Mapped[date]
    end_date:Mapped[date | None]
    planned_end_date:Mapped[date |None]
    vessel:Mapped["Vessel"]=relationship()
