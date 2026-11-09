from sqlalchemy import ForeignKey,String
from datetime import date
from sqlalchemy.orm import Mapped,mapped_column

from app.database import Base

class Certificate(Base):
    __tablename__="certificates"

    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    cert_name:Mapped[str]=mapped_column(String(150))
    cert_number:Mapped[str]=mapped_column((String(50)))
    issue_date:Mapped[date]
    expiry_date:Mapped[date | None]
    issuing_inst:Mapped[str]=mapped_column(String(100))
    file_path:Mapped[str | None]=mapped_column(String(255))
    @property
    def has_file(self) ->bool:
        return self.file_path is not None
