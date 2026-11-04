from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint,DateTime,ForeignKey,Index,func,text
from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.contract import Contract
    from app.models.port import Port

class Voyage(Base):
    __tablename__="voyages"
    # Safety net in the database itself: the router checks these too (for clear
    # error messages), but two requests arriving at once can slip past a router check.
    __table_args__=(
        CheckConstraint("from_port_id <> to_port_id",name="ck_voyages_different_ports"),
        CheckConstraint("eosp_at IS NULL OR eosp_at > cosp_at",name="ck_voyages_eosp_after_cosp"),
        # Partial unique index: at most one active voyage (no EOSP yet) per user
        Index(
            "uq_voyages_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("eosp_at IS NULL"),
        ),
    )

    id:Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # RESTRICT: a contract or port that still has voyages cannot be deleted
    contract_id:Mapped[int]=mapped_column(ForeignKey("contracts.id",ondelete="RESTRICT"),index=True)
    from_port_id:Mapped[int]=mapped_column(ForeignKey("ports.id",ondelete="RESTRICT"))
    to_port_id:Mapped[int]=mapped_column(ForeignKey("ports.id",ondelete="RESTRICT"))
    cosp_at:Mapped[datetime]=mapped_column(DateTime(timezone=True))
    # Empty while the ship is still on passage
    eosp_at:Mapped[datetime | None]=mapped_column(DateTime(timezone=True))
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())

    contract:Mapped["Contract"]=relationship()
    from_port:Mapped["Port"]=relationship(foreign_keys=[from_port_id])
    to_port:Mapped["Port"]=relationship(foreign_keys=[to_port_id])

