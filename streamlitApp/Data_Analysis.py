# Data_Analysis.py
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from statsmodels.tsa.arima.model import ARIMA

HERE = Path(__file__).resolve()
PROJECT_DIR = HERE.parent   # streamlitApp/
DATA_DIR = PROJECT_DIR / "data"
CSV_PATH = DATA_DIR / "eco2mix-national-tr.csv"

# ---------- LOAD ----------
@st.cache_data(show_spinner=False)
def load_data(path: Path) -> pd.DataFrame:
    """Charger eco2mix avec robustesse."""
    if not path.exists():
        matches = sorted(DATA_DIR.glob("eco2mix-national*.csv"))
        if matches:
            path = matches[-1]
        else:
            raise FileNotFoundError(f"Impossible de trouver {path}")

    for sep in (";", ",", None):
        try:
            df = pd.read_csv(path, sep=sep, encoding="utf-8", engine="python")
            break
        except Exception:
            continue

    df.columns = [c.strip().lower() for c in df.columns]
    rename = {
        "nucléaire": "nucleaire", "éolien": "eolien",
        "bioénergies": "bioenergies"
    }
    df = df.rename(columns=rename)

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    num_cols = [c for c in [
        "fioul","charbon","gaz","nucleaire","eolien","solaire",
        "hydraulique","pompage","bioenergies","consommation","taux_co2"
    ] if c in df.columns]

    for c in num_cols:
        df[c] = (df[c].astype(str)
                       .str.replace("\u202f", "", regex=False)
                       .str.replace(" ", "", regex=False)
                       .str.replace(",", ".", regex=False))
        df[c] = pd.to_numeric(df[c], errors="coerce")

    df = df.dropna(subset=["date", "consommation"])
    return df

# ---------- PLOTS ----------
def plot_energy_consumption_by_source(df):
    plt.figure(figsize=(10, 6))
    cols = [c for c in ["fioul","charbon","gaz","nucleaire","eolien",
                        "solaire","hydraulique","pompage","bioenergies"]
            if c in df.columns]
    total = df[cols].sum().sort_values(ascending=False)
    total.plot(kind="bar", color="skyblue")
    plt.title("Consommation d'énergie par source")
    plt.xlabel("Source d'énergie")
    plt.ylabel("Consommation (MW)")
    plt.xticks(rotation=45)
    st.pyplot(plt.gcf())

def plot_energy_consumption_over_time(df):
    plt.figure(figsize=(12, 6))
    s = df.sort_values("date")
    plt.plot(s["date"], s["consommation"], marker="o", linestyle="-")
    plt.title("Évolution de la consommation d'énergie")
    plt.xlabel("Date")
    plt.ylabel("Consommation (MW)")
    plt.xticks(rotation=45)
    st.pyplot(plt.gcf())

def plot_energy_co2_relation(df):
    if "taux_co2" not in df.columns:
        st.info("Pas de colonne 'taux_co2'")
        return
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x="consommation", y="taux_co2", s=25)
    plt.title("Relation consommation vs CO₂")
    st.pyplot(plt.gcf())

def plot_correlation_heatmap(df):
    """
    Интерактивная корреляционная матрица на Plotly:
    - hover показывает точные значения
    - можно зумить/панорамировать
    - нормальные подписи осей
    """
    # Оставляем только числовые колонки
    num_cols = [c for c in df.columns if df[c].dtype.kind in "fi"]
    if len(num_cols) < 2:
        st.info("Pas assez de colonnes numériques pour une corrélation.")
        return

    corr = df[num_cols].corr().round(2)

    fig = px.imshow(
        corr,
        text_auto=False,                 # не рисуем цифры в ячейках (hover их покажет)
        color_continuous_scale="RdBu_r", # привычная палитра кореляций
        zmin=-1, zmax=1,                 # симметричная шкала
        aspect="auto",
    )

    fig.update_layout(
        title="Matrice de corrélation (interactive)",
        margin=dict(l=40, r=20, t=60, b=40),
        coloraxis_colorbar=dict(title="corr"),
    )
    # Улучшим читаемость подписей осей
    fig.update_xaxes(side="bottom", tickangle=45, tickfont=dict(size=10))
    fig.update_yaxes(tickfont=dict(size=10), autorange="reversed")  # как у seaborn

    st.plotly_chart(fig, use_container_width=True)




def boxplot_energy_consumption(df):
    plt.figure(figsize=(10, 6))
    sns.boxplot(y=df["consommation"], color="skyblue")
    plt.title("Boîte à moustaches – consommation")
    st.pyplot(plt.gcf())

def violinplot_energy_consumption(df):
    plt.figure(figsize=(10, 6))
    sns.violinplot(y=df["consommation"], color="#A7C7E7")
    plt.title("Distribution de la consommation (violon)")
    st.pyplot(plt.gcf())

def year_with_highest_consumption(df):
    d = df.copy()
    d["year"] = d["date"].dt.year
    annual = d.groupby("year", as_index=False)["consommation"].sum()
    return annual.loc[annual["consommation"].idxmax()], annual

def plot_consumption_by_year(df_year, max_row):
    plt.figure(figsize=(12, 6))
    plt.plot(df_year["year"], df_year["consommation"], marker="o", linestyle="-")
    plt.scatter(max_row["year"], max_row["consommation"], color="red", label="Max")
    plt.title("Consommation annuelle")
    plt.legend()
    st.pyplot(plt.gcf())
