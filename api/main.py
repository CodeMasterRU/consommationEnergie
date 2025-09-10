from fastapi import FastAPI
from .routers import epci_router, region_router, solar_wind_router, major_installs_router, eco2mix_router, adresse_router, commune_router, departement_router, iris_router, prod_fr_router, evolution_parc_router
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
app.include_router(eco2mix_router, prefix="/api")
app.include_router(adresse_router, prefix="/api")
app.include_router(commune_router, prefix="/api")
app.include_router(departement_router, prefix="/api")
app.include_router(iris_router, prefix="/api")
app.include_router(prod_fr_router, prefix="/api")
app.include_router(evolution_parc_router, prefix="/api")