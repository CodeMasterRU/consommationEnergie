import pandas as pd
import numpy as np
import os
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf

# Загружаем данные
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, '..', 'streamlitApp', 'data', 'enedis_departement_data.csv')
df = pd.read_csv(csv_path)

# === Подготовка переменных ===
# Нормируем потребление на жителя
df["conso_par_habitant"] = df["conso_totale_mwh"] / df["nombre_d_habitants"].replace(0, np.nan)

# Индекс возраста жилья: взвешенное среднее по годам постройки
age_vars = [
    ("residences_principales_avant_1919", 1910),
    ("residences_principales_de_1919_a_1945", 1930),
    ("residences_principales_de_1946_a_1970", 1960),
    ("residences_principales_de_1971_a_1990", 1980),
    ("residences_principales_de_1991_a_2005", 2000),
    ("residences_principales_de_2006_a_2015", 2010),
    ("residences_principales_apres_2016", 2020),
]

for col, year in age_vars:
    if col in df.columns:
        df[col] = df[col].fillna(0) * year

df["age_logement_indice"] = df[[c for c, _ in age_vars]].sum(axis=1) / df[[c for c, _ in age_vars]].replace(0, np.nan).count(axis=1)

# === H1 : Climat ↔ Consommation ===
# Берем DJU и потребление на жителя
df_h1 = df.dropna(subset=["dju_a_tr", "conso_par_habitant"])
corr_climat = stats.pearsonr(df_h1["dju_a_tr"], df_h1["conso_par_habitant"])
print("=== H1 : Climat ↔ Consommation ===")
print(f"r = {corr_climat[0]:.3f}, p = {corr_climat[1]:.4f}")

# === H2 : Chauffage électrique ↔ Consommation ===
df_h2 = df.dropna(subset=["taux_de_chauffage_electrique", "conso_par_habitant"])
corr_chauffage = stats.pearsonr(df_h2["taux_de_chauffage_electrique"], df_h2["conso_par_habitant"])
print("\n=== H2 : Chauffage électrique ↔ Consommation ===")
print(f"r = {corr_chauffage[0]:.3f}, p = {corr_chauffage[1]:.4f}")

# === H3 : Age logement ↔ Consommation ===
df_h3 = df.dropna(subset=["age_logement_indice", "conso_par_habitant"])
model = smf.ols("conso_par_habitant ~ age_logement_indice", data=df_h3).fit()
print("\n=== H3 : Régression âge logement ↔ consommation ===")
print(model.summary())