# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

# Иногда числа приходят как строки с запятыми или "ND".
_NUM_CLEAN = re.compile(r"[^\d\-\.,]")

def _to_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if s.upper() == "ND":
            return None
        s = _NUM_CLEAN.sub("", s).replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


class Eco2mixBase(BaseModel):
    """Modèle d'enregistrement de référence eco2mix (données nationales)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    perimetre: Optional[str] = None
    nature: Optional[str] = None

    # В коллекции обычно есть "date" и "date_heure"
    date: Optional[datetime] = None
    date_heure: Optional[datetime] = None

    # Иногда хранится и поле "heure" как строка "02:30"
    heure: Optional[str] = None

    # Показатели (все делаем float|None и парсим валидатором)
    consommation: Optional[float] = None
    prevision_j: Optional[float] = None
    prevision_j1: Optional[float] = None

    fioul: Optional[float] = None
    fioul_tac: Optional[float] = None
    fioul_cogen: Optional[float] = None
    fioul_autres: Optional[float] = None

    charbon: Optional[float] = None
    gaz: Optional[float] = None
    nucleaire: Optional[float] = None

    eolien: Optional[float] = None
    eolien_terrestre: Optional[float] = None
    eolien_offshore: Optional[float] = None
    solaire: Optional[float] = None

    hydraulique: Optional[float] = None
    pompage: Optional[float] = None
    bioenergies: Optional[float] = None

    ech_physiques: Optional[float] = None
    taux_co2: Optional[float] = None

    # Приводим все числовые поля к float
    @field_validator(
        "consommation", "prevision_j", "prevision_j1",
        "fioul", "fioul_tac", "fioul_cogen", "fioul_autres",
        "charbon", "gaz", "nucleaire",
        "eolien", "eolien_terrestre", "eolien_offshore", "solaire",
        "hydraulique", "pompage", "bioenergies",
        "ech_physiques", "taux_co2",
        mode="before"
    )
    @classmethod
    def _parse_numbers(cls, v):
        return _to_float(v)


class Eco2mixIn(Eco2mixBase):
    pass


class Eco2mixOut(Eco2mixBase):
    id: str = Field(alias="_id")


class Eco2mixUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    perimetre: Optional[str] = None
    nature: Optional[str] = None
    date: Optional[datetime] = None
    date_heure: Optional[datetime] = None
    heure: Optional[str] = None

    consommation: Optional[float] = None
    prevision_j: Optional[float] = None
    prevision_j1: Optional[float] = None

    fioul: Optional[float] = None
    fioul_tac: Optional[float] = None
    fioul_cogen: Optional[float] = None
    fioul_autres: Optional[float] = None

    charbon: Optional[float] = None
    gaz: Optional[float] = None
    nucleaire: Optional[float] = None

    eolien: Optional[float] = None
    eolien_terrestre: Optional[float] = None
    eolien_offshore: Optional[float] = None
    solaire: Optional[float] = None

    hydraulique: Optional[float] = None
    pompage: Optional[float] = None
    bioenergies: Optional[float] = None

    ech_physiques: Optional[float] = None
    taux_co2: Optional[float] = None

    @field_validator(
        "consommation", "prevision_j", "prevision_j1",
        "fioul", "fioul_tac", "fioul_cogen", "fioul_autres",
        "charbon", "gaz", "nucleaire",
        "eolien", "eolien_terrestre", "eolien_offshore", "solaire",
        "hydraulique", "pompage", "bioenergies",
        "ech_physiques", "taux_co2",
        mode="before"
    )
    @classmethod
    def _parse_numbers(cls, v):
        return _to_float(v)
