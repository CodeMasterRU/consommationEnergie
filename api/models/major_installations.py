# -*- coding: utf-8 -*-
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

# Числовые поля в исходных данных иногда приходят строками с запятой.
_NUM_CLEAN = re.compile(r"[^\d\-\.,]")

def _to_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = _NUM_CLEAN.sub("", v).replace(",", ".")
        try:
            return float(s)
        except ValueError:
            return v
    return v


class MajorInstallBase(BaseModel):
    """Базовая модель одной установки (крупные объекты, без солнечных и ветра)."""
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    departement: str = Field(alias="Département")
    longitude: float = Field(alias="Longitude")
    latitude: float = Field(alias="Latitude")
    filiere: str = Field(alias="Filière")
    valeur_mw: float = Field(alias="Valeur (MW)")

    @field_validator("longitude", "latitude", "valeur_mw", mode="before")
    @classmethod
    def _parse_numbers(cls, v):
        return _to_float(v)


class MajorInstallIn(MajorInstallBase):
    pass


class MajorInstallOut(MajorInstallBase):
    id: str = Field(alias="_id")


class MajorInstallUpdate(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    departement: Optional[str] = Field(None, alias="Département")
    longitude: Optional[float] = Field(None, alias="Longitude")
    latitude: Optional[float] = Field(None, alias="Latitude")
    filiere: Optional[str] = Field(None, alias="Filière")
    valeur_mw: Optional[float] = Field(None, alias="Valeur (MW)")

    @field_validator("longitude", "latitude", "valeur_mw", mode="before")
    @classmethod
    def _parse_numbers(cls, v):
        return _to_float(v)
