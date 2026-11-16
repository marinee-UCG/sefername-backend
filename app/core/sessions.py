import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import NamedTuple
from uuid import uuid4

from fastapi import Response
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.audit import security_event
from app.core.config import settings
from app.core.security import ACCESS_TOKEN_COOKIE, create_access_token
from app.models.refresh_token import RefreshToken

REFRESH_TOKEN_COOKIE = "refresh_token"
REFRESH_REUSE_GRACE=timedelta(seconds=30)


class SessionError(Exception):
    """The refresh token is missing, unknown, expired or already used."""

class SessionTokens(NamedTuple):
    access_token:str
    refresh_token:str
    persistent:bool


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _lifetime(persistent: bool) -> timedelta:
    days = settings.refresh_token_expire_days if persistent else settings.session_refresh_expire_days
    return timedelta(days=days)


def set_session_cookies(response: Response, tokens:SessionTokens) -> None:
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=tokens.access_token,
        max_age=settings.access_token_expire_minutes * 60,
        **common,
    )
    # Without max_age the browser drops the cookie when it closes ("keep me signed in" off)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=tokens.refresh_token,
        max_age=int(_lifetime(tokens.persistent).total_seconds()) if tokens.persistent else None,
        **common,
    )


def start_session(db: Session, user_id: int, persistent: bool) -> SessionTokens:
    
    now = datetime.now(timezone.utc)
    # Tidy this user's dead rows while we are here
    db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(RefreshToken.expires_at < now, RefreshToken.revoked_at.is_not(None)),
        )
    )
    raw = secrets.token_urlsafe(32)
    session_id=uuid4().hex
    db.add(RefreshToken(
        user_id=user_id,
        session_id=session_id,
        token_hash=_hash(raw),
        persistent=persistent,
        expires_at=now + _lifetime(persistent),
    ))
    db.commit()
    return SessionTokens(
        access_token=create_access_token(user_id,session_id),
        persistent=persistent,
        refresh_token=raw,
    )


def refresh_session(db: Session, raw_token: str | None) -> SessionTokens:
    """Swaps a refresh token for a new pair in the same session."""
    if not raw_token:
        raise SessionError
    # Locked until commit: two refreshes at the same moment cannot both swap the same token
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw_token)).with_for_update())
    if row is None:
        raise SessionError
    now = datetime.now(timezone.utc)
    if row.revoked_at is not None:
        raise SessionError
    if row.replaced_at is not None:
        # Just swapped: two requests raced, the other one already holds the new token
        if now-row.replaced_at <= REFRESH_REUSE_GRACE:
            raise SessionError
        # An old token came back long after: someone has a copy. End every sign-in of this user.
        security_event("refresh_token_reused",user_id=row.user_id,session_id=row.session_id)
        end_all_sessions(db,row.user_id)
        raise SessionError
    if row.expires_at <= now:
        raise SessionError

    row.replaced_at = now
    raw = secrets.token_urlsafe(32)
    db.add(RefreshToken(
        user_id=row.user_id,
        session_id=row.session_id,
        token_hash=_hash(raw),
        persistent=row.persistent,
        expires_at=now + _lifetime(row.persistent),
    ))
    db.commit()
    
    return SessionTokens(
        access_token=create_access_token(row.user_id,row.session_id),
        refresh_token=raw,
        persistent=row.persistent,
    )


def end_session(db: Session, raw_token: str | None) -> None:
    """Signs out this device: every token of its session stops working.

    The whole session, not only this token: a sign-out sent with a token that was
    swapped a moment ago must still close the newer one.
    """
    if not raw_token:
        return
    row=db.scalar(select(RefreshToken).where(RefreshToken.token_hash== _hash(raw_token)))
    if row is None:
        return
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.session_id == row.session_id,RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()


def is_session_active(db:Session,session_id:str) -> bool:
    now=datetime.now(timezone.utc)
    query=select(RefreshToken.id).where(
        RefreshToken.session_id==session_id,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.replaced_at.is_(None),
        RefreshToken.expires_at > now
    )
    result=db.scalar(query)
    return result is not None


def end_all_sessions(db: Session, user_id: int, keep_session_id: str | None = None) -> None:
    """Every device of this user has to sign in again (stolen token, password change).

    `keep_session_id`: the device that changed the password carries on; all the others end.
    """
    query = update(RefreshToken).where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
    if keep_session_id is not None:
        query = query.where(RefreshToken.session_id != keep_session_id)
    db.execute(query.values(revoked_at=datetime.now(timezone.utc)))
    db.commit()


def clear_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")
