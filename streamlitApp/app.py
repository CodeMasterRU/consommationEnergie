import os
import json
from ast import literal_eval

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import streamlit as st
from streamlit_folium import st_folium
import folium


st.set_page_config(page_title="Énergie France – Enedis", layout="wide")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
GPKG_FILE = "ADE_4-0_GPKG_WGS84G_FRA-ED2025-07-15.gpkg"

CSV_FILES = {
    "enedis adresse":     "enedis_adresse_data.csv",     # ожидаются lat/lon или geo_point_2d
    "enedis commune":     "enedis_commune_data.csv",     # code_commune, conso_totale_mwh, (annee)
    "enedis departement": "enedis_departement_data.csv", # code_departement, conso_totale_mwh, (annee)
    "enedis epci":        "enedis_epci_data.csv",        # code_epci (SIREN), conso_totale_mwh, (annee)
    "enedis iris":        "enedis_iris_data.csv",        # geo_point_2d или lat/lon
    "enedis region":      "enedis_region_data.csv",      # code_region, conso_totale_mwh, (annee)
}

@st.cache_data
def load_csv(rel_name: str) -> pd.DataFrame:
    path = os.path.join(DATA_DIR, rel_name)
    return pd.read_csv(path)

@st.cache_resource
def load_gpkg_layer(layer_name: str) -> gpd.GeoDataFrame:
    path = os.path.join(DATA_DIR, GPKG_FILE)
    gdf = gpd.read_file(path, layer=layer_name).to_crs(4326)
    return gdf

def normalize_dept(code):
    if pd.isna(code): return None
    s = str(code).strip().upper()
    if s in {"2A", "2B"}: return s
    if s.isdigit() and 971 <= int(s) <= 976: return s
    if s.isdigit(): return s.zfill(2)
    return s

def normalize_code(code, width=5):
    if pd.isna(code): return None
    s = str(code).strip()
    return s.zfill(width) if s.isdigit() else s

def ensure_numeric(df: pd.DataFrame, col: str):
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def add_conso_par_hab(df: pd.DataFrame, total_col="conso_totale_mwh", pop_col="nombre_d_habitants"):
    if total_col in df.columns and pop_col in df.columns:
        ensure_numeric(df, total_col)
        ensure_numeric(df, pop_col)
        mask = df[total_col].notna() & df[pop_col].notna() & (df[pop_col] > 0)
        df.loc[mask, "conso_par_habitant"] = df.loc[mask, total_col] / df.loc[mask, pop_col]
    return df

def parse_geo_point_2d(val):
    if pd.isna(val): return pd.Series([None, None])
    try:
        d = literal_eval(val) if isinstance(val, str) and val.strip().startswith("{") else json.loads(val)
        return pd.Series([d.get("lat"), d.get("lon")])  # (lat, lon)
    except Exception:
        return pd.Series([None, None])

def sanitize_for_geojson(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    # convert datetimes to strings
    for col in gdf.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        gdf[col] = gdf[col].astype(str)
    # convert complex objects to strings (except numbers)
    for col in gdf.columns:
        if col == gdf.geometry.name: 
            continue
        if pd.api.types.is_object_dtype(gdf[col]):
            gdf[col] = gdf[col].apply(lambda x: x if isinstance(x, (int, float)) or pd.isna(x) else str(x))
    return gdf

def folium_choropleth(gdf: gpd.GeoDataFrame, key_col: str, value_col: str, title: str, tooltip_fields=None):
    # simplify geometry for speed
    gdf_web = sanitize_for_geojson(gdf)
    gdf_web["geometry"] = gdf_web.geometry.simplify(0.01, preserve_topology=True)

    # map center
    try:
        center_geom = gdf_web.geometry.representative_point().union_all().centroid
        center = [center_geom.y, center_geom.x]
    except Exception:
        center = [46.6, 2.5]

    m = folium.Map(location=center, zoom_start=5, tiles="cartodbpositron")

    geojson_str = gdf_web.to_json()

    folium.Choropleth(
        geo_data=geojson_str,
        data=gdf_web[[key_col, value_col]],
        columns=[key_col, value_col],
        key_on=f"feature.properties.{key_col}",
        fill_color="OrRd",
        fill_opacity=0.85,
        line_opacity=0.6,
        legend_name=title,
        nan_fill_color="#f0f0f0"
    ).add_to(m)

    fields = [c for c in (tooltip_fields or []) if c in gdf_web.columns]
    if fields:
        folium.GeoJson(
            data=geojson_str,
            tooltip=folium.GeoJsonTooltip(fields=fields, aliases=fields, localize=True),
            style_function=lambda _: {"fillOpacity": 0, "color": "transparent"}
        ).add_to(m)

    st_folium(m, height=660, width=None)

def folium_points(df: pd.DataFrame, lat_col="latitude", lon_col="longitude", popup_cols=None, color="blue", title="Points"):
    m = folium.Map(location=[46.6, 2.5], zoom_start=5, tiles="cartodbpositron")
    for _, r in df.iterrows():
        lat, lon = r.get(lat_col), r.get(lon_col)
        if pd.isna(lat) or pd.isna(lon): 
            continue
        popup = None
        if popup_cols:
            lines = []
            for c in popup_cols:
                if c in df.columns:
                    lines.append(f"<b>{c}:</b> {r.get(c)}")
            popup = folium.Popup("<br>".join(lines), max_width=320) if lines else None
        folium.CircleMarker(
            location=[lat, lon], radius=4, color=color, fill=True, fill_opacity=0.7, popup=popup
        ).add_to(m)
    st_folium(m, height=660, width=None)


st.sidebar.title("Navigation")
section = st.sidebar.radio(
    "Выберите раздел",
    ["enedis adresse", "enedis commune", "enedis departement", "enedis epci", "enedis iris", "enedis region"]
)

# метрика: total vs per capita
metric_choice = st.sidebar.selectbox("Les metriques", ["conso_totale_mwh", "conso_par_habitant"])
year = st.sidebar.text_input("Filtre d'annee", value="")

st.title("⚡ Analyse de la consommation – Enedis / France")

csv_name = CSV_FILES.get(section)
df = None
if csv_name:
    try:
        df = load_csv(csv_name)
    except FileNotFoundError:
        st.error(f"Fichier non trouve: data/{csv_name}")

if df is None:
    st.info("Загрузите данные в папку `data/` или проверьте имена файлов.")
    st.stop()

st.subheader(f"Данные: {section}")
st.dataframe(df.head(30))

# sector filter (если есть)
sect_field = "code_grand_secteur" if "code_grand_secteur" in df.columns else None
if sect_field:
    sect_vals = ["(все)"] + sorted([str(x) for x in df[sect_field].dropna().unique()])
    chosen_sect = st.sidebar.selectbox("Фильтр по сектору", sect_vals, index=0)
    if chosen_sect != "(все)":
        df = df[df[sect_field].astype(str) == chosen_sect]

# year filter
if "annee" in df.columns:
    if not year:
        year = str(int(df["annee"].dropna().max()))
        st.sidebar.info(f"Aucune année sélectionnée - j'utilise la dernière dans les données: {year}")
    df = df[df["annee"].astype(str) == year]

# prepare per capita
ensure_numeric(df, "conso_totale_mwh")
add_conso_par_hab(df, total_col="conso_totale_mwh")

value_col = metric_choice
if value_col not in df.columns:
    st.warning(f"Colonne '{value_col}' manquant. J'utilise 'conso_totale_mwh'.")
    value_col = "conso_totale_mwh"

#SECTIONS
if section == "enedis region":
    if "code_region" not in df.columns:
        st.warning("В CSV нет колонки 'code_region'.")
        st.stop()
    df["code_region"] = df["code_region"].astype(str).str.zfill(2)
    agg = df.groupby("code_region", as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("region")
    key_geo = "code_insee" if "code_insee" in gdf.columns else gdf.columns[0]
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on="code_region", how="left")

    # afficher uniquement les régions avec des données (si nécessaire)
    if value_col == "conso_totale_mwh":
        gdf_merge = gdf_merge[gdf_merge[value_col].notna() & (gdf_merge[value_col] > 0)]

    st.subheader("🗺️ Carte par régions")
    folium_choropleth(
        gdf_merge,
        key_col=key_geo,
        value_col=value_col,
        title=f"{value_col} par région" + (f" – {year}" if year else ""),
        tooltip_fields=[c for c in ["nom_officiel", "code_insee", value_col] if c in gdf_merge.columns]
    )

elif section == "enedis departement":
    code_col = "code_departement" if "code_departement" in df.columns else None
    if not code_col:
        st.warning("CSV n'a pas de colonne 'code_departement'.")
        st.stop()
    df[code_col] = df[code_col].apply(normalize_dept)
    agg = df.groupby(code_col, as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("departement")
    key_geo = "code_insee" if "code_insee" in gdf.columns else gdf.columns[0]
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")

    if value_col == "conso_totale_mwh":
        gdf_merge = gdf_merge[gdf_merge[value_col].notna() & (gdf_merge[value_col] > 0)]

    st.subheader("🗺️ Карта по департаментам")
    folium_choropleth(
        gdf_merge,
        key_col=key_geo,
        value_col=value_col,
        title=f"{value_col} par département" + (f" – {year}" if year else ""),
        tooltip_fields=[c for c in ["nom_officiel", "code_insee", value_col] if c in gdf_merge.columns]
    )

elif section == "enedis commune":
    code_col = "code_commune" if "code_commune" in df.columns else None
    if not code_col:
        st.warning("В CSV нет колонки 'code_commune'.")
        st.stop()
    df[code_col] = df[code_col].apply(lambda x: normalize_code(x, width=5))
    agg = df.groupby(code_col, as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("commune")
    key_geo = "code_insee" if "code_insee" in gdf.columns else gdf.columns[0]
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")

    # как просил: на карте — только коммуны с ненулевым total
    if value_col == "conso_totale_mwh":
        gdf_merge = gdf_merge[gdf_merge[value_col].notna() & (gdf_merge[value_col] > 0)]

    st.subheader("🗺️ Карта по коммунам")
    folium_choropleth(
        gdf_merge,
        key_col=key_geo,
        value_col=value_col,
        title=f"{value_col} par commune" + (f" – {year}" if year else ""),
        tooltip_fields=[c for c in ["nom_officiel", "code_insee", value_col] if c in gdf_merge.columns]
    )

elif section == "enedis epci":
    code_col = "code_epci" if "code_epci" in df.columns else None
    if not code_col:
        st.warning("В CSV нет колонки 'code_epci'.")
        st.stop()
    df[code_col] = df[code_col].astype(str).str.zfill(9)  # SIREN — 9 знаков
    agg = df.groupby(code_col, as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("epci")
    key_geo = None
    for c in ["code_siren", "CODE_SIREN", "siren", "CODE_EPCI", "code_epci", "id", "code_insee"]:
        if c in gdf.columns: 
            key_geo = c; break
    if key_geo is None: key_geo = gdf.columns[0]

    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")

    if value_col == "conso_totale_mwh":
        gdf_merge = gdf_merge[gdf_merge[value_col].notna() & (gdf_merge[value_col] > 0)]

    st.subheader("🗺️ Карта по EPCI")
    folium_choropleth(
        gdf_merge,
        key_col=key_geo,
        value_col=value_col,
        title=f"{value_col} par EPCI" + (f" – {year}" if year else ""),
        tooltip_fields=[c for c in ["nom_officiel", key_geo, value_col] if c in gdf_merge.columns]
    )

elif section == "enedis iris":
    # для IRIS делаем точки (если нет полигона)
    df_local = df.copy()
    if "geo_point_2d" in df_local.columns and ("latitude" not in df_local.columns or "longitude" not in df_local.columns):
        df_local[["latitude", "longitude"]] = df_local["geo_point_2d"].apply(parse_geo_point_2d)

    if "latitude" not in df_local.columns or "longitude" not in df_local.columns:
        st.warning("Для IRIS нужны координаты точек: столбцы latitude/longitude или geo_point_2d.")
        st.stop()

    # фильтрация по total для IRIS точек (если выбран total)
    if value_col == "conso_totale_mwh":
        ensure_numeric(df_local, value_col)
        df_local = df_local[df_local[value_col].notna() & (df_local[value_col] > 0)]

    st.subheader("🗺️ Точки IRIS")
    popup_cols = [c for c in ["nom_iris", "nom_commune", value_col, "conso_par_habitant"] if c in df_local.columns]
    folium_points(df_local.dropna(subset=["latitude", "longitude"]), popup_cols=popup_cols, color="purple", title="IRIS")

elif section == "enedis adresse":
    df_local = df.copy()
    if "geo_point_2d" in df_local.columns and ("latitude" not in df_local.columns or "longitude" not in df_local.columns):
        df_local[["latitude", "longitude"]] = df_local["geo_point_2d"].apply(parse_geo_point_2d)

    if "latitude" not in df_local.columns or "longitude" not in df_local.columns:
        st.warning("Для адресов нужны координаты: 'latitude' и 'longitude' или 'geo_point_2d'.")
        st.stop()

    st.subheader("🗺️ Адресные точки")
    popup_cols = [c for c in ["adresse", "nom_commune", value_col, "conso_par_habitant"] if c in df_local.columns]
    folium_points(df_local.dropna(subset=["latitude", "longitude"]), popup_cols=popup_cols, color="red", title="Adresse")

