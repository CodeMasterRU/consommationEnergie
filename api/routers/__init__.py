from .enedis_epci_data import router as epci_router
from .enedis_region_data import router as region_router
from .solar_wind_dept import router as solar_wind_router
from .major_installations import router as major_installs_router
from .eco2mix_national import router as eco2mix_router
from .enedis_adresse_data import router as adresse_router
from .enedis_commune_data import router as commune_router
from .enedis_departement_data import router as departement_router
from .enedis_iris_data import router as iris_router
from .evolution_production_fr import router as prod_fr_router
from .evolution_parc_installe_fr import router as evolution_parc_router

__all__ = ["epci_router", "region_router", "solar_wind_router", "major_installs_router", "eco2mix_router", "adresse_router", "commune_router", "departement_router", "iris_router", "prod_fr_router", "evolution_parc_router"]