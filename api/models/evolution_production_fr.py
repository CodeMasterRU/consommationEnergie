# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

_NUM_CLEAN = re.compile(r"[^\d\-\.,]")

def _to_float(v):
    if v is None or v == "": return None
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v.strip()).replace(",", ".")
        try:    return float(s)
        except: return None
    return None

class ProdFrBase(BaseModel):
    """
    Документ из коллекции 'Évolution de la production d’électricité en France'.
    Сохраняем исходные французские поля через alias.
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    date: Optional[str] = Field(None, alias="Date")               # "YYYY" или "YYYY-MM"
    filiere: Optional[str] = Field(None, alias="Filière")         # например: "Nucléaire"
    valeur_twh: Optional[float] = Field(None, alias="Valeur (TWh)")
    nature: Optional[str] = Field(None, alias="Nature")           # "Données Consolidées", ...

    # приведение чисел вида "229,582" -> 229.582
    @field_validator("valeur_twh", mode="before")
    @classmethod
    def _parse_float(cls, v):
        return _to_float(v)

class ProdFrIn(ProdFrBase):
    pass

class ProdFrOut(ProdFrBase):
    id: str = Field(alias="_id")

class ProdFrUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")
    date: Optional[str] = Field(None, alias="Date")
    filiere: Optional[str] = Field(None, alias="Filière")
    valeur_twh: Optional[float] = Field(None, alias="Valeur (TWh)")
    nature: Optional[str] = Field(None, alias="Nature")

    @field_validator("valeur_twh", mode="before")
    @classmethod
    def _parse_float(cls, v):
        return _to_float(v)
