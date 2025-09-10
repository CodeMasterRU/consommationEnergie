from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # читаем из .env (верхний регистр), а внутри используем нижний
    mongo_uri: str = Field(..., alias="MONGO_URI")
    db_name: str = Field(..., alias="DB_NAME")

    # имена коллекций — либо берём из .env, либо дефолты
    coll_epci: str = Field("enedis_epci_data", alias="COLL_EPCI")
    coll_region: str = Field("enedis_region_data", alias="COLL_REGION")
    coll_solar_wind_dept: str = Field("solar_wind_dept", alias="COLL_SW")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

settings = Settings()