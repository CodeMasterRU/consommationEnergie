# hypotheses/Region_stat_tests.py

import pandas as pd
from scipy import stats
import statsmodels.api as sm
import os

# === 1. Загрузка данных ===
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, '..', 'streamlitApp', 'data', 'enedis_region_data.csv')
df = pd.read_csv(csv_path)

# === 2. Предобработка ===
# Убираем строки без нужных данных
df = df.dropna(subset=["conso_totale_mwh", "nombre_d_habitants"])

# Добавляем показатель "потребление на жителя"
df["conso_par_habitant"] = df["conso_totale_mwh"] / df["nombre_d_habitants"]

# Индекс "возраста жилья" = средневзвешенное по эпохам строительства
df["age_logement_indice"] = (
    df["residences_principales_avant_1919"] * 100 +
    df["residences_principales_de_1919_a_1945"] * 80 +
    df["residences_principales_de_1946_a_1970"] * 60 +
    df["residences_principales_de_1971_a_1990"] * 40 +
    df["residences_principales_de_1991_a_2005"] * 20 +
    df["residences_principales_de_2006_a_2015"] * 10 +
    df["residences_principales_apres_2016"] * 5
)

# === 3. H1 : Climat ↔ Consommation (DJU vs consommation/hab) ===
print("=== H1 : Climat ↔ Consommation ===")
if "dju_a_tr" in df.columns:
    r, p = stats.pearsonr(df["dju_a_tr"], df["conso_par_habitant"])
    print(f"r = {r:.3f}, p = {p:.4f}")
else:
    print("⚠️ Колонка dju_a_tr отсутствует в данных региона")

# === 4. H2 : Chauffage électrique ↔ Consommation ===
print("\n=== H2 : Chauffage électrique ↔ Consommation ===")
if "taux_de_chauffage_electrique" in df.columns:
    r, p = stats.pearsonr(df["taux_de_chauffage_electrique"], df["conso_par_habitant"])
    print(f"r = {r:.3f}, p = {p:.4f}")
else:
    print("⚠️ Колонка taux_de_chauffage_electrique отсутствует в данных региона")

# === 5. H3 : Régression âge logement ↔ consommation ===
print("\n=== H3 : Régression âge logement ↔ consommation ===")
X = df[["age_logement_indice"]].fillna(0)
X = sm.add_constant(X)
y = df["conso_par_habitant"].fillna(0)

model = sm.OLS(y, X).fit()
print(model.summary())
