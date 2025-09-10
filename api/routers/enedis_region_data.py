# api/routers/enedis_region_data.py
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.enedis_region import RegionIn, RegionOut, RegionUpdate

COLL_REGION = "enedis_region_data"

router = APIRouter(prefix="/regions", tags=["Regions"])

def _num_or_str(v: str | int):
    """Пробуем интерпретировать значение как число, иначе оставляем строкой."""
    try:
        return int(v)
    except Exception:
        return v

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Mongo ObjectId -> str (чтобы проходила валидация/сериализация)."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ---------- DEBUG: один документ ----------
@router.get("/debug/one", response_model=RegionOut)
async def debug_one():
    doc = await db[COLL_REGION].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)


# ---------- LIST ----------
@router.get("", response_model=List[RegionOut])
async def list_regions(
    annee: Optional[int] = Query(None),
    code_region: Optional[str] = Query(None),
    nom_region: Optional[str] = Query(None, description="Filtrer par nom de région (correspondance exacte)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Exemple: 'annee,-conso_totale_mwh'"),
):
    # конструируем AND из переданных фильтров
    and_clauses: List[Dict[str, Any]] = []

    if annee is not None:
        and_clauses.append({"annee": annee})

    if code_region:
        # допускаем в БД хранение как числом, так и строкой
        and_clauses.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})

    if nom_region:
        and_clauses.append({"nom_region": nom_region})

    q: Dict[str, Any] = {"$and": and_clauses} if and_clauses else {}

    cursor = db[COLL_REGION].find(q)

    # Сортировка
    if sort:
        spec = []
        for part in sort.split(","):
            p = part.strip()
            if not p:
                continue
            spec.append((p[1:], DESCENDING) if p.startswith("-") else (p, ASCENDING))
        if spec:
            cursor = cursor.sort(spec)

    docs = await cursor.skip(offset).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- SAMPLE (быстрый срез) ----------
@router.get("/sample", response_model=List[RegionOut])
async def sample_regions(
    limit: int = Query(3, ge=1, le=50),
    annee: Optional[int] = Query(None),
    code_region: Optional[str] = Query(None),
    nom_region: Optional[str] = Query(None),
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if nom_region:
        ands.append({"nom_region": nom_region})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    cursor = db[COLL_REGION].find(q).limit(limit)
    docs = await cursor.to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- DISTINCT ----------
@router.get("/distinct")
async def distinct(field: str):
    """Renvoie une liste de valeurs uniques pour le champ (annee, code_region, nom_region, ...)."""
    vals = await db[COLL_REGION].distinct(field)
    # убираем None и сортируем как строки для стабильного вывода
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))


# ---------- COUNT ----------
@router.get("/count")
async def count_regions(
    annee: Optional[int] = None,
    code_region: Optional[str] = None,
    nom_region: Optional[str] = None,
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if nom_region:
        ands.append({"nom_region": nom_region})

    q = {"$and": ands} if ands else {}
    n = await db[COLL_REGION].count_documents(q)
    return {"count": n, "query": q}


# ---------- BY KEY (annee + code_region) ----------
@router.get("/by_key/{annee}/{code_region}", response_model=RegionOut)
async def get_by_key(annee: int, code_region: str = Path(..., description="Code de région (numéro ou ligne)")):
    doc = await db[COLL_REGION].find_one({
        "annee": annee,
        "$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}],
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=RegionOut)
async def get_region(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_REGION].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- CREATE ----------
@router.post("", response_model=RegionOut, status_code=201)
async def create_region(payload: RegionIn):
    res = await db[COLL_REGION].insert_one(payload.model_dump(exclude_none=True))
    doc = await db[COLL_REGION].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[RegionOut], status_code=201)
async def bulk_insert(items: List[RegionIn]):
    if not items:
        return []
    docs = [i.model_dump(exclude_none=True) for i in items]
    res = await db[COLL_REGION].insert_many(docs)
    cursor = db[COLL_REGION].find({"_id": {"$in": res.inserted_ids}})
    out = await cursor.to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=RegionOut)
async def update_region(doc_id: str, payload: RegionUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if data:
        await db[COLL_REGION].update_one({"_id": _id}, {"$set": data})
    doc = await db[COLL_REGION].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_region(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_REGION].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
