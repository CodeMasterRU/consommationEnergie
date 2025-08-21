import pandas as pd
import matplotlib.pyplot as plt

# --- пути к данным ---
commune_data_path = "./streamlitApp/data/enedis_commune_data.csv"
geo_path = "./streamlitApp/data/20230823-communes-departement-region.csv"  # нужен только если хочешь координаты

# --- загрузка ---
df_conso = pd.read_csv(commune_data_path)

# (опционально) координаты — для карт, НЕ для диаграммы по секторам
try:
    df_geo = pd.read_csv(geo_path)
    df_conso["code_commune"] = df_conso["code_commune"].astype(str).str.zfill(5)
    df_geo["code_commune_INSEE"] = df_geo["code_commune_INSEE"].astype(str).str.zfill(5)
    df_conso = df_conso.merge(
        df_geo[["code_commune_INSEE", "latitude", "longitude"]],
        left_on="code_commune",
        right_on="code_commune_INSEE",
        how="left",
    )
except FileNotFoundError:
    pass  # если файла с гео нет — просто продолжаем без координат

# --- приведение типов ---
df_conso["conso_totale_mwh"] = pd.to_numeric(df_conso["conso_totale_mwh"], errors="coerce")
df_conso["nombre_d_habitants"] = pd.to_numeric(df_conso.get("nombre_d_habitants"), errors="coerce")

# Нормализуем названия секторов (на всякий случай)
df_conso["code_grand_secteur"] = df_conso["code_grand_secteur"].astype(str).str.strip().str.title()

# =========================
# 1) Диаграмма: суммарное потребление по секторам
#    НЕ фильтруем по населению/координатам, только по наличию потребления
# =========================
secteurs = (
    df_conso.dropna(subset=["conso_totale_mwh"])
           .groupby("code_grand_secteur", as_index=False)["conso_totale_mwh"].sum()
           .sort_values("conso_totale_mwh", ascending=False)
)

plt.figure(figsize=(10, 6))
plt.bar(secteurs["code_grand_secteur"], secteurs["conso_totale_mwh"])
plt.title("Consommation totale par secteur d'activité (MWh)")
plt.ylabel("Consommation totale (MWh)")
plt.xlabel("Secteur")
plt.xticks(rotation=30, ha="right")
plt.grid(axis="y")
plt.tight_layout()
plt.show()

print("Сектора в исходных данных:", sorted(df_conso["code_grand_secteur"].unique()))

# =========================
# 2) Топ-10 коммун по потреблению на человека
#    Корректно считается только для RESIDENTIEL (там есть население)
# =========================
mask_res = df_conso["code_grand_secteur"].str.upper() == "RESIDENTIEL"
df_res = df_conso.loc[mask_res].copy()

df_res = df_res[
    df_res["conso_totale_mwh"].notna()
    & df_res["nombre_d_habitants"].notna()
    & (df_res["nombre_d_habitants"] > 0)
]

df_res["conso_par_habitant"] = df_res["conso_totale_mwh"] / df_res["nombre_d_habitants"]

top10_communes = (
    df_res[["nom_commune", "code_commune", "conso_par_habitant"]]
    .drop_duplicates()
    .sort_values(by="conso_par_habitant", ascending=False)
    .head(10)
)

print("\nTop 10 communes par consommation moyenne par habitant (MWh) — secteur Résidentiel:")
print(top10_communes.to_string(index=False))