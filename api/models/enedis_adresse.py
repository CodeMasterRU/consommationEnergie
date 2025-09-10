# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

_NUM_CLEAN = re.compile(r"[^\d\-\.,]")  # убираем всё кроме цифр/знака/точки/запятой


def _to_int(v):
    if v is None or v == "":
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        s = _NUM_CLEAN.sub("", s).replace(",", ".")
        try:
            # длинные коды как строки → приводим к int
            return int(float(s))
        except ValueError:
            return None
    return None


def _to_float(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v.strip()).replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


class AdresseBase(BaseModel):
    """Единая запись из enedis_adresse_data."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    annee: Optional[int] = None

    # ВАЖНО: code_iris числовой
    code_iris: Optional[int] = None
    nom_iris: Optional[str] = None

    numero_de_voie: Optional[int] = None
    type_de_voie: Optional[str] = None
    libelle_de_voie: Optional[str] = None

    code_commune: Optional[int] = None
    nom_commune: Optional[str] = None

    segment_de_client: Optional[str] = None
    nombre_de_logements: Optional[int] = None

    # Потребление (МВт·ч)
    consommation_annuelle_totale_de_l_adresse_mwh: Optional[float] = None
    consommation_annuelle_moyenne_par_site_de_l_adresse_mwh: Optional[float] = None
    consommation_annuelle_moyenne_de_la_commune_mwh: Optional[float] = None

    adresse: Optional[str] = None

    code_epci: Optional[int] = None
    code_departement: Optional[int] = None
    code_region: Optional[int] = None

    tri_des_adresses: Optional[int] = None

    # Парсинг целых чисел (добавлен code_iris)
    @field_validator(
        "annee", "code_iris", "numero_de_voie", "code_commune", "nombre_de_logements",
        "code_epci", "code_departement", "code_region", "tri_des_adresses",
        mode="before",
    )
    @classmethod
    def _parse_ints(cls, v):
        return _to_int(v)

    # Парсинг чисел с плавающей точкой
    @field_validator(
        "consommation_annuelle_totale_de_l_adresse_mwh",
        "consommation_annuelle_moyenne_par_site_de_l_adresse_mwh",
        "consommation_annuelle_moyenne_de_la_commune_mwh",
        mode="before",
    )
    @classmethod
    def _parse_floats(cls, v):
        return _to_float(v)


class AdresseIn(AdresseBase):
    pass


class AdresseOut(AdresseBase):
    id: str = Field(alias="_id")


class AdresseUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    annee: Optional[int] = None
    code_iris: Optional[int] = None
    nom_iris: Optional[str] = None

    numero_de_voie: Optional[int] = None
    type_de_voie: Optional[str] = None
    libelle_de_voie: Optional[str] = None

    code_commune: Optional[int] = None
    nom_commune: Optional[str] = None

    segment_de_client: Optional[str] = None
    nombre_de_logements: Optional[int] = None

    consommation_annuelle_totale_de_l_adresse_mwh: Optional[float] = None
    consommation_annuelle_moyenne_par_site_de_l_adresse_mwh: Optional[float] = None
    consommation_annuelle_moyenne_de_la_commune_mwh: Optional[float] = None

    adresse: Optional[str] = None

    code_epci: Optional[int] = None
    code_departement: Optional[int] = None
    code_region: Optional[int] = None
    tri_des_adresses: Optional[int] = None

    @field_validator(
        "annee", "code_iris", "numero_de_voie", "code_commune", "nombre_de_logements",
        "code_epci", "code_departement", "code_region", "tri_des_adresses",
        mode="before",
    )
    @classmethod
    def _parse_ints(cls, v):
        return _to_int(v)

    @field_validator(
        "consommation_annuelle_totale_de_l_adresse_mwh",
        "consommation_annuelle_moyenne_par_site_de_l_adresse_mwh",
        "consommation_annuelle_moyenne_de_la_commune_mwh",
        mode="before",
    )
    @classmethod
    def _parse_floats(cls, v):
        return _to_float(v)
