# streamlitApp/pages/production.py
import os
import math
import pandas as pd
import streamlit as st
import altair as alt
import folium
from streamlit_folium import st_folium
from pymongo import MongoClient

st.set_page_config(page_title="⚙️ Production & Parc – France", layout="wide")
st.title("⚙️ Production & Parc installé – Synthèse (type RTE)")

# ===================== Mongo helpers =====================
def _mongo_df(collection: str, query=None, projection=None) -> pd.DataFrame:
    """Read a MongoDB collection into a pandas DataFrame."""
    client = MongoClient(st.secrets["mongo"]["uri"])
    db = client[st.secrets["mongo"]["db"]]
    cur = db[collection].find(query or {}, projection)
    df = pd.DataFrame(list(cur))
    client.close()
    if "_id" in df.columns:
        df = df.drop(columns=["_id"])
    return df

def _num_fr_to_float(s: pd.Series) -> pd.Series:
    """Convert French numbers '1 234,56' → 1234.56"""
    return (
        s.astype(str)
         .str.replace("\u202f", "", regex=False)
         .str.replace(" ", "", regex=False)
         .str.replace(",", ".", regex=False)
         .pipe(pd.to_numeric, errors="coerce")
    )

# ===================== Loaders from Mongo =====================
@st.cache_data
def load_production_mongo() -> pd.DataFrame:
    # Имя коллекции как в Atlas
    coll = "Évolution de la production d'électricité en France"
    df = _mongo_df(coll)

    rename = {
        "Date": "date",
        "Filière": "filiere",
        "Filiere": "filiere",
        "Valeur (TWh)": "twh",
        "Nature": "nature",
    }
    for k, v in rename.items():
        if k in df.columns:
            df = df.rename(columns={k: v})

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["twh"] = _num_fr_to_float(df["twh"])
    df["filiere"] = df.get("filiere", "Total").astype(str).str.strip()
    df["annee"] = df["date"].dt.year
    df["mois"] = df["date"].dt.month
    df["mois_txt"] = df["date"].dt.strftime("%b")
    return df.dropna(subset=["date", "twh", "filiere"])

@st.cache_data
def load_park_mongo() -> pd.DataFrame:
    coll = "Évolution du parc installé de production d'électricité en France"
    df = _mongo_df(coll)

    rename = {
        "Date": "date", "Année": "date",
        "Filière": "filiere", "Filiere": "filiere",
        "Puissance (GW)": "gw", "Puissance GW": "gw", "Valeur (GW)": "gw",
        "Nature": "nature",
    }
    for k, v in rename.items():
        if k in df.columns:
            df = df.rename(columns={k: v})

    s = df["date"].astype(str).str.strip()
    if s.str.fullmatch(r"\d{4}").all():
        df["date"] = pd.to_datetime(s, format="%Y", errors="coerce")
    else:
        df["date"] = pd.to_datetime(s, errors="coerce")

    df["gw"] = _num_fr_to_float(df["gw"])
    df["filiere"] = df.get("filiere", "Total").astype(str).str.strip()
    df["is_total"] = df["filiere"].str.contains(r"Puissance\s+installée\s+totale", case=False, na=False)
    df["annee"] = df["date"].dt.year
    df["annee_str"] = df["annee"].astype("Int64").astype(str)
    return df.dropna(subset=["date", "gw"])

@st.cache_data
def load_installations_mongo() -> pd.DataFrame:
    coll = "Répartition des principales installations de production d'électricité en France, hors solaire et éolien"
    df = _mongo_df(coll)

    rename = {
        "Filière": "filiere", "Filiere": "filiere", "Type": "filiere",
        "Valeur (MW)": "mw", "Puissance (MW)": "mw",
        "Nom": "nom", "Nom site": "nom",
        "Latitude": "latitude", "Longitude": "longitude",
    }
    for k, v in rename.items():
        if k in df.columns:
            df = df.rename(columns={k: v})

    df["mw"] = _num_fr_to_float(df["mw"])
    df["filiere"] = df.get("filiere", "Inconnue").astype(str).str.strip()
    df = df.dropna(subset=["latitude", "longitude", "mw"])
    return df

@st.cache_data
def load_solar_wind_mongo() -> pd.DataFrame:
    coll = "Répartition des installations de production d'électricité solaire et éolienne en France, à la maille départementale"
    df = _mongo_df(coll)

    rename = {
        "Filière": "filiere", "Filiere": "filiere", "Type": "filiere",
        "Valeur (MW)": "mw", "Puissance (MW)": "mw",
        "Nom": "nom", "Nom site": "nom",
        "Latitude": "latitude", "Longitude": "longitude",
        "Nature": "nature",
    }
    for k, v in rename.items():
        if k in df.columns:
            df = df.rename(columns={k: v})

    df["mw"] = _num_fr_to_float(df["mw"])
    df["filiere"] = (
        df.get("filiere", "Inconnue")
          .astype(str).str.strip()
          .replace({"Eolien": "Éolien", "eolien": "Éolien", "solaire": "Solaire"})
    )
    df = df.dropna(subset=["latitude", "longitude", "mw"])
    return df

# ===================== UI Tabs =====================
tabs = st.tabs([
    "📊 Production (TWh)",
    "🏗️ Parc installé (GW)",
    "🗺️ Installations (carte)",
    "🗺️ Solaire & Éolien (département)"
])

# ===== TAB 1: Production (TWh) =====
with tabs[0]:
    dfp = load_production_mongo()

    colA, colB = st.columns(2)
    with colA:
        period_mode = st.toggle("Annuel / Mensuel", value=True, help="Вкл = годовой, выкл = помесячный")
    with colB:
        global_mode = st.toggle("Global / Filière", value=True, help="Вкл = сумма, выкл = по филиерам (stack)")

    all_fils = sorted(dfp["filiere"].dropna().unique())
    selected_fils = st.multiselect("Filières", all_fils, default=all_fils)
    dfp = dfp[dfp["filiere"].isin(selected_fils)]

    annual = dfp.groupby(["annee", "filiere"], as_index=False)["twh"].sum().sort_values(["annee", "filiere"])
    monthly = dfp.copy()

    if not period_mode:
        years_avail = sorted(monthly["annee"].unique())
        year_pick = st.selectbox("Année", years_avail, index=len(years_avail) - 1 if years_avail else 0)
        monthly = monthly[monthly["annee"] == year_pick]

    if period_mode:
        if global_mode:
            data = annual.groupby("annee", as_index=False)["twh"].sum()
            chart = (
                alt.Chart(data).mark_bar().encode(
                    x=alt.X("annee:O", title="Année"),
                    y=alt.Y("twh:Q", title="Production (TWh)"),
                    tooltip=[alt.Tooltip("annee:O"), alt.Tooltip("twh:Q", format=",.1f")]
                ).properties(height=420, title="Évolution de la production (annuel)")
            )
        else:
            chart = (
                alt.Chart(annual).mark_bar().encode(
                    x=alt.X("annee:O", title="Année"),
                    y=alt.Y("twh:Q", title="Production (TWh)", stack="zero"),
                    color=alt.Color("filiere:N", title="Filière"),
                    tooltip=["filiere:N", alt.Tooltip("annee:O"), alt.Tooltip("twh:Q", format=",.1f")]
                ).properties(height=420, title="Production par filière (annuel)")
            )
    else:
        mois_order = ["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Aoû","Sep","Oct","Nov","Déc"]
        if global_mode:
            data = monthly.groupby(["annee","mois","mois_txt"], as_index=False)["twh"].sum()
            year = int(data["annee"].iloc[0]) if not data.empty else 0
            reidx = pd.MultiIndex.from_product([[year], range(1, 12 + 1)], names=["annee", "mois"])
            data = data.set_index(["annee","mois"]).reindex(reidx).reset_index()
            data["mois_txt"] = data["mois"].map({1:"Jan",2:"Fév",3:"Mar",4:"Avr",5:"Mai",6:"Juin",7:"Juil",8:"Aoû",9:"Sep",10:"Oct",11:"Nov",12:"Déc"})
            data["twh"] = data["twh"].fillna(0)
            chart = (
                alt.Chart(data).mark_bar().encode(
                    x=alt.X("mois_txt:O", sort=mois_order, title="Mois"),
                    y=alt.Y("twh:Q", title="Production (TWh)"),
                    tooltip=[alt.Tooltip("mois_txt:N"), alt.Tooltip("twh:Q", format=",.2f")]
                ).properties(height=420, title=f"Production mensuelle totale – {year}")
            )
        else:
            chart = (
                alt.Chart(monthly).mark_bar().encode(
                    x=alt.X("mois_txt:O", sort=mois_order, title="Mois"),
                    y=alt.Y("twh:Q", title="Production (TWh)", stack="zero"),
                    color=alt.Color("filiere:N", title="Filière"),
                    tooltip=["filiere:N", alt.Tooltip("mois_txt:N"), alt.Tooltip("twh:Q", format=",.2f")]
                ).properties(height=420, title=f"Production mensuelle par filière – {int(monthly['annee'].iloc[0]) if not monthly.empty else ''}")
            )

    st.altair_chart(chart, use_container_width=True)

    if "nature" in dfp.columns and dfp["nature"].str.contains("Provisoires", case=False, na=False).any():
        st.caption("🟠 Données provisoires présentes sur la période sélectionnée.")

# ===== TAB 2: Parc installé (GW) =====
with tabs[1]:
    dfk = load_park_mongo()

    global_mode_gw = st.toggle(
        "Global / Filière (GW)",
        value=False,
        help="Вкл = суммарная мощность (total); выкл = по филиерам (стек)."
    )

    dfk["filiere"] = dfk["filiere"].astype(str).str.strip()
    dfk_no_total = dfk[~dfk["is_total"]].copy()
    dfk_no_total["annee_str"] = dfk_no_total["annee"].astype("Int64").astype(str)
    dfk["annee_str"] = dfk["annee"].astype("Int64").astype(str)

    filiere_order = [
        "Thermique renouvelable et déchets",
        "Solaire",
        "Eolien",
        "Thermique fossile",
        "Hydraulique",
        "Nucléaire",
    ]
    filiere_colors = ["#2E7D32", "#F39C12", "#26A69A", "#BDBDBD", "#1E88E5", "#F1C40F"]
    existing = [f for f in filiere_order if f in set(dfk_no_total["filiere"])]
    picked_fils_k = st.multiselect("Filières", existing, default=existing)
    dfk_no_total = dfk_no_total[dfk_no_total["filiere"].isin(picked_fils_k)]

    annual_k = (
        dfk_no_total.groupby(["annee_str", "filiere"], as_index=False)["gw"]
        .sum().sort_values(["annee_str", "filiere"])
    )

    if global_mode_gw:
        total_rows = dfk[dfk["is_total"]].copy()
        if not total_rows.empty:
            data = total_rows.groupby("annee_str", as_index=False)["gw"].sum()
        else:
            data = annual_k.groupby("annee_str", as_index=False)["gw"].sum()

        chart_k = (
            alt.Chart(data).mark_bar().encode(
                x=alt.X("annee_str:O", title="Année", sort="ascending"),
                y=alt.Y("gw:Q", title="Puissance installée (GW)"),
                tooltip=[alt.Tooltip("annee_str:O"), alt.Tooltip("gw:Q", format=",.1f")],
            ).properties(height=420, title="Évolution du parc installé (total)")
        )
    else:
        chart_k = (
            alt.Chart(annual_k).mark_bar().encode(
                x=alt.X("annee_str:O", title="Année", sort="ascending"),
                y=alt.Y("gw:Q", title="Puissance installée (GW)", stack="zero"),
                color=alt.Color(
                    "filiere:N", title="Filière",
                    scale=alt.Scale(domain=filiere_order, range=filiere_colors),
                    sort=filiere_order,
                ),
                order=alt.Order("filiere:N", sort="descending"),
                tooltip=["filiere:N", alt.Tooltip("annee_str:O"), alt.Tooltip("gw:Q", format=",.1f")],
            ).properties(height=420, title="Évolution du parc installé par filière")
        )
    st.altair_chart(chart_k, use_container_width=True)

    if "nature" in dfk.columns and dfk["nature"].str.contains("incompl", case=False, na=False).any():
        st.caption("🟠 Année incomplète (selon le fichier).")

# ===== TAB 3: Installations (map) =====
with tabs[2]:
    dfi = load_installations_mongo()

    color_map = {
        "Hydraulique": "#1E88E5",
        "Thermique renouvelable et déchets": "#2E7D32",
        "Thermique fossile": "#BDBDBD",
        "Nucléaire": "#F1C40F",
    }
    dfi["filiere_norm"] = dfi["filiere"].replace({
        "Hydroélectrique": "Hydraulique",
        "Thermique renouvelable": "Thermique renouvelable et déchets",
        "Thermique renouvelable et dechets": "Thermique renouvelable et déchets",
        "Nucleaire": "Nucléaire",
        "Eolien": "Éolien",
        "Solaire": "Solaire",
    })

    bins = [50, 1000, 2000, 3000, 4000, 10000]
    labels = ["50MW - 999MW","1000MW - 1999MW","2000MW - 2999MW","3000MW - 3999MW","4000MW - 10000MW"]
    dfi = dfi[dfi["mw"] >= 50]
    dfi["classe_mw"] = pd.cut(dfi["mw"], bins=bins, right=True, labels=labels, include_lowest=True)

    fils_all = [f for f in color_map.keys() if f in set(dfi["filiere_norm"])]
    sel_fils = st.multiselect("Filières", fils_all, default=fils_all)
    classes_all = labels
    sel_classes = st.multiselect("Classes de puissance (MW)", classes_all, default=classes_all)

    dfv = dfi[dfi["filiere_norm"].isin(sel_fils) & dfi["classe_mw"].isin(sel_classes)].copy()

    m = folium.Map(location=[46.6, 2.5], zoom_start=5, tiles="cartodbpositron")

    def radius_from_mw(mw):
        r = math.sqrt(float(mw)) * 0.25
        return max(4, min(28, r))

    for _, row in dfv.iterrows():
        lat, lon = float(row["latitude"]), float(row["longitude"])
        fil = row["filiere_norm"]
        color = color_map.get(fil, "#666666")
        r = radius_from_mw(row["mw"])
        name = row.get("nom", "")
        cap = f"{row['mw']:.0f} MW"
        folium.CircleMarker(
            location=[lat, lon],
            radius=r,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            weight=1,
            popup=folium.Popup(f"<b>{name}</b><br>{fil}<br>{cap}", max_width=260),
        ).add_to(m)

    st_folium(m, height=650, width=None)

# ===== TAB 4: Solaire & Éolien (département) =====
with tabs[3]:
    dsw = load_solar_wind_mongo()

    color_map_sw = {"Éolien": "#26A69A", "Solaire": "#F39C12"}
    bins_sw = [0, 500, 1000, 1500, 2000, 4000]
    labels_sw = ["0MW - 499MW","500MW - 999MW","1000MW - 1499MW","1500MW - 1999MW","2000MW - 4000MW"]
    dsw["classe_mw"] = pd.cut(dsw["mw"], bins=bins_sw, right=True, labels=labels_sw, include_lowest=True)

    col1, col2 = st.columns(2)
    with col1:
        fils_avail = [f for f in ["Éolien","Solaire"] if f in set(dsw["filiere"])]
        sel_fils = st.multiselect("Filières", fils_avail, default=fils_avail)
    with col2:
        sel_classes = st.multiselect("Classes de puissance (MW)", labels_sw, default=labels_sw)

    dmap = dsw[dsw["filiere"].isin(sel_fils) & dsw["classe_mw"].isin(sel_classes)].copy()

    m = folium.Map(location=[46.6, 2.5], zoom_start=5, tiles="cartodbpositron")

    def radius_from_mw_sw(mw):
        r = math.sqrt(float(mw)) * 0.18
        return max(4, min(20, r))

    for _, row in dmap.iterrows():
        lat, lon = float(row["latitude"]), float(row["longitude"])
        fil = row["filiere"]
        color = color_map_sw.get(fil, "#999999")
        r = radius_from_mw_sw(row["mw"])
        name = row.get("nom", "")
        cap = f"{row['mw']:.0f} MW"
        folium.CircleMarker(
            location=[lat, lon],
            radius=r,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=1,
            popup=folium.Popup(f"<b>{name}</b><br>{fil}<br>{cap}", max_width=260),
        ).add_to(m)

    st_folium(m, height=650, width=None)

    if "nature" in dsw.columns and dsw["nature"].str.contains("provisoire", case=False, na=False).any():
        st.caption("🟠 Données provisoires.")
