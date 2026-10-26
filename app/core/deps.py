from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
credentials_exception = HTTPException(
       status_code=status.HTTP_401_UNAUTHORIZED,
       detail="Gecersiz kimlik bilgisi",
       headers={"WWW-Authenticate": "Bearer"},
   )
   
def get_current_user(token:str=Depends(oauth2_scheme),db:Session=Depends(get_db)) -> User:
    user_id=decode_token(token)
    if user_id is None:
        raise credentials_exception
    user=db.get(User,user_id)
    if user is None:
        raise credentials_exception
    return user
