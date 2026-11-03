from datetime import datetime,timedelta,timezone


import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash=PasswordHash.recommended()
ACCESS_TOKEN_COOKIE="access_token"

def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password:str,hashed_password:str) -> bool:

    return password_hash.verify(plain_password,hashed_password)

def create_access_token(user_id:int) -> str:
    expires=datetime.now(timezone.utc)+timedelta(minutes=settings.access_token_expire_minutes)
    payload={"sub":str(user_id),"exp":expires}
    return jwt.encode(payload,settings.secret_key,algorithm=settings.algorithm)

def decode_token(token:str) -> int | None: 
    try:
        decoded=jwt.decode(token,settings.secret_key,algorithms=[settings.algorithm])
        return int(decoded["sub"])
    except jwt.InvalidTokenError:
        
        return None
