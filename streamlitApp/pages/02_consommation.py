# pages/2_⚡_Consommation_Enedis.py
import os
import json
from pathlib import Path
from ast import literal_eval

import pandas as pd
import geopandas as gpd
import streamlit as st
from streamlit_folium import st_folium
import folium
from pymongo import MongoClient

# ================= CONFIG =================
st.set_page_config(page_title="Énergie France – Consommation (Enedis)", layout="wide")
st.title("⚡ Consommation d'électricité – Enedis / France")

# где искать GPKG
GPKG_NAME = "ADE_4-0_GPKG_WGS84G_FRA-ED2025-07-15.gpkg"

def _find_gpkg() -> Path:
    here = Path(__file__).resolve().parent
    candidates = [
        here / "data" / GPKG_NAME,               # streamlitApp/pages/data
        here.parent / "data" / GPKG_NAME,        # streamlitApp/data
        here.parent.parent / "data" / GPKG_NAME  # consommationEnergie/data
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(f"Не найден GPKG: {GPKG_NAME}. Положи файл в одну из папок: "
                            f"{', '.join(str(p.parent) for p in candidates)}")

GPKG_PATH = _find_gpkg()

# имена коллекций с данными (Mongo)
COLL_DATA = {
    "enedis adresse":     "enedis_adresse_data",
    "enedis commune":     "enedis_commune_data",
    "enedis departement": "enedis_departement_data",
    "enedis epci":        "enedis_epci_data",
    "enedis iris":        "enedis_iris_data",
    "enedis region":      "enedis_region_data",
}

# ================= Mongo helpers =================
def _mongo_df(collection: str, query=None, projection=None) -> pd.DataFrame:
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client[st.secrets["mongo"]["db"]]
    cur = db[collection].find(query or {}, projection)
    df = pd.DataFrame(list(cur))
    client.close()
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df

# ================= GPKG helpers =================
@st.cache_resource
def load_gpkg_layer(layer_name: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(GPKG_PATH, layer=layer_name).to_crs(4326)
    return gdf

# ================= Utils =================
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
        return pd.Series([d.get("lat"), d.get("lon")])
    except Exception:
        return pd.Series([None, None])

def sanitize_for_geojson(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    for col in gdf.select_dtypes(include=["datetime64[ns]", "datetime64[ns, UTC]"]).columns:
        gdf[col] = gdf[col].astype(str)
    for col in gdf.columns:
        if col == gdf.geometry.name:
            continue
        if pd.api.types.is_object_dtype(gdf[col]):
            gdf[col] = gdf[col].apply(lambda x: x if isinstance(x, (int, float)) or pd.isna(x) else str(x))
    return gdf

def filter_nonempty_numeric(gdf: gpd.GeoDataFrame, col: str) -> gpd.GeoDataFrame:
    if col not in gdf.columns:
        return gdf.iloc[0:0]
    gdf = gdf.copy()
    gdf[col] = pd.to_numeric(gdf[col], errors="coerce")
    return gdf[gdf[col].notna() & (gdf[col] > 0)]

def folium_choropleth(gdf: gpd.GeoDataFrame, key_col: str, value_col: str, title: str, tooltip_fields=None):
    gdf_web = sanitize_for_geojson(gdf)
    # упростим геометрию, чтобы карта летала
    try:
        gdf_web["geometry"] = gdf_web.geometry.simplify(0.01, preserve_topology=True)
    except Exception:
        pass
    try:
        center_geom = gdf_web.geometry.representative_point().unary_union.centroid
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

def folium_points(df: pd.DataFrame, lat_col="latitude", lon_col="longitude", popup_cols=None, color="blue"):
    m = folium.Map(location=[46.6, 2.5], zoom_start=5, tiles="cartodbpositron")
    for _, r in df.iterrows():
        lat, lon = r.get(lat_col), r.get(lon_col)
        if pd.isna(lat) or pd.isna(lon):
            continue
        popup = None
        if popup_cols:
            lines = [f"<b>{c}:</b> {r.get(c)}" for c in popup_cols if c in df.columns]
            popup = folium.Popup("<br>".join(lines), max_width=320) if lines else None
        folium.CircleMarker(
            location=[lat, lon], radius=4, color=color, fill=True, fill_opacity=0.7, popup=popup
        ).add_to(m)
    st_folium(m, height=660, width=None)

# ================= SIDEBAR =================
st.sidebar.title("Navigation")
section = st.sidebar.radio(
    "Выберите раздел",
    ["enedis adresse", "enedis commune", "enedis departement", "enedis epci", "enedis iris", "enedis region"]
)
metric_choice = st.sidebar.selectbox("Les metriques", ["conso_totale_mwh", "conso_par_habitant"])
year = st.sidebar.text_input("Filtre d'annee", value="")

# ================= LOAD MAIN DATA (Mongo) =================
df = _mongo_df(COLL_DATA[section])

st.subheader(f"Aperçu données: {section}")
st.dataframe(df.head(30), use_container_width=True)

# фильтры
if "code_grand_secteur" in df.columns:
    sect_vals = ["(все)"] + sorted([str(x) for x in df["code_grand_secteur"].dropna().unique()])
    chosen_sect = st.sidebar.selectbox("Фильтр по сектору", sect_vals, index=0)
    if chosen_sect != "(все)":
        df = df[df["code_grand_secteur"].astype(str) == chosen_sect]

if "annee" in df.columns:
    if not year:
        year = str(int(df["annee"].dropna().max()))
        st.sidebar.info(f"Aucune année sélectionnée – j'utilise la dernière: {year}")
    df = df[df["annee"].astype(str) == year]

ensure_numeric(df, "conso_totale_mwh")
add_conso_par_hab(df, total_col="conso_totale_mwh")
value_col = metric_choice if metric_choice in df.columns else "conso_totale_mwh"

# ================= SECTIONS =================
if section == "enedis region":
    # агрегируем
    code_col = "code_region" if "code_region" in df.columns else "code"
    if code_col not in df.columns:
        st.error("Не найден код региона в данных.")
        st.stop()
    df[code_col] = df[code_col].astype(str).str.zfill(2)
    agg = df.groupby(code_col, as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("region")
    key_geo = "code_insee" if "code_insee" in gdf.columns else gdf.columns[0]
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")
    if value_col == "conso_totale_mwh":
        gdf_merge = filter_nonempty_numeric(gdf_merge, value_col)

    st.subheader("🗺️ Carte par régions (GPKG)")
    folium_choropleth(
        gdf_merge, key_col=key_geo, value_col=value_col,
        title=f"{value_col} par région – {year}",
        tooltip_fields=[c for c in ["nom_officiel", key_geo, value_col] if c in gdf_merge.columns]
    )

elif section == "enedis departement":
    code_col = "code_departement"
    if code_col not in df.columns:
        st.error("Не найден код департамента.")
        st.stop()
    df[code_col] = df[code_col].apply(normalize_dept)
    agg = df.groupby(code_col, as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("departement")
    key_geo = "code_insee" if "code_insee" in gdf.columns else gdf.columns[0]
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")
    if value_col == "conso_totale_mwh":
        gdf_merge = filter_nonempty_numeric(gdf_merge, value_col)

    st.subheader("🗺️ Карта по департаментам (GPKG)")
    folium_choropleth(
        gdf_merge, key_col=key_geo, value_col=value_col,
        title=f"{value_col} par département – {year}",
        tooltip_fields=[c for c in ["nom_officiel", key_geo, value_col] if c in gdf_merge.columns]
    )

elif section == "enedis epci":
    code_col = "code_epci" if "code_epci" in df.columns else None
    if not code_col:
        st.error("Не найден код EPCI.")
        st.stop()
    df[code_col] = df[code_col].astype(str).str.zfill(9)
    agg = df.groupby(code_col, as_index=False)[value_col].sum()

    gdf = load_gpkg_layer("epci")
    key_geo = next((c for c in ["code_siren","CODE_SIREN","siren","CODE_EPCI","code_epci","id","code_insee"] if c in gdf.columns), gdf.columns[0])
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")
    if value_col == "conso_totale_mwh":
        gdf_merge = filter_nonempty_numeric(gdf_merge, value_col)

    st.subheader("🗺️ Карта по EPCI (GPKG)")
    folium_choropleth(
        gdf_merge, key_col=key_geo, value_col=value_col,
        title=f"{value_col} par EPCI – {year}",
        tooltip_fields=[c for c in ["nom_officiel", key_geo, value_col] if c in gdf_merge.columns]
    )

elif section == "enedis commune":
    code_col = "code_commune"
    if code_col not in df.columns:
        st.error("Не найден код коммуны.")
        st.stop()
    df[code_col] = df[code_col].apply(lambda x: normalize_code(x, width=5))
    agg = df.groupby(code_col, as_index=False)[value_col].sum(min_count=1)

    gdf = load_gpkg_layer("commune")
    key_geo = "code_insee" if "code_insee" in gdf.columns else gdf.columns[0]
    gdf_merge = gdf.merge(agg, left_on=key_geo, right_on=code_col, how="left")
    gdf_merge = filter_nonempty_numeric(gdf_merge, value_col)
    if gdf_merge.empty:
        st.warning("Нет коммун с ненулевым значением выбранной метрики для текущих фильтров.")
        st.stop()

    st.subheader("🗺️ Карта по коммунам (GPKG)")
    folium_choropleth(
        gdf_merge, key_col=key_geo, value_col=value_col,
        title=f"{value_col} par commune – {year}",
        tooltip_fields=[c for c in ["nom_officiel", key_geo, value_col] if c in gdf_merge.columns]
    )

elif section == "enedis iris":
    df_local = df.copy()
    if "geo_point_2d" in df_local.columns and ("latitude" not in df_local.columns or "longitude" not in df_local.columns):
        df_local[["latitude", "longitude"]] = df_local["geo_point_2d"].apply(lambda s: pd.Series(parse_geo_point_2d(s)))
    if "latitude" not in df_local.columns or "longitude" not in df_local.columns:
        st.warning("Для IRIS нужны координаты: latitude/longitude или geo_point_2d.")
        st.stop()
    if value_col == "conso_totale_mwh":
        ensure_numeric(df_local, value_col)
        df_local = df_local[df_local[value_col].notna() & (df_local[value_col] > 0)]
    st.subheader("🗺️ Точки IRIS (Mongo)")
    popup_cols = [c for c in ["nom_iris", "nom_commune", value_col, "conso_par_habitant"] if c in df_local.columns]
    folium_points(df_local.dropna(subset=["latitude", "longitude"]), popup_cols=popup_cols, color="purple")

elif section == "enedis adresse":
    df_local = df.copy()
    if "geo_point_2d" in df_local.columns and ("latitude" not in df_local.columns or "longitude" not in df_local.columns):
        df_local[["latitude", "longitude"]] = df_local["geo_point_2d"].apply(lambda s: pd.Series(parse_geo_point_2d(s)))
    if "latitude" not in df_local.columns or "longitude" not in df_local.columns:
        st.warning("Для адресов нужны координаты: latitude/longitude или geo_point_2d.")
        st.stop()
    st.subheader("🗺️ Адресные точки (Mongo)")
    popup_cols = [c for c in ["adresse", "nom_commune", value_col, "conso_par_habitant"] if c in df_local.columns]
    folium_points(df_local.dropna(subset=["latitude", "longitude"]), popup_cols=popup_cols, color="red")
