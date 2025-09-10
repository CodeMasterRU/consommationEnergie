# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Path
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from ..database import db
from ..models.major_installations import (
    MajorInstallIn,
    MajorInstallOut,
    MajorInstallUpdate,
)

# ВАЖНО: имя коллекции в MongoDB с точным написанием и диакритикой.
COLL_MAJOR = "Répartition des principales installations de production d'électricité en France, hors solaire et éolien"

router = APIRouter(prefix="/major_installs", tags=["Major installations"])

# Удобное сопоставление "дружелюбных" имён полей с именами в коллекции
FIELD_MAP = {
    "departement": "Département",
    "longitude": "Longitude",
    "latitude": "Latitude",
    "filiere": "Filière",
    "valeur_mw": "Valeur (MW)",
}

ALLOWED_DISTINCT_FIELDS = {
    "Département", "Filière", "Valeur (MW)",  # оригинальные
    "departement", "filiere", "valeur_mw",    # дружелюбные
}

def _db_field(name: str) -> str:
    """Преобразование дружелюбного имени поля в имя поля в коллекции."""
    return FIELD_MAP.get(name, name)

def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# -------- DEBUG --------
@router.get("/debug/one", response_model=MajorInstallOut, summary="Toute entrée sans filtres")
async def debug_one():
    doc = await db[COLL_MAJOR].find_one({})
    if not doc:
        raise HTTPException(status_code=404, detail="Collection is empty")
    return _to_str_id(doc)

@router.get("/_debug", summary="Contrôle technique : taille de la collection")
async def _debug():
    n = await db[COLL_MAJOR].count_documents({})
    return {"collection": COLL_MAJOR, "count": n}


# -------- LIST --------
@router.get("", response_model=List[MajorInstallOut], summary="Liste des grandes installations avec filtres")
async def list_major_installs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sort: Optional[str] = Query(None, description="Ex: filiere,-valeur_mw (ou noms de champs originaux)"),
    departement: Optional[str] = Query(None, description="Nom d'installation (stocké dans les données du champ « Département »)"),
    filiere: Optional[str] = Query(None, description="Ex: Nucléaire | Hydraulique | Gaz ..."),
):
    q: Dict[str, Any] = {}
    if departement:
        q[_db_field("departement")] = departement
    if filiere:
        q[_db_field("filiere")] = filiere

    cursor = db[COLL_MAJOR].find(q)

    # сортировка
    if sort:
        spec = []
        for part in sort.split(","):
            p = part.strip()
            if not p:
                continue
            desc = p.startswith("-")
            field = _db_field(p[1:] if desc else p)
            spec.append((field, DESCENDING if desc else ASCENDING))
        if spec:
            cursor = cursor.sort(spec)

    docs = await cursor.skip(offset).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# -------- SAMPLE --------
@router.get("/sample", response_model=List[MajorInstallOut], summary="N exemples (aperçu rapide)")
async def sample_major_installs(
    limit: int = Query(3, ge=1, le=50),
    departement: Optional[str] = None,
    filiere: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if departement:
        q[_db_field("departement")] = departement
    if filiere:
        q[_db_field("filiere")] = filiere

    docs = await db[COLL_MAJOR].find(q).limit(limit).to_list(length=limit)
    return [_to_str_id(d) for d in docs]


# -------- DISTINCT --------
@router.get("/distinct", summary="Valeurs de champ uniques")
async def distinct_values(field: str = Query(..., description="Exemples: departement | filiere | valeur_mw (ou noms originaux)")):
    # Разрешаем как «дружелюбные», так и оригинальные имена
    if field not in ALLOWED_DISTINCT_FIELDS:
        raise HTTPException(status_code=400, detail=f"Champ invalide: {field}")
    real_field = _db_field(field)
    vals = await db[COLL_MAJOR].distinct(real_field)
    return sorted([v for v in vals if v is not None], key=lambda x: str(x))


# -------- COUNT --------
@router.get("/count", summary="Combien y a-t-il de documents par filtre ?")
async def count_major_installs(
    departement: Optional[str] = None,
    filiere: Optional[str] = None,
):
    q: Dict[str, Any] = {}
    if departement:
        q[_db_field("departement")] = departement
    if filiere:
        q[_db_field("filiere")] = filiere

    n = await db[COLL_MAJOR].count_documents(q)
    return {"count": n, "query": q}


# -------- BY _id --------
@router.get("/{doc_id}", response_model=MajorInstallOut, summary="Document sur ObjectId")
async def get_by_id(doc_id: str = Path(..., description="24 caractères ObjectId")):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    doc = await db[COLL_MAJOR].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# -------- CREATE --------
@router.post("", response_model=MajorInstallOut, status_code=201, summary="Créer un article")
async def create_major_install(payload: MajorInstallIn):
    res = await db[COLL_MAJOR].insert_one(payload.model_dump(by_alias=True, exclude_none=True))
    doc = await db[COLL_MAJOR].find_one({"_id": res.inserted_id})
    return _to_str_id(doc)


# -------- BULK INSERT --------
@router.post("/bulk", response_model=List[MajorInstallOut], status_code=201, summary="Update par lots")
async def bulk_insert(items: List[MajorInstallIn]):
    if not items:
        return []
    docs = [i.model_dump(by_alias=True, exclude_none=True) for i in items]
    res = await db[COLL_MAJOR].insert_many(docs)
    out = await db[COLL_MAJOR].find({"_id": {"$in": res.inserted_ids}}).to_list(length=len(res.inserted_ids))
    return [_to_str_id(d) for d in out]


# -------- PATCH --------
@router.patch("/{doc_id}", response_model=MajorInstallOut, summary="Update partiel")
async def update_major_install(doc_id: str, payload: MajorInstallUpdate):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    data = {k: v for k, v in payload.model_dump(by_alias=True, exclude_unset=True).items()}
    if data:
        await db[COLL_MAJOR].update_one({"_id": _id}, {"$set": data})

    doc = await db[COLL_MAJOR].find_one({"_id": _id})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    return _to_str_id(doc)


# -------- DELETE --------
@router.delete("/{doc_id}", status_code=204, summary="Suppresion")
async def delete_major_install(doc_id: str):
    try:
        _id = ObjectId(doc_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")

    res = await db[COLL_MAJOR].delete_one({"_id": _id})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return None
