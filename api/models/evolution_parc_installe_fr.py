# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re

_NUM_CLEAN = re.compile(r"[^\d\-\.,]")  # оставляем цифры/знак/точку/запятую

def _to_int(v):
    if v is None or v == "": return None
    if isinstance(v, int): return v
    if isinstance(v, float): return int(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v.strip())
        try:
            return int(float(s.replace(",", ".")))
        except ValueError:
            return None
    return None

def _to_float(v):
    if v is None or v == "": return None
    if isinstance(v, (int, float)): return float(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v.strip()).replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return None
    return None


class EvoParcBase(BaseModel):
    """
    Запись из 'Évolution du parc installé de production d'électricité en France'
    """
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    year: Optional[int] = Field(default=None, alias="Date")        # Год (в БД поле называется 'Date')
    filiere: Optional[str] = Field(default=None, alias="Filière")  # Технология
    valeur_gw: Optional[float] = Field(default=None, alias="Valeur (GW)")  # Мощность, ГВт

    @field_validator("year", mode="before")
    @classmethod
    def _parse_year(cls, v):
        return _to_int(v)

    @field_validator("valeur_gw", mode="before")
    @classmethod
    def _parse_val(cls, v):
        return _to_float(v)


class EvoParcIn(EvoParcBase):
    pass


class EvoParcOut(EvoParcBase):
    id: str = Field(alias="_id")


class EvoParcUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    year: Optional[int] = Field(default=None, alias="Date")
    filiere: Optional[str] = Field(default=None, alias="Filière")
    valeur_gw: Optional[float] = Field(default=None, alias="Valeur (GW)")

    @field_validator("year", mode="before")
    @classmethod
    def _parse_year(cls, v):
        return _to_int(v)

    @field_validator("valeur_gw", mode="before")
    @classmethod
    def _parse_val(cls, v):
        return _to_float(v)
