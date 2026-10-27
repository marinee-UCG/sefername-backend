from fastapi import FastAPI


from app.routers import auth,contracts




app=FastAPI(title="SeaLog")
app.include_router(auth.router)
app.include_router(contracts.router)

