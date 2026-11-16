from fastapi import APIRouter, Depends, Form, HTTPException, status,Response,Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import date,datetime,timedelta,timezone

from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import hash_password,verify_password,DUMMY_PASSWORD_HASH
from app.core.rate_limit import login_throttle,register_throttle,MAX_FAILURES_PER_ACCOUNT,MAX_FAILURES_PER_ADDRESS,MAX_REGISTRATIONS_PER_ADDRESS,MAX_FAILURES_PER_EMAIL
from app.core.sessions import REFRESH_TOKEN_COOKIE,SessionError,SessionTokens,clear_cookies,end_session,refresh_session,start_session,set_session_cookies

from app.services.apple_links import store_refresh_token
from app.services.social_auth import ProviderDisabledError,ProviderUnavailableError,SocialAuthError,SocialIdentity,verify_id_token
from app.database import get_db
from app.models.user_identity import UserIdentity
from app.models.user import User
from app.schemas.user import UserCreate, UserOut,UserUpdate,OnboardingIn,TokenPair,RefreshIn,SocialLoginIn
from app.core.deps import get_current_user
from app.core.config import settings
from app.core.audit import security_event

router =APIRouter(prefix="/auth",tags=["auth"])

# Two doors into the same sessions:
#   web (browser)  /auth/login, /auth/refresh, /auth/logout              tokens travel in httpOnly cookies
#   native (iOS)   /auth/token, /auth/token/refresh, /auth/token/revoke  tokens travel in the JSON body
# A refresh token never lands where the web page's JavaScript could read it.


def authenticate(request:Request,form_data:OAuth2PasswordRequestForm,db:Session) ->User:
    """Who is this, and is it really them? Shared by both doors: same limits, same timing, same message."""
    email=form_data.username.lower()
    # Behind a proxy this is the proxy's address unless uvicorn runs with --proxy-headers
    address=request.client.host if request.client else "unknown"
    account_key=f"account:{email}|{address}"
    email_key=f"email:{email}"
    address_key=f"address:{address}"

    # Checked before the password: a locked door does not even look at the key
    wait=max(
        login_throttle.retry_after(account_key,MAX_FAILURES_PER_ACCOUNT),
        login_throttle.retry_after(address_key,MAX_FAILURES_PER_ADDRESS),
        login_throttle.retry_after(email_key,MAX_FAILURES_PER_EMAIL),
    )
    if wait:
        security_event("login_blocked",request,email=email,retry_after=wait)
        minutes=max(1,round(wait/60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many sign-in attempts. Try again in {minutes} minute{'s' if minutes>1 else ''}.",
            headers={"Retry-After":str(wait)},
        )

    user=db.scalar(select(User).where(User.email==email))
    # Always verify against some hash, so an unknown email takes as long as a wrong password
    # (otherwise the response time tells which emails have an account)
    # An account made with Google/Apple has no password: it is checked against the dummy hash too
    # (same timing) and always fails, so nobody can sign in to it with a password
    has_password=user is not None and user.hashed_password is not None
    password_ok=verify_password(form_data.password,user.hashed_password if has_password else DUMMY_PASSWORD_HASH)
    if not has_password or not password_ok:
        login_throttle.record_failure(account_key)
        login_throttle.record_failure(address_key)
        login_throttle.record_failure(email_key)
        # known_account is for whoever reads the log, never sent to the client
        security_event("login_failed",request,email=email,known_account=user is not None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong email or password",
            headers={"WWW-Authenticate":"Bearer"},
        )
    login_throttle.reset(account_key)
    security_event("login_succeeded",request,user_id=user.id)
    return user

def social_sign_in(db:Session,identity:SocialIdentity) -> User:
    query=select(UserIdentity).where(UserIdentity.provider==identity.provider,UserIdentity.subject==identity.subject)
    link=db.scalar(query)
    if link is not None:
        return db.get(User,link.user_id)
    if identity.email is not None:
        query2=select(User).where(User.email==identity.email)
        link2=db.scalar(query2)
        if link2 is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with this email already exists. Sign in with your password, then connect {identity.provider.title()} in Settings"
            )
    if identity.email is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Your Google/Apple account did not share an email address"
        )
    if not identity.email_verified:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="This email address is not verified with the provider"
        )
    user=User(email=identity.email,hashed_password=None)
    db.add(user)
    db.flush()
    db.add(UserIdentity(
        user_id=user.id,
        provider=identity.provider,
        subject=identity.subject,
        email=identity.email,
        client_id=identity.audience,
    ))
    db.commit()
    db.refresh(user)
    return user

    

def token_pair(tokens:SessionTokens) -> TokenPair:
    return TokenPair(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=settings.access_token_expire_minutes*60,
    )


@router.post("/register",response_model=UserOut,status_code=status.HTTP_201_CREATED)
def register(user_in:UserCreate,request:Request,db:Session=Depends(get_db)):
    # "Email already in use" tells whether an account exists, so sign-ups are limited per address:
    # a person signs up once or twice, a script trying a list of emails hits the limit
    address=request.client.host if request.client else "unknown"
    address_key=f"register:{address}"
    wait=register_throttle.retry_after(address_key,MAX_REGISTRATIONS_PER_ADDRESS)
    if wait:
        security_event("register_blocked",request,retry_after=wait)
        minutes=max(1,round(wait/60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many sign-ups from this network. Try again in {minutes} minute{'s' if minutes>1 else ''}.",
            headers={"Retry-After":str(wait)},
        )
    register_throttle.record_failure(address_key)

    email=user_in.email.lower()
    existing=db.scalar(select(User).where(User.email==email))
    if existing:
        # Many of these from one address = someone checking which emails have an account
        security_event("register_email_taken",request,email=email)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Email already in use")
    user=User(
        email=email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    security_event("register_succeeded",request,user_id=user.id)
    return user


# ---------- Web: cookies ----------

@router.post("/login",status_code=status.HTTP_204_NO_CONTENT)
def login(
    request:Request,
    response:Response,
    form_data:OAuth2PasswordRequestForm=Depends(),
    remember:bool=Form(True),
    db:Session=Depends(get_db),
):
    user=authenticate(request,form_data,db)
    tokens=start_session(db,user.id,persistent=remember)
    # Nothing in the body: the page never sees a token, only the browser holds them
    set_session_cookies(response,tokens)
    response.status_code=status.HTTP_204_NO_CONTENT
    return response


@router.post("/refresh",status_code=status.HTTP_204_NO_CONTENT)
def refresh(request:Request,response:Response,db:Session=Depends(get_db)):
    try:
        tokens=refresh_session(db,request.cookies.get(REFRESH_TOKEN_COOKIE))
    except SessionError:
        # The response that says "sign in again" also takes the dead cookies away
        failed=Response(status_code=status.HTTP_401_UNAUTHORIZED)
        clear_cookies(failed)
        return failed
    set_session_cookies(response,tokens)
    response.status_code=status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout",status_code=status.HTTP_204_NO_CONTENT)
def logout(request:Request,response:Response,db:Session=Depends(get_db)):
    # The whole session ends: its access tokens stop working on the next request too
    end_session(db,request.cookies.get(REFRESH_TOKEN_COOKIE))
    clear_cookies(response)
    response.status_code=status.HTTP_204_NO_CONTENT
    return response


# ---------- Native (iOS): JSON body, kept in the Keychain ----------

@router.post("/token",response_model=TokenPair)
def issue_token(
    request:Request,
    form_data:OAuth2PasswordRequestForm=Depends(),
    db:Session=Depends(get_db),
):
    """Sign in from the app. Also what Swagger's Authorize button uses."""
    user=authenticate(request,form_data,db)
    # An app stays signed in until the user signs out (like every phone app); the token still rotates
    tokens=start_session(db,user.id,persistent=True)
    return token_pair(tokens)


@router.post("/token/refresh",response_model=TokenPair)
def refresh_token(refresh_in:RefreshIn,db:Session=Depends(get_db)):
    try:
        tokens=refresh_session(db,refresh_in.refresh_token)
    except SessionError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has ended. Sign in again.",
            headers={"WWW-Authenticate":"Bearer"},
        )
    return token_pair(tokens)


@router.post("/token/revoke",status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(refresh_in:RefreshIn,db:Session=Depends(get_db)):
    # Always 204, even for an unknown token (as in RFC 7009): the answer must not tell which tokens exist
    end_session(db,refresh_in.refresh_token)


# ---------- Sign in with Google / Apple (both doors) ----------

def verified_identity(provider:str,login_in:SocialLoginIn,request:Request) -> SocialIdentity:
    """The provider's ID token checked (services/social_auth.py), its errors turned into HTTP codes."""
    try:
        return verify_id_token(provider,login_in.id_token,login_in.nonce)
    except ProviderDisabledError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Sign in with {provider.title()} is not available.")
    except ProviderUnavailableError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"{provider.title()} could not be reached. Try again in a moment.",
        )
    except SocialAuthError as exc:
        # The reason stays in our log; the user only learns that it did not work
        security_event("social_login_failed",request,provider=provider,reason=str(exc)[:100])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Sign in with {provider.title()} failed. Please try again.",
            headers={"WWW-Authenticate":"Bearer"},
        )


def social_user(provider:str,login_in:SocialLoginIn,request:Request,db:Session) -> User:
    identity=verified_identity(provider,login_in,request)
    try:
        user=social_sign_in(db,identity)
    except IntegrityError:
        # Two first sign-ins at the same moment: the other one created the account and its link
        # (the unique constraints stopped this one), so the link is there now
        db.rollback()
        user=social_sign_in(db,identity)
    if login_in.authorization_code:
        # Apple: keep the link's refresh token (newest wins) so the link can be revoked on deletion
        link=db.scalar(select(UserIdentity).where(UserIdentity.provider==identity.provider,UserIdentity.subject==identity.subject))
        link.client_id=link.client_id or identity.audience
        store_refresh_token(link,login_in.authorization_code)
        db.commit()
    security_event("social_login_succeeded",request,user_id=user.id,provider=provider)
    return user


def web_social_login(provider:str,login_in:SocialLoginIn,request:Request,response:Response,db:Session) -> Response:
    user=social_user(provider,login_in,request,db)
    set_session_cookies(response,start_session(db,user.id,persistent=login_in.remember))
    response.status_code=status.HTTP_204_NO_CONTENT
    return response


def native_social_login(provider:str,login_in:SocialLoginIn,request:Request,db:Session) -> TokenPair:
    user=social_user(provider,login_in,request,db)
    return token_pair(start_session(db,user.id,persistent=True))


@router.post("/google",status_code=status.HTTP_204_NO_CONTENT)
def login_google(login_in:SocialLoginIn,request:Request,response:Response,db:Session=Depends(get_db)):
    return web_social_login("google",login_in,request,response,db)


@router.post("/apple",status_code=status.HTTP_204_NO_CONTENT)
def login_apple(login_in:SocialLoginIn,request:Request,response:Response,db:Session=Depends(get_db)):
    return web_social_login("apple",login_in,request,response,db)


@router.post("/token/google",response_model=TokenPair)
def token_google(login_in:SocialLoginIn,request:Request,db:Session=Depends(get_db)):
    return native_social_login("google",login_in,request,db)


@router.post("/token/apple",response_model=TokenPair)
def token_apple(login_in:SocialLoginIn,request:Request,db:Session=Depends(get_db)):
    return native_social_login("apple",login_in,request,db)


# ---------- Profile ----------

@router.get("/me",response_model=UserOut)
def read_me(current_user:User=Depends(get_current_user)):
    return current_user


@router.patch("/me",response_model=UserOut)
def update_me(
    user_in:UserUpdate,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db),
):
    update_data=user_in.model_dump(exclude_unset=True)

    # Once a name is set it cannot be cleared (rank can)
    if "full_name" in update_data and update_data["full_name"] is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="full_name cannot be null.",
        )

    planned=update_data.get("planned_sign_on")
    # One day of slack: the user's today can be the server's yesterday
    if planned is not None and planned < date.today()-timedelta(days=1):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Planned sign-on cannot be in the past.",
        )

    for key,value in update_data.items():
        setattr(current_user,key,value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/onboarding",response_model=UserOut)
def complete_onboarding(
    onboarding_in:OnboardingIn,
    current_user:User=Depends(get_current_user),
    db:Session=Depends(get_db)
):
    if current_user.onboarded_at is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Onboarding already completed"
        )
    onboarding=onboarding_in.model_dump()
    current_user.onboarded_at=datetime.now(timezone.utc)
    for key,value in onboarding.items():
        setattr(current_user,key,value)
    db.commit()
    db.refresh(current_user)
    return current_user
