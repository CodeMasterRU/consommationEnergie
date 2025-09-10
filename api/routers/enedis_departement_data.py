from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.enedis_departement import (
    DepartementIn, DepartementOut, DepartementUpdate
)

COLL_DEPT = "enedis_departement_data"
router = APIRouter(prefix="/departements", tags=["Departements"])

def _num_or_str(v: str | int):
    try:
        return int(v)
    except Exception:
        return v

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# ---------- DEBUG ----------
@router.get("/debug/one", response_model=DepartementOut)
async def debug_one():
    doc = await db[COLL_DEPT].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

# ---------- LIST ----------
@router.get("", response_model=List[DepartementOut])
async def list_departements(
    annee: Optional[int] = Query(None),
    code_departement: Optional[str] = Query(None),
    nom_departement: Optional[str] = Query(None),
    code_region: Optional[str] = Query(None),
    nom_region: Optional[str] = Query(None),
    code_categorie_consommation: Optional[str] = Query(None),
    code_grand_secteur: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="exemple: 'annee,-conso_totale_mwh'"),
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_departement:
        ands.append({"$or": [
            {"code_departement": code_departement},
            {"code_departement": _num_or_str(code_departement)}
        ]})
    if nom_departement:
        ands.append({"nom_departement": nom_departement})
    if code_region:
        ands.append({"$or": [
            {"code_region": code_region},
            {"code_region": _num_or_str(code_region)}
        ]})
    if nom_region:
        ands.append({"nom_region": nom_region})
    if code_categorie_consommation:
        ands.append({"code_categorie_consommation": code_categorie_consommation})
    if code_grand_secteur:
        ands.append({"code_grand_secteur": code_grand_secteur})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    cursor = db[COLL_DEPT].find(q)

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
@router.get("/sample", response_model=List[DepartementOut])
async def sample_departements(
    limit: int = Query(3, ge=1, le=50),
    annee: Optional[int] = Query(None),
    code_departement: Optional[str] = Query(None),
    code_region: Optional[str] = Query(None),
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_departement:
        ands.append({"$or": [
            {"code_departement": code_departement},
            {"code_departement": _num_or_str(code_departement)}
        ]})
    if code_region:
        ands.append({"$or": [
            {"code_region": code_region},
            {"code_region": _num_or_str(code_region)}
        ]})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    docs = await db[COLL_DEPT].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]

# ---------- DISTINCT ----------
ALLOWED_DISTINCT_FIELDS = {
    "annee",
    "code_departement", "nom_departement",
    "code_region", "nom_region",
    "code_categorie_consommation",
    "code_grand_secteur",
    "code_secteur_naf2",
}

@router.get("/distinct", response_model=List[Any])
async def distinct_values(field: str = Query(..., description="exemple: code_departement | nom_departement | code_region | ...")):
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Champ invalide '{field}'")
    vals = await db[COLL_DEPT].distinct(field)
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))

# ---------- COUNT ----------
@router.get("/count")
async def count_departements(
    annee: Optional[int] = None,
    code_region: Optional[str] = None,
    code_departement: Optional[str] = None,
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_departement:
        ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    q = {"$and": ands} if ands else {}
    n = await db[COLL_DEPT].count_documents(q)
    return {"count": n, "query": q}

# ---------- BY KEY (annee + code_departement) ----------
@router.get("/by_key/{annee}/{code_departement}", response_model=DepartementOut)
async def get_by_key(annee: int, code_departement: str = Path(..., description="nombre ou chaîne")):
    doc = await db[COLL_DEPT].find_one({
        "annee": annee,
        "$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}],
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=DepartementOut)
async def get_departement(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_DEPT].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- CREATE ----------
@router.post("", response_model=DepartementOut, status_code=201)
async def create_departement(payload: DepartementIn):
    res = await db[COLL_DEPT].insert_one(payload.model_dump(exclude_none=True))
    doc = await db[COLL_DEPT].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)

# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[DepartementOut], status_code=201)
async def bulk_insert(items: List[DepartementIn]):
    if not items:
        return []
    docs = [i.model_dump(exclude_none=True) for i in items]
    res = await db[COLL_DEPT].insert_many(docs)
    out = await db[COLL_DEPT].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]

# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=DepartementOut)
async def update_departement(doc_id: str, payload: DepartementUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if data:
        await db[COLL_DEPT].update_one({"_id": _id}, {"$set": data})
    doc = await db[COLL_DEPT].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_departement(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_DEPT].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
