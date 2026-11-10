from fastapi import APIRouter, Depends, Form, HTTPException, status,Response,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date,datetime,timedelta,timezone

from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import hash_password,verify_password,create_access_token,ACCESS_TOKEN_COOKIE,DUMMY_PASSWORD_HASH
from app.core.rate_limit import login_throttle,MAX_FAILURES_PER_ACCOUNT,MAX_FAILURES_PER_ADDRESS
from app.core.sessions import REFRESH_TOKEN_COOKIE,SessionError,clear_cookies,end_session,refresh_session,start_session

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut,UserUpdate,Token,OnboardingIn
from app.core.deps import get_current_user
from app.core.config import settings

router =APIRouter(prefix="/auth",tags=["auth"])

@router.post("/register",response_model=UserOut,status_code=status.HTTP_201_CREATED)
def register(user_in:UserCreate,db:Session=Depends(get_db)):
    email=user_in.email.lower()
    existing=db.scalar(select(User).where(User.email==email))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Email already in use")
    user=User(
        email=email,
        hashed_password=hash_password(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/login",response_model=Token)
def login(
    request:Request,
    response:Response,
    form_data:OAuth2PasswordRequestForm=Depends(),
    remember:bool=Form(True),
    db:Session=Depends(get_db),
):
    email=form_data.username.lower()
    # Behind a proxy this is the proxy's address unless uvicorn runs with --proxy-headers
    address=request.client.host if request.client else "unknown"
    account_key=f"account:{email}|{address}"
    address_key=f"address:{address}"

    # Checked before the password: a locked door does not even look at the key
    wait=max(
        login_throttle.retry_after(account_key,MAX_FAILURES_PER_ACCOUNT),
        login_throttle.retry_after(address_key,MAX_FAILURES_PER_ADDRESS),
    )
    if wait:
        minutes=max(1,round(wait/60))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many sign-in attempts. Try again in {minutes} minute{'s' if minutes>1 else ''}.",
            headers={"Retry-After":str(wait)},
        )

    user=db.scalar(select(User).where(User.email==email))
    # Always verify against some hash, so an unknown email takes as long as a wrong password
    # (otherwise the response time tells which emails have an account)
    password_ok=verify_password(form_data.password,user.hashed_password if user else DUMMY_PASSWORD_HASH)
    if not user or not password_ok:
        login_throttle.record_failure(account_key)
        login_throttle.record_failure(address_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong email or password",
            headers={"WWW-Authenticate":"Bearer"},
        )
    login_throttle.reset(account_key)
    start_session(response,db,user.id,persistent=remember)
    # The body keeps a token for Swagger's Authorize button; the app itself only uses the cookies
    return {"access_token":create_access_token(user.id),"token_type":"bearer"}


@router.post("/refresh",status_code=status.HTTP_204_NO_CONTENT)
def refresh(request:Request,response:Response,db:Session=Depends(get_db)):
    try:
        refresh_session(response,db,request.cookies.get(REFRESH_TOKEN_COOKIE))
    except SessionError:
        # The response that says "sign in again" also takes the dead cookies away
        failed=Response(status_code=status.HTTP_401_UNAUTHORIZED)
        clear_cookies(failed)
        return failed
    response.status_code=status.HTTP_204_NO_CONTENT
    return response


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


@router.post("/logout",status_code=status.HTTP_204_NO_CONTENT)
def logout(request:Request,response:Response,db:Session=Depends(get_db)):
    # Unlike the access token, the refresh token really stops working here
    end_session(response,db,request.cookies.get(REFRESH_TOKEN_COOKIE))


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
