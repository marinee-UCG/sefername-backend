from fastapi import APIRouter, Depends, HTTPException, status,Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import hash_password,verify_password,create_access_token,ACCESS_TOKEN_COOKIE

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut,Token
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
        full_name=user_in.full_name,
        rank=user_in.rank,
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
