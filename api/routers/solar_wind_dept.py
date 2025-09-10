from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, HTTPException, Path, Query
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from ..database import db
from ..models.solar_wind_dept import SolarWindIn, SolarWindOut, SolarWindUpdate

router = APIRouter(prefix="/solar_wind_dept", tags=["Solar/Wind by Département"])

# Точное имя коллекции в Mongo (как в Compass)
COLL_SW = "Répartition des installations de production d'électricité solaire et éolienne en France, à la maille départementale"

# Соответствие Python-имен -> Mongo-ключей (с пробелами/акцентами)
F = {
    "departement": "Département",
    "longitude": "Longitude",
    "latitude": "Latitude",
    "filiere": "Filière",
    "valeur_mw": "Valeur (MW)",
}

# Для distinct позволяем только то, что реально полезно
ALLOWED_DISTINCT_FIELDS = {"departement", "filiere"}


def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def _build_sort(sort: Optional[str]) -> Optional[List[Tuple[str, int]]]:
    if not sort:
        return None
    spec: List[Tuple[str, int]] = []
    for part in sort.split(","):
        p = part.strip()
        if not p:
            continue
        desc = p.startswith("-")
        key = p[1:] if desc else p
        # допускаем и python-имя, и «французский» ключ
        mongo_key = F.get(key, key)
        spec.append((mongo_key, DESCENDING if desc else ASCENDING))
    return spec or None


def _range_filter(min_v: Optional[float], max_v: Optional[float]) -> Optional[Dict[str, Any]]:
    if min_v is None and max_v is None:
        return None
    cond: Dict[str, Any] = {}
    if min_v is not None:
        cond["$gte"] = min_v
    if max_v is not None:
        cond["$lte"] = max_v
    return cond or None


# ---------- DEBUG ----------
@router.get("/debug/one", response_model=SolarWindOut, summary="Любая запись (для проверки)")
async def debug_one():
    doc = await db[COLL_SW].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)


@router.get("/_debug", summary="Debug: кол-во документов")
async def _debug():
    n = await db[COLL_SW].count_documents({})
    return {"collection": COLL_SW, "count": n}


# ---------- LIST ----------
@router.get("", response_model=List[SolarWindOut], summary="Список установок по департаментам")
async def list_sw(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="например: filiere,-valeur_mw или 'Filière,-Valeur (MW)'"),
    departement: Optional[str] = Query(None, description="Название департамента (точное совпадение)"),
    filiere: Optional[str] = Query(None, description="Solaire | Éolien"),
    valeur_min: Optional[float] = Query(None, description="Мин. значение MW"),
    valeur_max: Optional[float] = Query(None, description="Макс. значение MW"),
):
    q: Dict[str, Any] = {}
    if departement:
        q[F["departement"]] = departement
    if filiere:
        q[F["filiere"]] = filiere
    rng = _range_filter(valeur_min, valeur_max)
    if rng:
        q[F["valeur_mw"]] = rng

    cursor = db[COLL_SW].find(q)
    s = _build_sort(sort)
    if s:
        cursor = cursor.sort(s)

    docs = await cursor.skip(offset).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- SAMPLE ----------
@router.get("/sample", response_model=List[SolarWindOut], summary="N примеров (быстрый просмотр)")
async def sample_sw(
    limit: int = Query(3, ge=1, le=50),
    departement: Optional[str] = None,
    filiere: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if departement:
        q[F["departement"]] = departement
    if filiere:
        q[F["filiere"]] = filiere

    docs = await db[COLL_SW].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- DISTINCT ----------
@router.get("/distinct", response_model=List[str], summary="Уникальные значения поля")
async def distinct_sw(field: str = Query(..., description="departement | filiere")):
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Недопустимое поле '{field}'")
    vals = await db[COLL_SW].distinct(F[field])
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))


# ---------- COUNT ----------
@router.get("/count", summary="Сколько документов по фильтру")
async def count_sw(
    departement: Optional[str] = None,
    filiere: Optional[str] = None,
    valeur_min: Optional[float] = None,
    valeur_max: Optional[float] = None,
):
    q: Dict[str, Any] = {}
    if departement:
        q[F["departement"]] = departement
    if filiere:
        q[F["filiere"]] = filiere
    rng = _range_filter(valeur_min, valeur_max)
    if rng:
        q[F["valeur_mw"]] = rng

    n = await db[COLL_SW].count_documents(q)
    return {"count": n, "query": q}


# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=SolarWindOut, summary="Документ по ObjectId")
async def get_sw(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_SW].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- CREATE ----------
@router.post("", response_model=SolarWindOut, status_code=201, summary="Создать запись")
async def create_sw(payload: SolarWindIn):
    data = payload.model_dump(exclude_none=True, by_alias=True)  # пишем ключами из Mongo
    res = await db[COLL_SW].insert_one(data)
    doc = await db[COLL_SW].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[SolarWindOut], status_code=201, summary="Массовая загрузка")
async def bulk_insert_sw(items: List[SolarWindIn]):
    if not items:
        return []
    docs = [i.model_dump(exclude_none=True, by_alias=True) for i in items]
    res = await db[COLL_SW].insert_many(docs)
    out = await db[COLL_SW].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=SolarWindOut, summary="Обновить запись")
async def update_sw(doc_id: str, payload: SolarWindUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = {k: v for k, v in payload.model_dump(exclude_unset=True, by_alias=True).items()}
    if data:
        await db[COLL_SW].update_one({"_id": _id}, {"$set": data})
    doc = await db[COLL_SW].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204, summary="Удалить запись")
async def delete_sw(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_SW].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
