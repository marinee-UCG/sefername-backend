from fastapi import FastAPI

from app.database import Base,engine
from app.models import user
from app.routers import auth

Base.metadata.create_all(bind=engine)

app=FastAPI(title="SeaLog")
app.include_router(auth.router)

