from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings



from app.routers import auth,contracts,vessels,identity_document,certificates,ports,voyages




app=FastAPI(title="SeaLog")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET","POST","PATCH","DELETE"],
    allow_headers=["Authorization","Content-Type"],
)
app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(vessels.router)
app.include_router(identity_document.router)
app.include_router(certificates.router)
app.include_router(ports.router)
app.include_router(voyages.router)
