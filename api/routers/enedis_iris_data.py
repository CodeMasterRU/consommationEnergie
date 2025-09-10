from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.enedis_iris import IrisIn, IrisOut, IrisUpdate

COLL_IRIS = "enedis_iris_data"
router = APIRouter(prefix="/iris", tags=["IRIS"])

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
@router.get("/debug/one", response_model=IrisOut)
async def debug_one():
    doc = await db[COLL_IRIS].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

# ---------- LIST ----------
@router.get("", response_model=List[IrisOut])
async def list_iris(
    annee: Optional[int] = Query(None),
    code_iris: Optional[str] = Query(None),
    code_commune: Optional[str] = Query(None),
    code_epci: Optional[str] = Query(None),
    code_departement: Optional[str] = Query(None),
    code_region: Optional[str] = Query(None),
    code_categorie_consommation: Optional[str] = Query(None),
    code_grand_secteur: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Exemple: 'annee,-conso_totale_mwh'"),
):
    ands: List[Dict[str, Any]] = []
    if annee is not None: ands.append({"annee": annee})
    if code_iris:        ands.append({"$or": [{"code_iris": code_iris}, {"code_iris": _num_or_str(code_iris)}]})
    if code_commune:     ands.append({"$or": [{"code_commune": code_commune}, {"code_commune": _num_or_str(code_commune)}]})
    if code_epci:        ands.append({"$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]})
    if code_departement: ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    if code_region:      ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_categorie_consommation:
        ands.append({"code_categorie_consommation": code_categorie_consommation})
    if code_grand_secteur:
        ands.append({"code_grand_secteur": code_grand_secteur})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    cursor = db[COLL_IRIS].find(q)

    if sort:
        spec = []
        for part in sort.split(","):
            p = part.strip()
            if not p: continue
            spec.append((p[1:], DESCENDING) if p.startswith("-") else (p, ASCENDING))
        if spec:
            cursor = cursor.sort(spec)

    docs = await cursor.skip(offset).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]

# ---------- SAMPLE ----------
@router.get("/sample", response_model=List[IrisOut])
async def sample_iris(
    limit: int = Query(3, ge=1, le=50),
    annee: Optional[int] = Query(None),
    code_iris: Optional[str] = Query(None),
    code_commune: Optional[str] = Query(None),
    code_epci: Optional[str] = Query(None),
    code_departement: Optional[str] = Query(None),
    code_region: Optional[str] = Query(None),
):
    ands: List[Dict[str, Any]] = []
    if annee is not None: ands.append({"annee": annee})
    if code_iris:        ands.append({"$or": [{"code_iris": code_iris}, {"code_iris": _num_or_str(code_iris)}]})
    if code_commune:     ands.append({"$or": [{"code_commune": code_commune}, {"code_commune": _num_or_str(code_commune)}]})
    if code_epci:        ands.append({"$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]})
    if code_departement: ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    if code_region:      ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    docs = await db[COLL_IRIS].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]

# ---------- DISTINCT ----------
ALLOWED_DISTINCT_FIELDS = {
    "annee",
    "code_iris", "nom_iris", "type_iris",
    "code_commune", "nom_commune",
    "code_epci", "nom_epci", "type_epci",
    "code_departement", "nom_departement",
    "code_region", "nom_region",
    "code_categorie_consommation",
    "code_grand_secteur",
    "code_secteur_naf2",
}

@router.get("/distinct", response_model=List[Any])
async def distinct_values(field: str = Query(..., description="exemple: code_iris | code_commune | code_region | ...")):
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"data invalid '{field}'")
    vals = await db[COLL_IRIS].distinct(field)
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))

# ---------- COUNT ----------
@router.get("/count")
async def count_iris(
    annee: Optional[int] = None,
    code_region: Optional[str] = None,
    code_departement: Optional[str] = None,
):
    ands: List[Dict[str, Any]] = []
    if annee is not None: ands.append({"annee": annee})
    if code_region:      ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_departement: ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    q = {"$and": ands} if ands else {}
    n = await db[COLL_IRIS].count_documents(q)
    return {"count": n, "query": q}

# ---------- BY KEY (annee + code_iris) ----------
@router.get("/by_key/{annee}/{code_iris}", response_model=IrisOut)
async def get_by_key(annee: int, code_iris: str = Path(..., description="nombre ou ligne")):
    doc = await db[COLL_IRIS].find_one({
        "annee": annee,
        "$or": [{"code_iris": code_iris}, {"code_iris": _num_or_str(code_iris)}],
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=IrisOut)
async def get_iris(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_IRIS].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- CREATE ----------
@router.post("", response_model=IrisOut, status_code=201)
async def create_iris(payload: IrisIn):
    res = await db[COLL_IRIS].insert_one(payload.model_dump(exclude_none=True))
    doc = await db[COLL_IRIS].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)

# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[IrisOut], status_code=201)
async def bulk_insert(items: List[IrisIn]):
    if not items:
        return []
    docs = [i.model_dump(exclude_none=True) for i in items]
    res = await db[COLL_IRIS].insert_many(docs)
    out = await db[COLL_IRIS].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]

# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=IrisOut)
async def update_iris(doc_id: str, payload: IrisUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if data:
        await db[COLL_IRIS].update_one({"_id": _id}, {"$set": data})
    doc = await db[COLL_IRIS].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_iris(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_IRIS].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
