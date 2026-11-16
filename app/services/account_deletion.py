"""Deleting an account and everything it owns. One place, used by the app (/account/delete)
and by the admin tool (app/scripts/admin.py), so neither can forget a step.

Steps: revoke Apple links at Apple (App Store rule, best effort) -> delete the user row
(ON DELETE CASCADE removes contracts, voyages, documents, certificates, sessions, identities)
-> remove the uploaded files (passport scans must not outlive the account) -> security log.
"""
import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import security_event
from app.core.config import settings
from app.models.user import User
from app.models.user_identity import UserIdentity
from app.services.apple_links import revoke as revoke_apple_link


def delete_user(db: Session, user: User, by: str = "user", ip: str | None = None) -> None:
    """`by` says who did it ("user" from the app, "admin" from the admin tool) for the log."""
    user_id = user.id
    for link in db.scalars(select(UserIdentity).where(UserIdentity.user_id == user_id)).all():
        revoke_apple_link(link)
    db.delete(user)
    db.commit()
    shutil.rmtree(Path(settings.upload_dir) / str(user_id), ignore_errors=True)
    # Only the id stays in the log: the account and its data are gone
    security_event("account_deleted", user_id=user_id, by=by, **({"ip": ip} if ip else {}))
