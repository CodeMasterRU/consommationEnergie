# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.eco2mix_national import (
    Eco2mixIn, Eco2mixOut, Eco2mixUpdate
)

COLL_ECO2MIX = "eco2mix-national-tr"

router = APIRouter(prefix="/eco2mix", tags=["Eco2mix national"])

ALLOWED_DISTINCT_FIELDS = {
    "perimetre", "nature", "heure"
}

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        # pydantic/py can парсить ISO со смещением
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


# ---------- DEBUG ----------
@router.get("/debug/one", response_model=Eco2mixOut)
async def debug_one():
    doc = await db[COLL_ECO2MIX].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

@router.get("/_debug")
async def _debug():
    n = await db[COLL_ECO2MIX].count_documents({})
    return {"collection": COLL_ECO2MIX, "count": n}


# ---------- LIST ----------
@router.get("", response_model=List[Eco2mixOut])
async def list_eco2mix(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Exemple: date_heure,-consommation"),
    perimetre: Optional[str] = Query(None),
    nature: Optional[str] = Query(None),
    heure: Optional[str] = Query(None, description="Filtrer par heure si stocké sous forme de chaîne, par exemple '02:30'"),
    date_from: Optional[str] = Query(None, description="Chaîne ISO, filtre date_heure >= ..."),
    date_to: Optional[str] = Query(None, description="Chaîne ISO, filtre date_heure < ..."),
):
    q: Dict[str, Any] = {}
    if perimetre: q["perimetre"] = perimetre
    if nature: q["nature"] = nature
    if heure: q["heure"] = heure

    dt_from = _parse_dt(date_from)
    dt_to = _parse_dt(date_to)
    if dt_from or dt_to:
        rng: Dict[str, Any] = {}
        if dt_from: rng["$gte"] = dt_from
        if dt_to: rng["$lt"] = dt_to
        q["date_heure"] = rng

    cursor = db[COLL_ECO2MIX].find(q)

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


# ---------- SAMPLE ----------
@router.get("/sample", response_model=List[Eco2mixOut])
async def sample_eco2mix(
    limit: int = Query(3, ge=1, le=50),
    perimetre: Optional[str] = None,
    nature: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if perimetre: q["perimetre"] = perimetre
    if nature: q["nature"] = nature
    docs = await db[COLL_ECO2MIX].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- DISTINCT ----------
@router.get("/distinct", summary="Valeurs de data uniques")
async def distinct_values(field: str):
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Donnée invalide '{field}'")
    vals = await db[COLL_ECO2MIX].distinct(field)
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))


# ---------- COUNT ----------
@router.get("/count")
async def count_eco2mix(
    perimetre: Optional[str] = None,
    nature: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if perimetre: q["perimetre"] = perimetre
    if nature: q["nature"] = nature

    dt_from = _parse_dt(date_from)
    dt_to = _parse_dt(date_to)
    if dt_from or dt_to:
        rng: Dict[str, Any] = {}
        if dt_from: rng["$gte"] = dt_from
        if dt_to: rng["$lt"] = dt_to
        q["date_heure"] = rng

    n = await db[COLL_ECO2MIX].count_documents(q)
    return {"count": n, "query": q}


# ---------- BY _id ----------
@router.get("/{doc_id}", response_model=Eco2mixOut)
async def get_eco2mix(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_ECO2MIX].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- CREATE ----------
@router.post("", response_model=Eco2mixOut, status_code=201)
async def create_eco2mix(payload: Eco2mixIn):
    res = await db[COLL_ECO2MIX].insert_one(payload.model_dump(by_alias=True, exclude_none=True))
    doc = await db[COLL_ECO2MIX].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[Eco2mixOut], status_code=201)
async def bulk_insert(items: List[Eco2mixIn]):
    if not items:
        return []
    docs = [i.model_dump(by_alias=True, exclude_none=True) for i in items]
    res = await db[COLL_ECO2MIX].insert_many(docs)
    out = await db[COLL_ECO2MIX].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=Eco2mixOut)
async def update_eco2mix(doc_id: str, payload: Eco2mixUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = {k: v for k, v in payload.model_dump(by_alias=True, exclude_unset=True).items()}
    if data:
        await db[COLL_ECO2MIX].update_one({"_id": _id}, {"$set": data})

    doc = await db[COLL_ECO2MIX].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_eco2mix(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_ECO2MIX].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
