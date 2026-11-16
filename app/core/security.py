from datetime import datetime,timedelta,timezone


import jwt
from pwdlib import PasswordHash

from app.core.config import settings


password_hash=PasswordHash.recommended()

ACCESS_TOKEN_COOKIE="access_token"
# Checked against when the email has no account, so both cases take the same time
DUMMY_PASSWORD_HASH=password_hash.hash("not-a-real-password")

def hash_password(password:str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password:str,hashed_password:str) -> bool:

    return password_hash.verify(plain_password,hashed_password)

def create_access_token(user_id:int,session_id:str) -> str:
    now=datetime.now(timezone.utc)
    expires=now+timedelta(minutes=settings.access_token_expire_minutes)
    payload={"sub":str(user_id),"exp":expires,"sid":session_id,"iat":now,"typ":"access"}
    return jwt.encode(payload,settings.secret_key,algorithm=settings.algorithm)

def decode_token(token:str) -> tuple[int,str] | None: 
    try:
        decoded=jwt.decode(token,settings.secret_key,algorithms=[settings.algorithm],options={"require":["exp","sub","sid","typ"]})
        if decoded["typ"] != "access":
            return None
        return int(decoded["sub"]),decoded["sid"]
    except jwt.InvalidTokenError:
        
        return None
