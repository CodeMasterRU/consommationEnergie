from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re

# вычистим лишние символы (не цифры/знак/точка/запятая)
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


class SolarWindBase(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

    departement: str = Field(alias="Département")
    longitude: float = Field(alias="Longitude")
    latitude: float = Field(alias="Latitude")
    filiere: str = Field(alias="Filière")
    valeur_mw: float = Field(alias="Valeur (MW)")

    # конвертируем строки с запятой → float
    @field_validator("longitude", "latitude", "valeur_mw", mode="before")
    @classmethod
    def _parse_numbers(cls, v):
        return _to_float(v)


class SolarWindIn(SolarWindBase):
    pass


class SolarWindOut(SolarWindBase):
    id: str = Field(alias="_id")


class SolarWindUpdate(BaseModel):
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
