from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    database_url:str
    secret_key:str
    algorithm:str="HS256"
    access_token_expire_minutes:int = 30
    # Refresh token: 30 days with "keep me signed in", otherwise one day (and the browser session)
    refresh_token_expire_days:int = 30
    session_refresh_expire_days:int = 1
    upload_dir:str="uploads"
    max_upload_size_mb:int=10
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


settings=Settings()
