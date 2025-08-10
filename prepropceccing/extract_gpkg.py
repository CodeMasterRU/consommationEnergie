import geopandas as gpd
import fiona

# Путь к твоему файлу
gpkg_path = "ADE_4-0_GPKG_WGS84G_FRA-ED2025-07-15.gpkg"

# Посмотреть, какие слои есть внутри
layers = fiona.listlayers(gpkg_path)
print("Слои в GeoPackage:")
for layer in layers:
    print(layer)

# Прочитать слой регионов
gdf_regions = gpd.read_file(gpkg_path, layer="REGION")  # или "REGION_2025" — смотри по списку
print(gdf_regions.head())

# Быстро нарисовать карту регионов
gdf_regions.plot(edgecolor="black", facecolor="none", figsize=(8,8))
