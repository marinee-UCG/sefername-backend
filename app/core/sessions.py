import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Response
from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import ACCESS_TOKEN_COOKIE, create_access_token
from app.models.refresh_token import RefreshToken

REFRESH_TOKEN_COOKIE = "refresh_token"


class SessionError(Exception):
    """The refresh token is missing, unknown, expired or already used."""


def _hash(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def _lifetime(persistent: bool) -> timedelta:
    days = settings.refresh_token_expire_days if persistent else settings.session_refresh_expire_days
    return timedelta(days=days)


def _set_cookies(response: Response, user_id: int, raw_refresh: str, persistent: bool) -> None:
    common = {"httponly": True, "secure": settings.cookie_secure, "samesite": "lax", "path": "/"}
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=create_access_token(user_id),
        max_age=settings.access_token_expire_minutes * 60,
        **common,
    )
    # Without max_age the browser drops the cookie when it closes ("keep me signed in" off)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=raw_refresh,
        max_age=int(_lifetime(persistent).total_seconds()) if persistent else None,
        **common,
    )


def start_session(response: Response, db: Session, user_id: int, persistent: bool) -> None:
    """Signs in: a new refresh token row and both cookies."""
    now = datetime.now(timezone.utc)
    # Tidy this user's dead rows while we are here
    db.execute(
        delete(RefreshToken).where(
            RefreshToken.user_id == user_id,
            or_(RefreshToken.expires_at < now, RefreshToken.revoked_at.is_not(None)),
        )
    )
    raw = secrets.token_urlsafe(32)
    db.add(RefreshToken(
        user_id=user_id,
        token_hash=_hash(raw),
        persistent=persistent,
        expires_at=now + _lifetime(persistent),
    ))
    db.commit()
    _set_cookies(response, user_id, raw, persistent)


def refresh_session(response: Response, db: Session, raw_token: str | None) -> int:
    """Swaps a refresh token for a new pair of cookies; returns the user id."""
    if not raw_token:
        raise SessionError
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw_token)))
    if row is None:
        raise SessionError
    now = datetime.now(timezone.utc)
    if row.revoked_at is not None:
        # A used token came back: someone has a copy. End every sign-in of this user.
        end_all_sessions(db, row.user_id)
        raise SessionError
    if row.expires_at <= now:
        raise SessionError

    row.revoked_at = now
    raw = secrets.token_urlsafe(32)
    db.add(RefreshToken(
        user_id=row.user_id,
        token_hash=_hash(raw),
        persistent=row.persistent,
        expires_at=now + _lifetime(row.persistent),
    ))
    db.commit()
    _set_cookies(response, row.user_id, raw, row.persistent)
    return row.user_id


def is_persistent(db: Session, raw_token: str | None) -> bool:
    """Whether this device chose "keep me signed in" (true when it cannot tell)."""
    if not raw_token:
        return True
    row = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw_token)))
    return row.persistent if row else True


def end_session(response: Response, db: Session, raw_token: str | None) -> None:
    """Signs out this device: its refresh token stops working and both cookies go."""
    if raw_token:
        db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == _hash(raw_token), RefreshToken.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        db.commit()
    clear_cookies(response)


def end_all_sessions(db: Session, user_id: int) -> None:
    """Every device of this user has to sign in again (password change, stolen token)."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    db.commit()


def clear_cookies(response: Response) -> None:
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE, path="/")
