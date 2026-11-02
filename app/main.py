from fastapi import FastAPI


from app.routers import auth,contracts,vessels,identity_document




app=FastAPI(title="SeaLog")
app.include_router(auth.router)
app.include_router(contracts.router)
app.include_router(vessels.router)
app.include_router(identity_document.router)

