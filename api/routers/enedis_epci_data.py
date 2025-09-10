# api/routers/enedis_epci_data.py
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.enedis_epci import EPCIIn, EPCIOut, EPCIUpdate

router = APIRouter(prefix="/epci", tags=["EPCI"])
COLL_EPCI = "enedis_epci_data"

# Какие поля разрешено дергать в /distinct
ALLOWED_DISTINCT_FIELDS = {
    "annee",
    "code_region",
    "code_departement",
    "code_epci",
    "nom_epci",
    "nom_region",
    "nom_departement",
    "code_categorie_consommation",
    "code_grand_secteur",
}

def _num_or_str(v: str | int):
    """Пробуем привести к int, иначе оставляем строкой (на случай разнородных типов в БД)."""
    try:
        return int(v)
    except Exception:
        return v

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    """ObjectId -> str."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ---------- DEBUG ----------
@router.get("/debug/one", summary="Toute entrée sans filtres", response_model=EPCIOut)
async def debug_one():
    doc = await db[COLL_EPCI].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

@router.get("/_debug", summary="Debug")
async def _debug():
    n = await db[COLL_EPCI].count_documents({})
    return {"collection": COLL_EPCI, "count": n}


# ---------- LIST ----------
@router.get("/", summary="Liste des EPCI avec filtres", response_model=List[EPCIOut])
async def list_epci(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="exemple: annee,-conso_totale_mwh"),
    annee: Optional[int] = Query(None),
    code_region: Optional[str] = Query(None),
    code_departement: Optional[str] = Query(None),
    code_epci: Optional[str] = Query(None),
):
    # Собираем AND из переданных условий, в кодах допускаем как str, так и int
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_departement:
        ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    if code_epci:
        ands.append({"$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    cursor = db[COLL_EPCI].find(q)

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
@router.get("/sample", summary="N exemples (aperçu rapide)", response_model=List[EPCIOut])
async def sample(
    limit: int = Query(3, ge=1, le=50),
    annee: Optional[int] = Query(None),
    code_region: Optional[str] = Query(None),
    code_departement: Optional[str] = Query(None),
    code_epci: Optional[str] = Query(None),
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_departement:
        ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    if code_epci:
        ands.append({"$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    docs = await db[COLL_EPCI].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# ---------- DISTINCT ----------
@router.get("/distinct", summary="Valeurs de champ uniques", response_model=List[Any])
async def distinct_values(
    field: str = Query(..., description="exemple: annee | code_region | code_epci | nom_epci ..."),
    annee: Optional[int] = None,
    code_region: Optional[str] = None,
    code_departement: Optional[str] = None,
    code_epci: Optional[str] = None,
):
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Champ invalide '{field}'")

    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_departement:
        ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    if code_epci:
        ands.append({"$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]})

    q: Dict[str, Any] = {"$and": ands} if ands else {}
    vals = await db[COLL_EPCI].distinct(field, filter=q)

    def _norm(v):
        try:
            return int(v)
        except Exception:
            return v

    return sorted((_norm(v) for v in vals), key=lambda x: (isinstance(x, str), x))


# ---------- COUNT ----------
@router.get("/count", summary="Combien y a-t-il de documents par filtre ?")
async def count_docs(
    annee: Optional[int] = None,
    code_region: Optional[str] = None,
    code_departement: Optional[str] = None,
    code_epci: Optional[str] = None,
):
    ands: List[Dict[str, Any]] = []
    if annee is not None:
        ands.append({"annee": annee})
    if code_region:
        ands.append({"$or": [{"code_region": code_region}, {"code_region": _num_or_str(code_region)}]})
    if code_departement:
        ands.append({"$or": [{"code_departement": code_departement}, {"code_departement": _num_or_str(code_departement)}]})
    if code_epci:
        ands.append({"$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}]})

    q = {"$and": ands} if ands else {}
    n = await db[COLL_EPCI].count_documents(q)
    return {"count": n, "query": q}


# ---------- BY KEY (annee + code_epci) ----------
@router.get("/by_key/{annee}/{code_epci}", response_model=EPCIOut)
async def get_by_key(annee: int, code_epci: str = Path(..., description="Code EPCI (numéro ou chaîne)")):
    doc = await db[COLL_EPCI].find_one({
        "annee": annee,
        "$or": [{"code_epci": code_epci}, {"code_epci": _num_or_str(code_epci)}],
    })
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=EPCIOut, summary="Document sur ObjectId")
async def by_id(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    doc = await db[COLL_EPCI].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- CREATE ----------
@router.post("/", response_model=EPCIOut, status_code=201, summary="Créer un EPCI")
async def create_epci(payload: EPCIIn):
    res = await db[COLL_EPCI].insert_one(payload.model_dump(exclude_none=True))
    doc = await db[COLL_EPCI].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[EPCIOut], status_code=201, summary="Téléchargement massif")
async def bulk_insert(items: List[EPCIIn]):
    if not items:
        return []
    docs = [i.model_dump(exclude_none=True) for i in items]
    res = await db[COLL_EPCI].insert_many(docs)
    cursor = db[COLL_EPCI].find({"_id": {"$in": res.inserted_ids}})
    out = await cursor.to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=EPCIOut, summary="Mise à jour EPCI")
async def update_epci(doc_id: str, payload: EPCIUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = {k: v for k, v in payload.model_dump(exclude_unset=True).items()}
    if data:
        await db[COLL_EPCI].update_one({"_id": _id}, {"$set": data})
    doc = await db[COLL_EPCI].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204, summary="Supprimer EPCI")
async def delete_epci(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_EPCI].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
