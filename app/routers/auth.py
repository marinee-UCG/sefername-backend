from fastapi import APIRouter, Depends, HTTPException, status,Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from datetime import date,datetime,timedelta,timezone

from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import hash_password,verify_password,create_access_token,ACCESS_TOKEN_COOKIE

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
def login(response:Response,form_data:OAuth2PasswordRequestForm=Depends(),db:Session=Depends(get_db)):
    email=form_data.username.lower()
    user=db.scalar(select(User).where(User.email==email))
    if not user or not verify_password(form_data.password,user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong email or password",
            headers={"WWW-Authenticate":"Bearer"},
        )
    access_token=create_access_token(user.id)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=settings.access_token_expire_minutes*60,
        path="/",
    )
    

    return {"access_token":access_token,"token_type":"bearer"}


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
def logout(response:Response):
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE,path="/")


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
