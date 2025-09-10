from .enedis_epci_data import router as epci_router
from .enedis_region_data import router as region_router
from .solar_wind_dept import router as solar_wind_router
from .major_installations import router as major_installs_router

__all__ = ["epci_router", "region_router", "solar_wind_router", "major_installs_router"]