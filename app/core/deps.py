from fastapi import Depends, HTTPException, status,Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.sessions import is_session_active
from app.core.security import decode_token,ACCESS_TOKEN_COOKIE
from app.database import get_db
from app.models.user import User

# Swagger's Authorize button signs in through the native door, which answers with the token in JSON
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token",auto_error=False)
credentials_exception = HTTPException(
       status_code=status.HTTP_401_UNAUTHORIZED,
       detail="Could not validate credentials",
       headers={"WWW-Authenticate": "Bearer"},
   )
   
def get_current_user(request:Request,token:str | None =Depends(oauth2_scheme),db:Session=Depends(get_db)) -> User:
    token = request.cookies.get(ACCESS_TOKEN_COOKIE) or token
    if token is None:
        raise credentials_exception
    claims=decode_token(token)
    if claims is None:
        raise credentials_exception
    user_id,session_id=claims
    if not is_session_active(db,session_id):
        raise credentials_exception
    user=db.get(User,user_id)
    if user is None:
        raise credentials_exception
    # Kept for endpoints that act on "this device", e.g. a password change keeps it signed in
    request.state.session_id=session_id
    return user
