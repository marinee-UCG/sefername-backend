import shutil
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.rate_limit import MAX_FAILURES_PER_ACCOUNT, login_throttle
from app.core.security import hash_password, verify_password
from app.core.sessions import REFRESH_TOKEN_COOKIE, clear_cookies, end_all_sessions, is_persistent, start_session
from app.database import get_db
from app.models.certificate import Certificate
from app.models.contract import Contract
from app.models.identity_document import IdentityDocument
from app.models.user import User
from app.models.voyage import Voyage
from app.routers.voyages import voyage_out
from app.schemas.account import AccountDelete, AccountExport, PasswordChange

router = APIRouter(prefix="/account", tags=["account"])


def check_password(user: User, password: str) -> None:
    """Asks for the password again, with the same failure limit as the login form."""
    key = f"password:{user.id}"
    wait = login_throttle.retry_after(key, MAX_FAILURES_PER_ACCOUNT)
    if wait:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many wrong passwords. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    if not verify_password(password, user.hashed_password):
        login_throttle.record_failure(key)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your current password is not right.")
    login_throttle.reset(key)


@router.post("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_in: PasswordChange,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_password(current_user, password_in.current_password)
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE)
    remember = is_persistent(db, raw_refresh)

    current_user.hashed_password = hash_password(password_in.new_password)
    db.commit()
    # Every other device has to sign in with the new password; this one carries on
    end_all_sessions(db, current_user.id)
    start_session(response, db, current_user.id, persistent=remember)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


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
        certificates=certificates,
        identity_documents=documents,
    )
    # A download, not a page: the browser saves it under a dated name
    return JSONResponse(
        content=export.model_dump(mode="json"),
        headers={"Content-Disposition": f'attachment; filename="sefername-export-{date.today().isoformat()}.json"'},
    )


@router.post("/delete", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    delete_in: AccountDelete,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    check_password(current_user, delete_in.password)
    user_id = current_user.id

    # The database removes the user's rows with the account (ON DELETE CASCADE)
    db.delete(current_user)
    db.commit()

    # Then the uploaded files: passport scans must not outlive the account
    user_dir = Path(settings.upload_dir) / str(user_id)
    shutil.rmtree(user_dir, ignore_errors=True)

    clear_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
