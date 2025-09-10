from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from ..config import settings

client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.db_name]

COLL_EPCI = settings.coll_epci
COLL_REGION = settings.coll_region
COLL_SW = settings.coll_solar_wind_dept

async def ensure_indexes():
    # Без unique=True, чтобы не падать, если есть другой индекс:
    await db[COLL_EPCI].create_index([("annee", ASCENDING), ("code_epci", ASCENDING)])
    await db[COLL_REGION].create_index([("annee", ASCENDING), ("code_region", ASCENDING)])
    await db[COLL_SW].create_index([("Département", ASCENDING)])
    await db[COLL_SW].create_index([("Filière", ASCENDING)])
    await db[COLL_SW].create_index([("Valeur (MW)", DESCENDING)])



def close_connection() -> None:
    """Закрыть Mongo-клиент при завершении приложения."""
    client.close()