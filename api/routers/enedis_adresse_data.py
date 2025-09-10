# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.enedis_adresse import AdresseIn, AdresseOut, AdresseUpdate

COLL_ADRESSE = "enedis_adresse_data"
router = APIRouter(prefix="/addresses", tags=["Addresses (enedis_adresse_data)"])

ALLOWED_DISTINCT_FIELDS = {
    "annee",
    "code_iris", "nom_iris",
    "code_commune", "nom_commune",
    "code_departement", "code_region", "code_epci",
    "segment_de_client", "type_de_voie",
}

def _num_or_str(v: str | int):
    """Коды иногда как строки/числа — подстрахуемся в фильтре."""
    try:
        return int(v)
    except Exception:
        return v

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# --------- DEBUG ----------
@router.get("/debug/one", response_model=AdresseOut)
async def debug_one():
    doc = await db[COLL_ADRESSE].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

@router.get("/_debug")
async def _debug():
    n = await db[COLL_ADRESSE].count_documents({})
    return {"collection": COLL_ADRESSE, "count": n}


# --------- LIST ----------
@router.get("", response_model=List[AdresseOut], summary="Liste d'adresses avec filtres")
async def list_addresses(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="exemples: annee,-consommation_annuelle_totale_de_l_adresse_mwh"),

    annee: Optional[int] = Query(None),
    code_region: Optional[str] = Query(None),
    code_departement: Optional[str] = Query(None),
    code_commune: Optional[str] = Query(None),
    code_epci: Optional[str] = Query(None),
    code_iris: Optional[str] = Query(None),
    nom_commune: Optional[str] = Query(None),
    segment_de_client: Optional[str] = Query(None),
):
    q: Dict[str, Any] = {}

    if annee is not None:
        q["annee"] = annee
    if code_region:
        q["$or"] = q.get("$or", []) + [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]
    if code_departement:
        q["$or"] = q.get("$or", []) + [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]
    if code_commune:
        q["$or"] = q.get("$or", []) + [{"code_commune": code_commune}, {"code_commune": _num_or_str(code_commune)}]
    if code_epci:
        q["$or"] = q.get("$or", []) + [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]
    if code_iris:
        q["code_iris"] = code_iris
    if nom_commune:
        q["nom_commune"] = nom_commune
    if segment_de_client:
        q["segment_de_client"] = segment_de_client

    # если OR есть, а прямых полей нет — оставляем как есть
    if "$or" in q and len(q) > 1:
        # завернём все прямые в $and
        ands = []
        ors = q.pop("$or")
        for k, v in list(q.items()):
            ands.append({k: v})
            q.pop(k)
        q["$and"] = ands + [{"$or": ors}]

    cursor = db[COLL_ADRESSE].find(q)

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


# --------- SAMPLE ----------
@router.get("/sample", response_model=List[AdresseOut], summary="N exemples (aperçu rapide)")
async def sample_addresses(
    limit: int = Query(3, ge=1, le=50),
    annee: Optional[int] = None,
    code_commune: Optional[str] = None,
    nom_commune: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if annee is not None:
        q["annee"] = annee
    if code_commune:
        q["$or"] = [{"code_commune": code_commune}, {"code_commune": _num_or_str(code_commune)}]
    if nom_commune:
        q["nom_commune"] = nom_commune

    docs = await db[COLL_ADRESSE].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# --------- DISTINCT ----------
@router.get("/distinct", summary="Valeurs de data uniques")
async def distinct_values(field: str):
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Champ invalide '{field}'")
    vals = await db[COLL_ADRESSE].distinct(field)
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))


# --------- COUNT ----------
@router.get("/count")
async def count_addresses(
    annee: Optional[int] = None,
    code_region: Optional[str] = None,
    code_departement: Optional[str] = None,
    code_commune: Optional[str] = None,
    code_epci: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if annee is not None: q["annee"] = annee
    ors = []
    if code_region: ors += [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]
    if code_departement: ors += [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]
    if code_commune: ors += [{"code_commune": code_commune}, {"code_commune": _num_or_str(code_commune)}]
    if code_epci: ors += [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]
    if ors:
        q = {"$and": [{"$or": ors}] } if q else {"$or": ors}

    n = await db[COLL_ADRESSE].count_documents(q)
    return {"count": n, "query": q}


# --------- BY _id ----------
@router.get("/{doc_id}", response_model=AdresseOut, summary="Document par ObjectId")
async def get_by_id(doc_id: str = Path(..., description="24 hex ObjectId")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_ADRESSE].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# --------- CREATE ----------
@router.post("", response_model=AdresseOut, status_code=201)
async def create_adresse(payload: AdresseIn):
    res = await db[COLL_ADRESSE].insert_one(payload.model_dump(by_alias=True, exclude_none=True))
    doc = await db[COLL_ADRESSE].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# --------- BULK ----------
@router.post("/bulk", response_model=List[AdresseOut], status_code=201)
async def bulk_insert(items: List[AdresseIn]):
    if not items:
        return []
    docs = [i.model_dump(by_alias=True, exclude_none=True) for i in items]
    res = await db[COLL_ADRESSE].insert_many(docs)
    out = await db[COLL_ADRESSE].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# --------- PATCH ----------
@router.patch("/{doc_id}", response_model=AdresseOut)
async def update_adresse(doc_id: str, payload: AdresseUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = {k: v for k, v in payload.model_dump(by_alias=True, exclude_unset=True).items()}
    if data:
        await db[COLL_ADRESSE].update_one({"_id": _id}, {"$set": data})

    doc = await db[COLL_ADRESSE].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# --------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_adresse(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_ADRESSE].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
