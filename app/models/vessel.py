from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    imo: Mapped[str | None] = mapped_column(String(7))
    vessel_type: Mapped[str | None] = mapped_column(String(50))
    flag: Mapped[str | None] = mapped_column(String(50))
    dwt: Mapped[int | None]
    gt: Mapped[int | None]
    main_engine: Mapped[str | None] = mapped_column(String(100))
    kw: Mapped[int | None]