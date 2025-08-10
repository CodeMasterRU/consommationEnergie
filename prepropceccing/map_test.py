import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import folium
from folium.plugins import MarkerCluster

# === 1. Загрузка данных ===

# Путь к файлам
commune_data_path = "./DataEnedis10_000/enedis_commune_data.csv"
commune_geo_path = "20230823-communes-departement-region.csv"

# Загрузка
enedis_df = pd.read_csv(commune_data_path)
geo_df = pd.read_csv(commune_geo_path)

# === 2. Объединение данных ===

# Обеспечиваем формат кода INSEE
enedis_df['code_commune'] = enedis_df['code_commune'].astype(str).str.zfill(5)
geo_df['code_commune_INSEE'] = geo_df['code_commune_INSEE'].astype(str).str.zfill(5)

# Слияние
merged = enedis_df.merge(
    geo_df[['code_commune_INSEE', 'latitude', 'longitude']],
    left_on='code_commune',
    right_on='code_commune_INSEE',
    how='left'
)

# Очистка
merged = merged.dropna(subset=['latitude', 'longitude'])
merged['conso_totale_mwh'] = pd.to_numeric(merged['conso_totale_mwh'], errors='coerce')
merged['nombre_d_habitants'] = pd.to_numeric(merged['nombre_d_habitants'], errors='coerce')
merged = merged[merged['conso_totale_mwh'].notna() & merged['nombre_d_habitants'].notna() & (merged['nombre_d_habitants'] > 0)]

# Расчет consommation par habitant
merged['conso_par_habitant'] = merged['conso_totale_mwh'] / merged['nombre_d_habitants']

# === 3. Построение интерактивной карты ===

# Центр карты
center_lat = merged['latitude'].mean()
center_lon = merged['longitude'].mean()
m = folium.Map(location=[center_lat, center_lon], zoom_start=6, tiles="cartodbpositron")
marker_cluster = MarkerCluster().add_to(m)

# Добавление точек
for _, row in merged.iterrows():
    popup_text = (
        f"<b>Commune:</b> {row['nom_commune']}<br>"
        f"<b>Code commune:</b> {row['code_commune']}<br>"
        f"<b>Conso totale (MWh):</b> {row['conso_totale_mwh']:.2f}<br>"
        f"<b>Habitants:</b> {int(row['nombre_d_habitants'])}<br>"
        f"<b>Conso/habitant (MWh):</b> {row['conso_par_habitant']:.2f}"
    )
    folium.CircleMarker(
        location=[row['latitude'], row['longitude']],
        radius=5,
        popup=folium.Popup(popup_text, max_width=300),
        color='blue',
        fill=True,
        fill_opacity=0.6
    ).add_to(marker_cluster)

# === 4. Сохранение карты ===
m.save("communes_energy_map.html")
print("✅ Карту сохранено как communes_energy_map.html")
