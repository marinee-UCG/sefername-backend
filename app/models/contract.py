from datetime import date

from sqlalchemy import ForeignKey,String
from sqlalchemy.orm import Mapped,mapped_column,relationship

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from app.models.vessel import Vessel
    from app.models.port import Port


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
    sign_on_port:Mapped["Port | None"]=relationship()

    service_doc_path:Mapped[str | None]=mapped_column(String(255))
    sign_on_port_id:Mapped[int | None]=mapped_column(ForeignKey("ports.id",ondelete="RESTRICT"))
    
    @property
    def has_service_doc(self) -> bool:
        return self.service_doc_path is not None

