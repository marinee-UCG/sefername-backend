from fastapi import FastAPI


from app.routers import auth



app=FastAPI(title="SeaLog")
app.include_router(auth.router)

