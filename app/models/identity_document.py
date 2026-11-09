from datetime import datetime,date

from sqlalchemy import String,ForeignKey,DateTime,func,false
from sqlalchemy.orm import mapped_column,Mapped
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class IdentityDocument(Base):
    __tablename__="identity_documents"

    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    doc_type:Mapped[str]=mapped_column(String(30))
    document_number:Mapped[str | None ]=mapped_column(String(50))
    issuing_country:Mapped[str | None]=mapped_column(String(50))
    issue_date:Mapped[ date  | None]
    expiry_date:Mapped[date | None]
    file_path:Mapped[str | None]=mapped_column(String(255))
    extracted_data:Mapped[dict |None]=mapped_column(JSONB)
    verified:Mapped[bool]=mapped_column(default=False,server_default=false())
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
    @property
    def has_file(self) -> bool:
        return self.file_path is not None