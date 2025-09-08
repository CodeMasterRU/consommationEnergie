from pathlib import Path
import warnings
import geopandas as gpd
import fiona
from shapely.geometry import mapping
from pymongo import MongoClient, InsertOne

warnings.filterwarnings("ignore", category=RuntimeWarning)

# === Конфигурация ===
GPKG_PATH = Path(__file__).resolve().parent / "data" / "ADE_4-0_GPKG_WGS84G_FRA-ED2025-07-15.gpkg"

MONGO_URI = "mongodb+srv://mynameisvitos_db_user:Js0dbrEgIWOAVnak@energy-fr-cluster.ijkewy2.mongodb.net/"
DB_NAME = "energy_fr"

# Слои, коллекции и ключевые поля
layers_cfg = {
    "commune": ("communes_points", ["INSEE_COM", "NOM_COM"]),      # будет точка
    "departement": ("departements_geom", ["CODE_DEP", "NOM_DEP"]), # полигоны
    "region": ("regions_geom", ["CODE_REG", "NOM_REG"]),           # полигоны
    "epci": ("epci_geom", ["SIREN_EPCI", "NOM_EPCI"]),             # полигоны
}

SIMPLIFY_TOL = 0.0015  # упрощение для полигонов (~150 м)
ROUND_DEC = 5          # округление координат

# === Хелпер для округления координат ===
def round_coords(obj, ndigits=5):
    if not obj:
        return obj
    t = obj.get("type")
    coords = obj.get("coordinates")

    def r(v): return None if v is None else round(v, ndigits)
    def round_seq(x):
        if isinstance(x, (list, tuple)):
            if len(x) == 2 and all(isinstance(i, (int, float)) for i in x):
                return [r(x[0]), r(x[1])]
            return [round_seq(i) for i in x]
        return x

    if t in ("Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", "MultiPolygon"):
        obj["coordinates"] = round_seq(coords)
    return obj

# === Основная логика ===
assert GPKG_PATH.exists(), f"❌ Не найден файл: {GPKG_PATH}"
print("✅ Нашёл GPKG:", GPKG_PATH)

layers = fiona.listlayers(GPKG_PATH)
print("🔎 Слои в файле:", layers)

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

for layer, (collection, keep_cols) in layers_cfg.items():
    if layer not in layers:
        print(f"⚠️ Слой {layer} не найден в GPKG, пропускаем")
        continue

    print(f"\n=== Обработка слоя {layer} → {collection} ===")

    gdf = gpd.read_file(GPKG_PATH, layer=layer).to_crs(4326)

    # оставить только нужные поля
    cols = [c for c in keep_cols if c in gdf.columns]
    gdf = gdf[cols + ["geometry"]]

    if layer == "commune":
        # заменить полигоны на центроиды (Point)
        gdf["geometry"] = gdf["geometry"].centroid
        gdf["geometry"] = gdf["geometry"].apply(
            lambda p: {"type": "Point", "coordinates": [round(p.x, ROUND_DEC), round(p.y, ROUND_DEC)]}
            if p else None
        )
    else:
        # упрощение полигонов + округление
        gdf["geometry"] = gdf["geometry"].simplify(SIMPLIFY_TOL, preserve_topology=True)
        gdf["geometry"] = gdf["geometry"].apply(lambda g: round_coords(mapping(g), ROUND_DEC) if g else None)

    # запись в Mongo
    col = db[collection]
    col.drop()

    records = gdf.to_dict("records")
    if not records:
        print(f"⚠️ Нет данных в {layer}")
        continue

    batch, BATCH_SIZE = [], 2000
    count = 0
    for rec in records:
        batch.append(InsertOne(rec))
        if len(batch) >= BATCH_SIZE:
            col.bulk_write(batch, ordered=False)
            count += len(batch)
            batch = []
            print(f"   Вставлено {count} доков...")
    if batch:
        col.bulk_write(batch, ordered=False)
        count += len(batch)

    print(f"✅ Импортировано {count} объектов в {DB_NAME}.{collection}")

    # индекс 2dsphere
    col.create_index([("geometry", "2dsphere")])
    print(f"📌 Индекс 2dsphere создан для {collection}")

print("\n🎉 Все слои обработаны")
