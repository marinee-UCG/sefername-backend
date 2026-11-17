from datetime import date,datetime

from sqlalchemy import DateTime,ForeignKey,String,UniqueConstraint,func
from sqlalchemy.orm import Mapped,mapped_column

from app.database import Base

class NoonReport(Base):
    __tablename__="noon_reports"

    __table_args__=(
        UniqueConstraint("voyage_id","ship_date",name="uq_noon_reports_voyage_day"),
    )
    id:Mapped[int]=mapped_column(primary_key=True)
    voyage_id:Mapped[int]=mapped_column(ForeignKey("voyages.id",ondelete="CASCADE"),index=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    recorded_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    ship_date:Mapped[date]
    lat:Mapped[float]
    lon:Mapped[float]
    note:Mapped[str | None]=mapped_column(String(280))
    wind_bft:Mapped[int | None]
    wind_dir_deg:Mapped[int | None]
    wave_m:Mapped[float | None]
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())