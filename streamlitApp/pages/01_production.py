import os
import glob
import pandas as pd
import streamlit as st
import altair as alt
from ast import literal_eval
import json
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="⚙️ Production & Parc – France", layout="wide")
st.title("⚙️ Production & Parc installé – Synthèse (type RTE)")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ---------- Утилиты ----------
def _find_csv(candidates, fallback_patterns=None):
    paths = [os.path.join(DATA_DIR, n) for n in candidates if os.path.exists(os.path.join(DATA_DIR, n))]
    if paths:
        # если несколько — берём самый свежий
        paths = sorted(paths, key=lambda p: os.path.getmtime(p), reverse=True)
        return paths[0]
    if fallback_patterns:
        found = []
        for pat in fallback_patterns:
            found += glob.glob(os.path.join(DATA_DIR, pat))
        if found:
            found = sorted(found, key=lambda p: os.path.getmtime(p), reverse=True)
            return found[0]
    return None

def _parse_number_fr(s: pd.Series) -> pd.Series:
    return (
        s.astype(str)
         .str.replace("\u202f", "", regex=False)  # thin NBSP
         .str.replace(" ", "", regex=False)
         .str.replace(",", ".", regex=False)
         .pipe(pd.to_numeric, errors="coerce")
    )

# ---------- Загрузка ПРОИЗВОДСТВА (TWh) ----------
PROD_CANDIDATES = [
    "Évolution de la production d'électricité en France.csv",
    "Evolution de la production d'electricite en France.csv",
    "evolution_production_france.csv",
    "production_france.csv",
]

PROD_FALLBACK = ["*production*.csv", "*Évolution*production*.csv", "*evolution*production*.csv"]
PROD_PATH = _find_csv(PROD_CANDIDATES, PROD_FALLBACK)

@st.cache_data
def load_production_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df.columns = [c.strip() for c in df.columns]
    df = df.rename(columns={
        "Date": "date",
        "Filière": "filiere",
        "Valeur (TWh)": "twh",
        "Nature": "nature",
    })
    if not {"date","filiere","twh"}.issubset(df.columns):
        raise ValueError("Файл с производством должен содержать колонки: Date, Filière, Valeur (TWh).")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["twh"] = _parse_number_fr(df["twh"])
    df["annee"] = df["date"].dt.year
    df["mois"]  = df["date"].dt.month
    df["mois_txt"] = df["date"].dt.strftime("%b")
    return df.dropna(subset=["date","twh","filiere"])

# ---------- Загрузка ПАРКА (GW) ----------
PARK_CANDIDATES = [
    "Évolution du parc installé de production d'électricité en France.csv",
    "Evolution du parc installe de production d'electricite en France.csv",
    "parc_installe_france.csv",
    "capacite_installee_france.csv",
]
PARK_FALLBACK = ["*parc*install*.csv", "*capacite*instal*.csv", "*GW*.csv"]
PARK_PATH = _find_csv(PARK_CANDIDATES, PARK_FALLBACK)

@st.cache_data
def load_park_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df.columns = [c.strip() for c in df.columns]

    # Имена колонок
    rename = {
        "Date": "date",
        "Année": "date",
        "Filière": "filiere",
        "Valeur (GW)": "gw",
        "Puissance (GW)": "gw",
        "Puissance installée (GW)": "gw",
        "Nature": "nature",
    }
    
    for k, v in list(rename.items()):
        if k in df.columns:
            df = df.rename(columns={k: v})

    if "date" not in df.columns:
        raise ValueError("Файл парка должен содержать 'Date'/'Année'.")

    # ---- ВАЖНО: корректный разбор года ----
    s = df["date"].astype(str).str.strip()
    if s.str.fullmatch(r"\d{4}").all():
        # только год (2007, 2008, …)
        df["date"] = pd.to_datetime(s, format="%Y", errors="coerce")
    else:
        # на всякий случай: если вдруг там YYYY-MM или даты
        df["date"] = pd.to_datetime(s, errors="coerce")

    # Значения GW (французская запятая -> точка)
    df["gw"] = (
        df["gw"].astype(str)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # Филиеры + флаг total (если такие строки есть в других версиях csv)
    df["filiere"] = df.get("filiere", "Total").astype(str).str.strip()
    df["is_total"] = df["filiere"].str.contains(
        r"Puissance\s+installée\s+totale", case=False, na=False
    )

    # Год и строковая версия года — используем ТОЛЬКО их на оси X
    df["annee"] = df["date"].dt.year
    df["annee_str"] = df["annee"].astype("Int64").astype(str)

    return df.dropna(subset=["date", "gw"])

# ---------- Загрузка КАРТЫ УСТАНОВОК (MW) ----------
INSTALL_CANDIDATES = [
    "Répartition des principales installations de production d'électricité en France, hors solaire et éolien.csv",
    "Repartition des principales installations de production d'electricite en France, hors solaire et eolien.csv",
    "installations_production_france.csv",
    "sites_production_principaux.csv",
]
INSTALL_FALLBACK = ["*installation*production*.csv", "*sites*production*.csv", "*hors*eolien*solaire*.csv"]
INSTALL_PATH = _find_csv(INSTALL_CANDIDATES, INSTALL_FALLBACK)

def _parse_geo_point(val):
    if pd.isna(val):
        return pd.Series([None, None])
    try:
        if isinstance(val, str) and val.strip().startswith("{"):
            d = literal_eval(val)
        elif isinstance(val, str) and (":" in val and "lat" in val.lower()):
            d = json.loads(val)
        else:
            return pd.Series([None, None])
        return pd.Series([d.get("lat") or d.get("Latitude"), d.get("lon") or d.get("Longitude")])
    except Exception:
        return pd.Series([None, None])

@st.cache_data
def load_installations_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df.columns = [c.strip() for c in df.columns]

    # возможные заголовки
    rename = {
        "Filière": "filiere",
        "Filiere": "filiere",
        "Type": "filiere",
        "Puissance (MW)": "mw",
        "Puissance MW": "mw",
        "Valeur (MW)": "mw",
        "Nom": "nom",
        "Nom site": "nom",
        "Latitude": "latitude",
        "Longitude": "longitude",
    }
    for k, v in list(rename.items()):
        if k in df.columns:
            df = df.rename(columns={k: v})

    # координаты: пытаемся извлечь
    if "latitude" not in df.columns or "longitude" not in df.columns:
        cand = [c for c in df.columns if "geo_point" in c.lower() or "geom" in c.lower()]
        if cand:
            latlon = df[cand[0]].apply(_parse_geo_point)
            df[["latitude", "longitude"]] = latlon

    # чистим мощность (французская запись)
    if "mw" not in df.columns:
        # пытаемся найти колонку со словом MW/puissance
        for c in df.columns:
            if "mw" in c.lower() or "puissance" in c.lower() or "valeur" in c.lower():
                df = df.rename(columns={c: "mw"})
                break
    df["mw"] = (
        df["mw"].astype(str)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # финальные столбцы
    df["filiere"] = df.get("filiere", "Inconnue").astype(str).str.strip()
    df = df.dropna(subset=["latitude", "longitude", "mw"])
    return df
# ---------- Загрузка карты Solaire & Éolien ----------
SW_CANDIDATES = [
    "Répartition des installations de production d'électricité solaire et éolienne en France, à la maille départementale.csv",
    "Repartition des installations de production d'electricite solaire et eolienne en France, a la maille departementale.csv",
    "installations_solaire_eolien_departement.csv",
]
SW_FALLBACK = ["*solaire*eolien*depart*.csv", "*eolien*solaire*.csv"]

@st.cache_data
def load_solar_wind_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";")
    df.columns = [c.strip() for c in df.columns]

    # нормализация заголовков
    rename = {
        "Filière": "filiere",
        "Filiere": "filiere",
        "Type": "filiere",
        "Puissance (MW)": "mw",
        "Puissance MW": "mw",
        "Valeur (MW)": "mw",
        "Nom": "nom",
        "Nom site": "nom",
        "Latitude": "latitude",
        "Longitude": "longitude",
        "Nature": "nature",
    }
    for k, v in list(rename.items()):
        if k in df.columns:
            df = df.rename(columns={k: v})

    # координаты (если приходят одним полем вроде geo_point_2d)
    if "latitude" not in df.columns or "longitude" not in df.columns:
        cand = [c for c in df.columns if "geo_point" in c.lower() or "geom" in c.lower()]
        if cand:
            def _parse_geo_point(val):
                if pd.isna(val): return pd.Series([None, None])
                try:
                    d = literal_eval(val) if isinstance(val, str) and val.strip().startswith("{") else json.loads(val)
                    return pd.Series([d.get("lat") or d.get("Latitude"), d.get("lon") or d.get("Longitude")])
                except Exception:
                    return pd.Series([None, None])
            df[["latitude", "longitude"]] = df[cand[0]].apply(_parse_geo_point)

    # мощность → число
    if "mw" not in df.columns:
        for c in df.columns:
            if "mw" in c.lower() or "puissance" in c.lower() or "valeur" in c.lower():
                df = df.rename(columns={c: "mw"})
                break
    df["mw"] = (
        df["mw"].astype(str)
        .str.replace("\u202f", "", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
    )

    # нормализация филиер
    repl = {"Eolien": "Éolien", "eolien": "Éolien", "Solaire": "Solaire", "solaire":"Solaire"}
    df["filiere"] = df.get("filiere", "Inconnue").astype(str).str.strip().replace(repl)

    # убираем пустые координаты/мощности
    df = df.dropna(subset=["latitude", "longitude", "mw"])
    return df


# ---------- Табы ----------
tabs = st.tabs([
    "📊 Production (TWh)",
    "🏗️ Parc installé (GW)",
    "🗺️ Installations (carte)",
    "🗺️ Solaire & Éolien (département)"
])

# ======== TAB 1: Production (TWh) ========
with tabs[0]:
    if not PROD_PATH:
        st.warning("В `data/` не найден файл с производством (TWh). Положи, например: "
                   "`Évolution de la production d'électricité en France.csv`.")
        st.stop()

    st.caption(f"Файл производства: `{os.path.basename(PROD_PATH)}`")
    try:
        dfp = load_production_csv(PROD_PATH)
    except Exception as e:
        st.error(f"Ошибка чтения файла производства: {e}")
        st.stop()

    colA, colB = st.columns(2)
    with colA:
        period_mode = st.toggle("Annuel / Mensuel", value=True, help="Вкл = годовой, выкл = помесячный")
    with colB:
        global_mode = st.toggle("Global / Filière", value=True, help="Вкл = сумма, выкл = по филиерам (stack)")

    all_fils = sorted(dfp["filiere"].dropna().unique())
    selected_fils = st.multiselect("Filières", all_fils, default=all_fils)
    dfp = dfp[dfp["filiere"].isin(selected_fils)]

    annual = dfp.groupby(["annee","filiere"], as_index=False)["twh"].sum().sort_values(["annee","filiere"])
    monthly = dfp.copy()

    if not period_mode:
        years_avail = sorted(monthly["annee"].unique())
        year_pick = st.selectbox("Année", years_avail, index=len(years_avail)-1 if years_avail else 0)
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
            # заполняем отсутствующие месяцы нулями
            reidx = pd.MultiIndex.from_product([[year], range(1,13)], names=["annee","mois"])
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


# ======== TAB 2: Parc installé (GW) ========
with tabs[1]:
    if not PARK_PATH:
        st.warning("Файл парка (GW) не найден в `data/`.")
        st.stop()

    st.caption(f"Файл парка: `{os.path.basename(PARK_PATH)}`")
    try:
        dfk = load_park_csv(PARK_PATH)  # в этой функции уже есть dfk['is_total'], dfk['annee']
    except Exception as e:
        st.error(f"Ошибка чтения файла парка: {e}")
        st.stop()

    # режимы: хотим по умолчанию 'Filière' (stacked), как на твоём референсе
    global_mode_gw = st.toggle(
        "Global / Filière (GW)",
        value=False,
        help="Вкл = суммарная мощность (total); выкл = по филиерам (стек)."
    )

    # нормализуем названия и исключим total из стека
    dfk["filiere"] = dfk["filiere"].astype(str).str.strip()
    dfk_no_total = dfk[~dfk["is_total"]].copy()

    # год как строка — ключевой фикс, чтобы Altair не делал «1970»
    dfk_no_total["annee_str"] = dfk_no_total["annee"].astype("Int64").astype(str)
    dfk["annee_str"]       = dfk["annee"].astype("Int64").astype(str)

    # порядок/цвета филиер (можешь подогнать под свой файл)
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

    # годовая агрегация
    annual_k = (
        dfk_no_total.groupby(["annee_str", "filiere"], as_index=False)["gw"]
        .sum()
        .sort_values(["annee_str", "filiere"])
    )

    if global_mode_gw:
        # если есть официальный ряд total — используем его; иначе сумма филиер
        total_rows = dfk[dfk["is_total"]].copy()
        if not total_rows.empty:
            data = total_rows.groupby("annee_str", as_index=False)["gw"].sum()
        else:
            data = annual_k.groupby("annee_str", as_index=False)["gw"].sum()

        chart_k = (
            alt.Chart(data)
            .mark_bar()
            .encode(
                x=alt.X("annee_str:O", title="Année", sort="ascending"),
                y=alt.Y("gw:Q", title="Puissance installée (GW)"),
                tooltip=[alt.Tooltip("annee_str:O"), alt.Tooltip("gw:Q", format=",.1f")],
            )
            .properties(height=420, title="Évolution du parc installé (total)")
        )
    else:
        # stacked par filière — как на второй/третьей картинке
        chart_k = (
            alt.Chart(annual_k)
            .mark_bar()
            .encode(
                x=alt.X("annee_str:O", title="Année", sort="ascending"),
                y=alt.Y("gw:Q", title="Puissance installée (GW)", stack="zero"),
                color=alt.Color(
                    "filiere:N",
                    title="Filière",
                    scale=alt.Scale(domain=filiere_order, range=filiere_colors),
                    sort=filiere_order,
                ),
                order=alt.Order("filiere:N", sort="descending"),
                tooltip=["filiere:N", alt.Tooltip("annee_str:O"), alt.Tooltip("gw:Q", format=",.1f")],
            )
            .properties(height=420, title="Évolution du parc installé par filière")
        )

    st.altair_chart(chart_k, use_container_width=True)

    if "nature" in dfk.columns and dfk["nature"].str.contains("incompl", case=False, na=False).any():
        st.caption("🟠 Année incomplète (selon le fichier).")

with tabs[2]:
    if not INSTALL_PATH:
        st.warning("В `data/` не найден файл с установками. Помести, напр.: "
                   "`Répartition des principales installations de production d'électricité en France, hors solaire et éolien.csv`.")
        st.stop()

    st.caption(f"Файл установок: `{os.path.basename(INSTALL_PATH)}`")
    try:
        dfi = load_installations_csv(INSTALL_PATH)
    except Exception as e:
        st.error(f"Ошибка чтения файла установок: {e}")
        st.stop()

    # цвета под стиль RTE
    color_map = {
        "Hydraulique": "#1E88E5",
        "Thermique renouvelable et déchets": "#2E7D32",
        "Thermique fossile": "#BDBDBD",
        "Nucléaire": "#F1C40F",
    }
    # если в файле другие надписи — нормализуем простым маппингом (опционально)
    dfi["filiere_norm"] = dfi["filiere"].replace({
        "Hydroélectrique": "Hydraulique",
        "Thermique renouvelable": "Thermique renouvelable et déchets",
        "Thermique renouvelable et dechets": "Thermique renouvelable et déchets",
        "Nucleaire": "Nucléaire",
        "Eolien": "Éolien",
        "Solaire": "Solaire",
    })

    # бинning по MW (как на скрине)
    bins = [50, 1000, 2000, 3000, 4000, 10000]
    labels = [
        "50MW - 999MW",
        "1000MW - 1999MW",
        "2000MW - 2999MW",
        "3000MW - 3999MW",
        "4000MW - 10000MW",
    ]
    dfi = dfi[dfi["mw"] >= 50]  # мелочь отсекаем
    dfi["classe_mw"] = pd.cut(dfi["mw"], bins=bins, right=True, labels=labels, include_lowest=True)

    # фильтры
    fils_all = [f for f in color_map.keys() if f in set(dfi["filiere_norm"])]
    sel_fils = st.multiselect("Filières", fils_all, default=fils_all)
    classes_all = labels
    sel_classes = st.multiselect("Classes de puissance (MW)", classes_all, default=classes_all)

    dfv = dfi[dfi["filiere_norm"].isin(sel_fils) & dfi["classe_mw"].isin(sel_classes)].copy()

    # карта Folium
    m = folium.Map(location=[46.6, 2.5], zoom_start=5, tiles="cartodbpositron")

    # масштаб радиуса по мощности: sqrt, ограничим
    def radius_from_mw(mw):
        import math
        r = math.sqrt(float(mw)) * 0.25  # подбери при желании
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


# ======== TAB 4: Solaire & Éolien (département) ========
with tabs[3]:
    SW_PATH = _find_csv(SW_CANDIDATES, SW_FALLBACK)
    if not SW_PATH:
        st.warning("В `data/` не найден CSV для solaire & éolien (département). "
                   "Положи файл: «Répartition des installations de production d'électricité solaire et éolienne en France, à la maille départementale.csv».")
        st.stop()

    st.caption(f"Файл: `{os.path.basename(SW_PATH)}`")
    try:
        dsw = load_solar_wind_csv(SW_PATH)
    except Exception as e:
        st.error(f"Ошибка чтения файла: {e}")
        st.stop()

    # Цвета в стиле RTE
    color_map_sw = {
        "Éolien":  "#26A69A",  # зелёно-бирюзовый
        "Solaire": "#F39C12",  # оранжевый
    }

    # Бины мощности (как на скрине)
    bins_sw = [0, 500, 1000, 1500, 2000, 4000]
    labels_sw = [
        "0MW - 499MW",
        "500MW - 999MW",
        "1000MW - 1499MW",
        "1500MW - 1999MW",
        "2000MW - 4000MW",
    ]
    dsw["classe_mw"] = pd.cut(dsw["mw"], bins=bins_sw, right=True, labels=labels_sw, include_lowest=True)

    # фильтры
    col1, col2 = st.columns(2)
    with col1:
        fils_avail = [f for f in ["Éolien","Solaire"] if f in set(dsw["filiere"])]
        sel_fils = st.multiselect("Filières", fils_avail, default=fils_avail)
    with col2:
        sel_classes = st.multiselect("Classes de puissance (MW)", labels_sw, default=labels_sw)

    dmap = dsw[dsw["filiere"].isin(sel_fils) & dsw["classe_mw"].isin(sel_classes)].copy()

    # карта
    m = folium.Map(location=[46.6, 2.5], zoom_start=5, tiles="cartodbpositron")

    def radius_from_mw_sw(mw):
        # компактнее, чем на «большой» карте — точки меньше, чтобы читалось
        import math
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

    # бейдж «Données provisoires» если есть такое поле
    if "nature" in dsw.columns and dsw["nature"].str.contains("provisoire", case=False, na=False).any():
        st.caption("🟠 Données provisoires.")