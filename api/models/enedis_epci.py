# api/models/enedis_epci.py
from __future__ import annotations

from typing import Optional, Union, Any

from pydantic import BaseModel, Field, ConfigDict, field_validator

import ast
import json


# -----------------------------
# Геометрия: центр EPCI
# -----------------------------
class GeoPoint(BaseModel):
    lon: float
    lat: float

    model_config = ConfigDict(extra="ignore")


# -----------------------------
# БАЗОВАЯ МОДЕЛЬ ДЛЯ EPCI
# -----------------------------
class EPCIBase(BaseModel):
    # Обязательные поля
    annee: int
    code_epci: Union[int, str]

    # Описательные поля
    nom_epci: Optional[str] = None
    type_epci: Optional[str] = None

    # Иерархия территорий
    code_departement: Optional[Union[int, str]] = None
    nom_departement: Optional[str] = None
    code_region: Optional[Union[int, str]] = None
    nom_region: Optional[str] = None

    # Отраслевые/категорийные коды
    code_categorie_consommation: Optional[str] = None  # "ENT" и т.п.
    code_grand_secteur: Optional[str] = None          # "TERTIAIRE" и т.п.
    code_secteur_naf2: Optional[int] = None

    # Количества/метрики
    nb_sites: Optional[int] = None
    conso_totale_mwh: Optional[float] = None
    conso_moyenne_mwh: Optional[float] = None

    # В некоторых выгрузках встречаются варианты названия этого поля.
    # Мы будем приводить их к одному имени: `nombre_de_mailles_secretes`.
    nombre_de_mailles_secretes: Optional[Union[int, float]] = None

    # Центроид (в Mongo часто строкой вида "{'lon': 2.5, 'lat': 49.9}")
    centroid: Optional[GeoPoint] = None

    model_config = ConfigDict(
        extra="allow",           # пропускаем лишние поля, если встретятся
        populate_by_name=True,   # позволяем использовать алиасы
    )

    # --- Валидаторы ---

    @field_validator("code_epci", "code_departement", "code_region", mode="before")
    @classmethod
    def _to_int_or_str(cls, v: Any) -> Any:
        """Разрешаем хранить коды как число или строку — приводим к числу, если возможно."""
        if v is None:
            return v
        try:
            # В некоторых наборах код может приходить как "062" — int сохранит 62.
            # Если тебе критично сохранять ведущие нули, убери этот try/except.
            return int(v)
        except Exception:
            return str(v)

    @field_validator("centroid", mode="before")
    @classmethod
    def _parse_centroid(cls, v: Any) -> Any:
        """
        Разбираем centroid, который может приходить:
        - уже как dict {"lon": ..., "lat": ...}
        - как строка "{'lon': 2.5, 'lat': 49.9}" (python-словарь)
        - как JSON-строка '{"lon": 2.5, "lat": 49.9}'
        - как список/кортеж [lon, lat]
        """
        if v is None:
            return v

        if isinstance(v, GeoPoint):
            return v

        if isinstance(v, dict):
            lon = v.get("lon") if "lon" in v else v.get("x")
            lat = v.get("lat") if "lat" in v else v.get("y")
            if lon is not None and lat is not None:
                return GeoPoint(lon=float(lon), lat=float(lat))
            return None

        if isinstance(v, (list, tuple)) and len(v) == 2:
            return GeoPoint(lon=float(v[0]), lat=float(v[1]))

        if isinstance(v, str):
            s = v.strip()
            # Пытаемся как JSON
            try:
                obj = json.loads(s)
                return cls._parse_centroid(obj)
            except Exception:
                pass
            # Пытаемся как python-литерал "{'lon': ..., 'lat': ...}"
            try:
                obj = ast.literal_eval(s)
                return cls._parse_centroid(obj)
            except Exception:
                pass

        return None

    @field_validator("nombre_de_mailles_secretes", mode="before")
    @classmethod
    def _unify_secret_cells(cls, v: Any, values: dict) -> Any:
        """
        Приводим различные варианты названия к единому полю.
        Если в документе встретились:
          - nombre_de_mailles_secretees
          - nombre_de_mailles_secretisees
        и т.п., мы заполним canonical-поле nombre_de_mailles_secretes.
        """
        if v is not None:
            return v

        # ищем популярные опечатки/варианты
        for k in (
            "nombre_de_mailles_secretees",
            "nombre_de_mailles_secretees",
            "nombre_de_mailles_secretisees",
            "nombre_de_mailles_secretiesses",
            "nombre_de_mailles_secretées",  # на всякий случай
        ):
            if k in values and values[k] is not None:
                return values[k]
        return v


# -----------------------------
# ВЫХОДНАЯ МОДЕЛЬ (из БД)
# -----------------------------
class EPCIOut(EPCIBase):
    id: str = Field(alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def _id_to_str(cls, v: Any) -> str:
        try:
            return str(v)
        except Exception:
            return v


# -----------------------------
# ВХОД ДЛЯ СОЗДАНИЯ
# -----------------------------
class EPCIIn(EPCIBase):
    """
    Для вставки нового документа.
    Требуемые поля унаследованы из EPCIBase: annee, code_epci.
    Остальные — опциональные.
    """
    pass


# -----------------------------
# ЧАСТИЧНОЕ ОБНОВЛЕНИЕ (PATCH)
# -----------------------------
class EPCIUpdate(BaseModel):
    annee: Optional[int] = None
    code_epci: Optional[Union[int, str]] = None

    nom_epci: Optional[str] = None
    type_epci: Optional[str] = None

    code_departement: Optional[Union[int, str]] = None
    nom_departement: Optional[str] = None
    code_region: Optional[Union[int, str]] = None
    nom_region: Optional[str] = None

    code_categorie_consommation: Optional[str] = None
    code_grand_secteur: Optional[str] = None
    code_secteur_naf2: Optional[int] = None

    nb_sites: Optional[int] = None
    conso_totale_mwh: Optional[float] = None
    conso_moyenne_mwh: Optional[float] = None
    nombre_de_mailles_secretes: Optional[Union[int, float]] = None

    centroid: Optional[GeoPoint] = None

    model_config = ConfigDict(extra="allow")

    # те же приведения типов, что и в базовой модели
    _normalize_codes = EPCIBase.__dict__["_to_int_or_str"]
    _parse_centroid = EPCIBase.__dict__["_parse_centroid"]
    _unify_secret_cells = EPCIBase.__dict__["_unify_secret_cells"]
