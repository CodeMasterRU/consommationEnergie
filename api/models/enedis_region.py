# api/models/enedis_region.py
from typing import Optional
from pydantic import BaseModel
from pydantic.config import ConfigDict


class RegionBase(BaseModel):
    annee: Optional[int] = None
    code_region: Optional[int] = None
    nom_region: Optional[str] = None

    code_categorie_consommation: Optional[str] = None
    code_grand_secteur: Optional[str] = None
    code_secteur_naf2: Optional[int] = None

    nb_sites: Optional[int] = None
    conso_totale_mwh: Optional[float] = None
    conso_moyenne_mwh: Optional[float] = None
    nombre_de_mailles_secretisees: Optional[float] = None

    # В БД centroid хранится строкой вида "{'lon': 2.77, 'lat': 49.96}"
    centroid: Optional[str] = None

    model_config = ConfigDict(extra='ignore')


class RegionIn(RegionBase):
    """Вставка (create/bulk)."""
    pass


class RegionUpdate(RegionBase):
    """Частичное обновление (patch)."""
    pass


class RegionOut(RegionBase):
    """Ответы из API (разрешаем поле '_id')."""
    _id: Optional[str] = None
    model_config = ConfigDict(protected_namespaces=(), extra='ignore')
