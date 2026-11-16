import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.audit import security_event
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import MAX_FAILURES_PER_ACCOUNT, login_throttle
from app.core.security import hash_password, verify_password
from app.core.sessions import clear_cookies, end_all_sessions
from app.database import get_db
from app.models.certificate import Certificate
from app.models.contract import Contract
from app.models.identity_document import IdentityDocument
from app.models.user import User
from app.models.voyage import Voyage
from app.routers.voyages import voyage_out
from app.routers.certificates import certificate_out
from app.routers.identity_document import document_out
from app.schemas.account import AccountDelete, AccountExport, IdentityOut, PasswordChange
from app.schemas.user import SocialLoginIn
from app.models.user_identity import UserIdentity
from app.routers.auth import verified_identity
from app.services.apple_links import revoke as revoke_apple_link, store_refresh_token
from sqlalchemy.exc import IntegrityError
from typing import Literal

router = APIRouter(prefix="/account", tags=["account"])


def check_password(user: User, password: str) -> None:
    """Asks for the password again, with the same failure limit as the login form."""
    key = f"password:{user.id}"
    wait = login_throttle.retry_after(key, MAX_FAILURES_PER_ACCOUNT)
    if wait:
        security_event("password_check_blocked", user_id=user.id, retry_after=wait)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many wrong passwords. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    # An account without a password (Google/Apple only) never passes this check
    if user.hashed_password is None or not verify_password(password, user.hashed_password):
        login_throttle.record_failure(key)
        # Someone holding a signed-in device but not knowing the password: worth seeing
        security_event("password_check_failed", user_id=user.id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your current password is not right.")
    login_throttle.reset(key)


def confirm_it_is_you(user: User, delete_in: AccountDelete, request: Request, db: Session) -> None:
    """Asked before wiping the account: the password, or (no password) a fresh Google/Apple sign-in
    with an account that is connected to this user."""
    if user.hashed_password is not None:
        check_password(user, delete_in.password or "")
        return
    if delete_in.provider is None or delete_in.id_token is None or delete_in.nonce is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Confirm with the Google or Apple account you sign in with.",
        )
    identity = verified_identity(
        delete_in.provider, SocialLoginIn(id_token=delete_in.id_token, nonce=delete_in.nonce), request
    )
    link = db.scalar(select(UserIdentity).where(
        UserIdentity.user_id == user.id,
        UserIdentity.provider == identity.provider,
        UserIdentity.subject == identity.subject,
    ))
    if link is None:
        security_event("password_check_failed", request, user_id=user.id, provider=identity.provider)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That is not the account you sign in with.")


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_in: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.hashed_password is None:
        # Setting a first password from a signed-in session alone would let a stolen session
        # add a permanent way in; it needs its own confirmed flow (later, with email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your account signs in with Google or Apple and has no password to change.",
        )
    check_password(current_user, password_in.current_password)

    current_user.hashed_password = hash_password(password_in.new_password)
    db.commit()
    # Every other device has to sign in with the new password; this one (web or app) carries on
    # with the tokens it already holds, so nothing new has to be sent back
    end_all_sessions(db, current_user.id, keep_session_id=request.state.session_id)
    security_event("password_changed", request, user_id=current_user.id)


@router.get("/export", response_model=AccountExport)
def export_account(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = current_user.id
    contracts = db.scalars(select(Contract).where(Contract.user_id == user_id).order_by(Contract.start_date)).all()
    voyages = db.scalars(select(Voyage).where(Voyage.user_id == user_id).order_by(Voyage.cosp_at)).all()
    certificates = db.scalars(select(Certificate).where(Certificate.user_id == user_id).order_by(Certificate.id)).all()
    documents = db.scalars(select(IdentityDocument).where(IdentityDocument.user_id == user_id).order_by(IdentityDocument.id)).all()

    export = AccountExport(
        exported_at=datetime.now(timezone.utc),
        profile=current_user,
        contracts=contracts,
        voyages=[voyage_out(v) for v in voyages],
        certificates=[certificate_out(c) for c in certificates],
        identity_documents=[document_out(d) for d in documents],
    )
    # A download, not a page: the browser saves it under a dated name
    return JSONResponse(
        content=export.model_dump(mode="json"),
        headers={"Content-Disposition": f'attachment; filename="sefername-export-{date.today().isoformat()}.json"'},
    )


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    delete_in: AccountDelete,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    confirm_it_is_you(current_user, delete_in, request, db)
    user_id = current_user.id
    # Only the id stays in the log: the account and its data are gone
    security_event("account_deleted", request, user_id=user_id)

    # The database removes the user's rows with the account (ON DELETE CASCADE)
    # Apple's rule: a deleted account's "Sign in with Apple" link is revoked at Apple too (best effort)
    for link in db.scalars(select(UserIdentity).where(UserIdentity.user_id == user_id)).all():
        revoke_apple_link(link)
    db.delete(current_user)
    db.commit()

    # Then the uploaded files: passport scans must not outlive the account
    user_dir = Path(settings.upload_dir) / str(user_id)
    shutil.rmtree(user_dir, ignore_errors=True)

    clear_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


# ---------- Connected sign-ins (Google / Apple) ----------

Provider = Literal["google", "apple"]


@router.get("/identities", response_model=list[IdentityOut])
def list_identities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.scalars(select(UserIdentity).where(UserIdentity.user_id == current_user.id).order_by(UserIdentity.provider)).all()


@router.post("/identities/{provider}", response_model=IdentityOut, status_code=status.HTTP_201_CREATED)
def connect_identity(
    provider: Provider,
    login_in: SocialLoginIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The safe way to join an existing account with Google/Apple: the user is already signed in here
    AND proves the Google/Apple account with a fresh sign-in. (No automatic joining by email.)"""
    identity = verified_identity(provider, login_in, request)
    taken = db.scalar(select(UserIdentity).where(
        UserIdentity.provider == identity.provider, UserIdentity.subject == identity.subject,
    ))
    if taken is not None:
        detail = ("This account is already connected." if taken.user_id == current_user.id
                  else f"This {provider.title()} account is already used by another Sefername account.")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    link = UserIdentity(
        user_id=current_user.id, provider=identity.provider, subject=identity.subject,
        email=identity.email, client_id=identity.audience,
    )
    store_refresh_token(link, login_in.authorization_code)
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        # Already one of this provider on the account, or connected elsewhere at the same moment
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Your account already has a {provider.title()} sign-in. Disconnect it first.",
        )
    db.refresh(link)
    security_event("identity_connected", request, user_id=current_user.id, provider=provider)
    return link


@router.delete("/identities/{provider}", status_code=status.HTTP_204_NO_CONTENT)
def disconnect_identity(
    provider: Provider,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    links = db.scalars(select(UserIdentity).where(UserIdentity.user_id == current_user.id)).all()
    link = next((l for l in links if l.provider == provider), None)
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not connected.")
    # The last way in cannot go: without a password and without another sign-in, nobody could enter again
    if current_user.hashed_password is None and len(links) == 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This is the only way you sign in. Connect another account first.",
        )
    revoke_apple_link(link)
    db.delete(link)
    db.commit()
    security_event("identity_disconnected", request, user_id=current_user.id, provider=provider)
