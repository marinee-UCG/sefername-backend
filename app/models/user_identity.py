from datetime import datetime

from sqlalchemy import DateTime,ForeignKey,String,Text,func,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column

from app.database import Base

class UserIdentity(Base):
    __tablename__="user_identities"

    __table_args__=(
        UniqueConstraint("provider","subject",name="uq_user_identities_provider_subject"),
        UniqueConstraint("user_id","provider",name="uq_user_identities_user_provider"),
    )
    id:Mapped[int]=mapped_column(primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    provider:Mapped[str]=mapped_column(String(20))
    subject:Mapped[str]=mapped_column(String(255))
    email:Mapped[str | None]=mapped_column(String(255))
    # Which of our app ids the sign-in was for (Apple needs the same one to revoke the link)
    client_id:Mapped[str | None]=mapped_column(String(255))
    # Apple only: the refresh token Apple gave for this link, used to revoke it when the account is deleted.
    # Sealed like the document numbers (core/crypto.py): a token in a leaked table must not work.
    provider_refresh_token:Mapped[str | None]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())