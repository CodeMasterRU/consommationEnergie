# api/routers/evolution_parc_installe_fr.py
# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.evolution_parc_installe_fr import (
    EvoParcIn, EvoParcOut, EvoParcUpdate
)

# Точное имя коллекции в MongoDB
COLL_EVOL_PARC = "Évolution du parc installé de production d'électricité en France"

router = APIRouter(prefix="/evolution_parc", tags=["Installed capacity (France)"])

# Короткие имена → реальные ключи БД (с акцентами)
_FIELD_MAP = {
    "year": "Date",
    "filiere": "Filière",
    "valeur_gw": "Valeur (GW)",
}
def _dbf(name: str) -> str:
    return _FIELD_MAP.get(name, name)

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ---------- DEBUG ----------
@router.get("/debug/one", response_model=EvoParcOut)
async def debug_one():
    doc = await db[COLL_EVOL_PARC].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)


# ---------- LIST ----------
@router.get("", response_model=List[EvoParcOut])
async def list_installed_capacity(
    year: Optional[int] = Query(None, description="Год (поле Date)"),
    filiere: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Напр.: year,-valeur_gw или имена полей БД"),
):
    q: Dict[str, Any] = {}
    if year is not None:
        q["Date"] = year
    if filiere:
        q["Filière"] = filiere

    cursor = db[COLL_EVOL_PARC].find(q)

    if sort:
        spec = []
        for part in sort.split(","):
            p = part.strip()
            if not p:
                continue
            spec.append((_dbf(p[1:]), DESCENDING) if p.startswith("-") else (_dbf(p), ASCENDING))
        if spec:
            cursor = cursor.sort(spec)

    docs = await cursor.skip(offset).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- SAMPLE ----------
@router.get("/sample", response_model=List[EvoParcOut])
async def sample_installed_capacity(
    limit: int = Query(3, ge=1, le=50),
    year: Optional[int] = Query(None),
    filiere: Optional[str] = Query(None),
):
    q: Dict[str, Any] = {}
    if year is not None:
        q["Date"] = year
    if filiere:
        q["Filière"] = filiere

    docs = await db[COLL_EVOL_PARC].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- DISTINCT ----------
ALLOWED_DISTINCT_FIELDS = {"Date", "Filière"}
@router.get("/distinct", response_model=List[Any])
async def distinct_values(field: str = Query(..., description="Date | Filière")):
    # поддержим короткие имена
    field = _dbf(field)
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Недопустимое поле '{field}'")
    vals = await db[COLL_EVOL_PARC].distinct(field)
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))


# ---------- COUNT ----------
@router.get("/count")
async def count_docs(year: Optional[int] = None, filiere: Optional[str] = None):
    q: Dict[str, Any] = {}
    if year is not None:
        q["Date"] = year
    if filiere:
        q["Filière"] = filiere
    n = await db[COLL_EVOL_PARC].count_documents(q)
    return {"count": n, "query": q}


# ---------- BY KEY (Date + Filière) ----------
@router.get("/by_key/{year}/{filiere}", response_model=EvoParcOut)
async def get_by_key(year: int, filiere: str):
    doc = await db[COLL_EVOL_PARC].find_one({"Date": year, "Filière": filiere})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=EvoParcOut)
async def get_doc(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_EVOL_PARC].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- CREATE ----------
@router.post("", response_model=EvoParcOut, status_code=201)
async def create_doc(payload: EvoParcIn):
    # сохраняем ключи БД (by_alias=True чтобы получить 'Date', 'Filière', 'Valeur (GW)')
    data = payload.model_dump(exclude_none=True, by_alias=True)
    res = await db[COLL_EVOL_PARC].insert_one(data)
    doc = await db[COLL_EVOL_PARC].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[EvoParcOut], status_code=201)
async def bulk_insert(items: List[EvoParcIn]):
    if not items:
        return []
    docs = [i.model_dump(exclude_none=True, by_alias=True) for i in items]
    res = await db[COLL_EVOL_PARC].insert_many(docs)
    cursor = db[COLL_EVOL_PARC].find({"_id": {"$in": res.inserted_ids}})
    out = await cursor.to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=EvoParcOut)
async def update_doc(doc_id: str, payload: EvoParcUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = payload.model_dump(exclude_unset=True, by_alias=True)
    if data:
        await db[COLL_EVOL_PARC].update_one({"_id": _id}, {"$set": data})

    doc = await db[COLL_EVOL_PARC].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_doc(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_EVOL_PARC].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
