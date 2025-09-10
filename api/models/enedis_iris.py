# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

_NUM_CLEAN = re.compile(r"[^\d\-\.,]")  # оставляем цифры/знак/точку/запятую

def _to_int(v):
    if v is None or v == "": return None
    if isinstance(v, int):    return v
    if isinstance(v, float):  return int(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v.strip()).replace(",", ".")
        try:    return int(float(s))
        except: return None
    return None

def _to_float(v):
    if v is None or v == "": return None
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v.strip()).replace(",", ".")
        try:    return float(s)
        except: return None
    return None


class IrisBase(BaseModel):
    """Запись из enedis_iris_data (уровень IRIS)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    annee: Optional[int] = None

    code_iris: Optional[int] = None
    nom_iris: Optional[str] = None
    type_iris: Optional[str] = None

    code_commune: Optional[int] = None
    nom_commune: Optional[str] = None

    code_epci: Optional[int] = None
    nom_epci: Optional[str] = None
    type_epci: Optional[str] = None

    code_departement: Optional[int] = None
    nom_departement: Optional[str] = None

    code_region: Optional[int] = None
    nom_region: Optional[str] = None

    code_categorie_consommation: Optional[str] = None  # ENT/PRO/…
    code_grand_secteur: Optional[str] = None          # INDUSTRIE/TERTIAIRE/INCONNU …
    code_secteur_naf2: Optional[int] = None

    nb_sites: Optional[int] = None
    conso_totale_mwh: Optional[float] = None
    conso_moyenne_mwh: Optional[float] = None

    geo_point_2d: Optional[str] = None  # как в БД: строка '{"lon":..,"lat":..}'

    @field_validator(
        "annee", "code_iris", "code_commune", "code_epci",
        "code_departement", "code_region", "code_secteur_naf2", "nb_sites",
        mode="before",
    )
    @classmethod
    def _parse_ints(cls, v):
        return _to_int(v)

    @field_validator("conso_totale_mwh", "conso_moyenne_mwh", mode="before")
    @classmethod
    def _parse_floats(cls, v):
        return _to_float(v)


class IrisIn(IrisBase):
    pass


class IrisOut(IrisBase):
    id: str = Field(alias="_id")


class IrisUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    annee: Optional[int] = None
    code_iris: Optional[int] = None
    nom_iris: Optional[str] = None
    type_iris: Optional[str] = None

    code_commune: Optional[int] = None
    nom_commune: Optional[str] = None

    code_epci: Optional[int] = None
    nom_epci: Optional[str] = None
    type_epci: Optional[str] = None

    code_departement: Optional[int] = None
    nom_departement: Optional[str] = None

    code_region: Optional[int] = None
    nom_region: Optional[str] = None

    code_categorie_consommation: Optional[str] = None
    code_grand_secteur: Optional[str] = None
    code_secteur_naf2: Optional[int] = None

    nb_sites: Optional[int] = None
    conso_totale_mwh: Optional[float] = None
    conso_moyenne_mwh: Optional[float] = None

    geo_point_2d: Optional[str] = None

    @field_validator(
        "annee", "code_iris", "code_commune", "code_epci",
        "code_departement", "code_region", "code_secteur_naf2", "nb_sites",
        mode="before",
    )
    @classmethod
    def _parse_ints(cls, v):
        return _to_int(v)

    @field_validator("conso_totale_mwh", "conso_moyenne_mwh", mode="before")
    @classmethod
    def _parse_floats(cls, v):
        return _to_float(v)
