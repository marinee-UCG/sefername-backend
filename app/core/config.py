from pydantic_settings import BaseSettings,SettingsConfigDict

class Settings(BaseSettings):
    database_url:str
    secret_key:str
    algorithm:str="HS256"
    access_token_expire_minutes:int = 30
    upload_dir:str="uploads"
    max_upload_size_mb:int=10
    cors_origins:list[str]=["http://localhost:5173"]
    cookie_secure:bool=False
    

    model_config=SettingsConfigDict(env_file=".env")


settings=Settings()
