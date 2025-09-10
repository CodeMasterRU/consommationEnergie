from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.evolution_production_fr import ProdFrIn, ProdFrOut, ProdFrUpdate

# ВАЖНО: поставь точное имя коллекции как в MongoDB.
# Если у тебя другой идентификатор — поменяй строку ниже.
COLL_PROD_FR = "Évolution de la production d'électricité en France"

# Ключи в БД (фр. названия полей)
K_DATE = "Date"
K_FILIERE = "Filière"
K_VALEUR = "Valeur (TWh)"
K_NATURE = "Nature"

router = APIRouter(prefix="/prod_evolution", tags=["Production • France (évolution)"])

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

# ---------- DEBUG ----------
@router.get("/debug/one", response_model=ProdFrOut)
async def debug_one():
    doc = await db[COLL_PROD_FR].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

# ---------- LIST ----------
@router.get("", response_model=List[ProdFrOut])
async def list_prod_fr(
    filiere: Optional[str] = Query(None),
    nature: Optional[str] = Query(None),
    date: Optional[str] = Query(None, description="Filtrer par date exacte (AAAA ou AAAA-MM)"),
    annee: Optional[int] = Query(None, description="Année : filtrera la date par préfixe ^AAAA"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="ex.: 'Date,-Valeur (TWh)' (par noms d'origine ou alias)"),
):
    q: Dict[str, Any] = {}
    if filiere: q[K_FILIERE] = filiere
    if nature:  q[K_NATURE]  = nature
    if date:    q[K_DATE]    = date
    if annee is not None:
        q[K_DATE] = {"$regex": f"^{annee}"}

    cursor = db[COLL_PROD_FR].find(q)

    if sort:
        # принимаем имена полей как alias ("date", "valeur_twh") и как исходные ("Date", "Valeur (TWh)")
        mapping = {
            "date": K_DATE,
            "filiere": K_FILIERE,
            "valeur_twh": K_VALEUR,
            "nature": K_NATURE,
            K_DATE: K_DATE, K_FILIERE: K_FILIERE, K_VALEUR: K_VALEUR, K_NATURE: K_NATURE
        }
        spec = []
        for part in sort.split(","):
            p = part.strip()
            if not p: 
                continue
            desc = p.startswith("-")
            key = p[1:] if desc else p
            key = mapping.get(key, key)
            spec.append((key, DESCENDING if desc else ASCENDING))
        if spec:
            cursor = cursor.sort(spec)

    docs = await cursor.skip(offset).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]

# ---------- SAMPLE ----------
@router.get("/sample", response_model=List[ProdFrOut])
async def sample_prod_fr(
    limit: int = Query(3, ge=1, le=50),
    filiere: Optional[str] = None,
    annee: Optional[int] = None,
):
    q: Dict[str, Any] = {}
    if filiere: q[K_FILIERE] = filiere
    if annee is not None: q[K_DATE] = {"$regex": f"^{annee}"}
    docs = await db[COLL_PROD_FR].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]

# ---------- DISTINCT ----------
_ALLOWED_DISTINCT = {"date", "filiere", "nature", "annee"}

@router.get("/distinct", response_model=List[Any])
async def distinct_values(field: str = Query(..., description="date|filiere|nature|annee")):
    if field not in _ALLOWED_DISTINCT:
        raise HTTPException(status_code=400, detail=f"Data invalid'{field}'")

    if field == "date":
        vals = await db[COLL_PROD_FR].distinct(K_DATE)
        return sorted([v for v in vals if v is not None], key=str)

    if field == "filiere":
        vals = await db[COLL_PROD_FR].distinct(K_FILIERE)
        return sorted([v for v in vals if v is not None], key=str)

    if field == "nature":
        vals = await db[COLL_PROD_FR].distinct(K_NATURE)
        return sorted([v for v in vals if v is not None], key=str)

    # field == "annee": берём distinct по Date, извлекаем первые 4 символа
    dates = await db[COLL_PROD_FR].distinct(K_DATE)
    years = sorted({d[:4] for d in dates if isinstance(d, str) and len(d) >= 4})
    # вернём числа где возможно
    def _to_int(s):
        try: return int(s)
        except: return s
    return sorted((_to_int(y) for y in years), key=lambda x: (isinstance(x, str), x))

# ---------- COUNT ----------
@router.get("/count")
async def count_prod_fr(
    filiere: Optional[str] = None,
    annee: Optional[int] = None,
):
    q: Dict[str, Any] = {}
    if filiere: q[K_FILIERE] = filiere
    if annee is not None: q[K_DATE] = {"$regex": f"^{annee}"}
    n = await db[COLL_PROD_FR].count_documents(q)
    return {"count": n, "query": q}

# ---------- GET BY _id ----------
@router.get("/{doc_id}", response_model=ProdFrOut)
async def get_by_id(doc_id: str = Path(..., description="Mongo ObjectId (24 hex)")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    doc = await db[COLL_PROD_FR].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- CREATE ----------
@router.post("", response_model=ProdFrOut, status_code=201)
async def create_item(payload: ProdFrIn):
    res = await db[COLL_PROD_FR].insert_one(payload.model_dump(by_alias=True, exclude_none=True))
    doc = await db[COLL_PROD_FR].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)

# ---------- BULK INSERT ----------
@router.post("/bulk", response_model=List[ProdFrOut], status_code=201)
async def bulk_insert(items: List[ProdFrIn]):
    if not items:
        return []
    docs = [i.model_dump(by_alias=True, exclude_none=True) for i in items]
    res = await db[COLL_PROD_FR].insert_many(docs)
    out = await db[COLL_PROD_FR].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]

# ---------- PATCH ----------
@router.patch("/{doc_id}", response_model=ProdFrOut)
async def update_item(doc_id: str, payload: ProdFrUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    data = payload.model_dump(by_alias=True, exclude_unset=True)
    if data:
        await db[COLL_PROD_FR].update_one({"_id": _id}, {"$set": data})
    doc = await db[COLL_PROD_FR].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)

# ---------- DELETE ----------
@router.delete("/{doc_id}", status_code=204)
async def delete_item(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    res = await db[COLL_PROD_FR].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
