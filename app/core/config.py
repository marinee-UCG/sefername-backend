import base64

from pydantic import Field,field_validator
from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    database_url:str
    # Signs every token: too short and it can be guessed, so the app will not start with one
    secret_key:str=Field(min_length=32)
    algorithm:str="HS256"
    access_token_expire_minutes:int = 30
    # Refresh token: 30 days with "keep me signed in", otherwise one day (and the browser session)
    refresh_token_expire_days:int = 30
    session_refresh_expire_days:int = 1
    upload_dir:str="uploads"
    # Uploaded files and sensitive fields (document numbers...) are stored encrypted (AES-256-GCM)
    # with this key: 32 random bytes, base64.
    # Make one with:  python -c "import os,base64;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
    # Keep a copy somewhere safe and NOT next to the backups: without it nothing encrypted can be read.
    data_encryption_key:str
    # After a key change, the previous keys still decrypt older data (newest first)
    data_encryption_old_keys:list[str]=[]
    max_upload_size_mb:int=10
    user_storage_limit_mb:int=200
    extract_per_hour:int = 10
    cors_origins:list[str]=["http://localhost:5173"]
    cookie_secure:bool=False
    # Swagger (/docs) is handy on the laptop; on the server it would show every endpoint to anyone
    docs_enabled:bool=True
    promotion_service_days:int=900
    news_feed_url:str="https://www.trthaber.com/manset_articles.rss"
    news_refresh_minutes:int=15
    news_count:int=5
    currency_feed_url:str="https://www.tcmb.gov.tr/kurlar/today.xml"
    currency_refresh_minutes:int=60
    currency_codes:list[str]=["USD","EUR","GBP"]
    

    model_config=SettingsConfigDict(env_file=".env")

    @field_validator("data_encryption_key")
    @classmethod
    def check_file_key(cls,value:str) -> str:
        # A wrong key must stop the app at start, not on the first upload
        try:
            raw=base64.urlsafe_b64decode(value)
        except ValueError as exc:
            raise ValueError("DATA_ENCRYPTION_KEY is not valid base64") from exc
        if len(raw)!=32:
            raise ValueError("DATA_ENCRYPTION_KEY must be 32 bytes (base64 of os.urandom(32))")
        return value


settings=Settings()
