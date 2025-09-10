from fastapi import FastAPI
from .routers import epci_router, region_router, solar_wind_router, major_installs_router
from .database.mongodb import ensure_indexes, close_connection

app = FastAPI(title="Energy API")

@app.on_event("startup")
async def startup():
    await ensure_indexes()

@app.on_event("shutdown")
async def shutdown():
    close_connection()

app.include_router(epci_router, prefix="/api")
app.include_router(region_router, prefix="/api")
app.include_router(solar_wind_router, prefix="/api")
app.include_router(major_installs_router, prefix="/api")