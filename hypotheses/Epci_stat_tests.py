import pandas as pd
from scipy.stats import ttest_ind, pearsonr
import statsmodels.api as sm
import os

# === 1. Загрузка данных ===
# Здесь ты вставишь путь к своему CSV, который содержит все нужные данные
# Например: conso, population, revenu_moyen, annee_construction, temp_moy
base_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(base_dir, '..', 'streamlitApp', 'data', 'enedis_epci_data.csv')
df = pd.read_csv(csv_path)

# === 2. Переменные ===
df["conso_par_habitant"] = df["conso_totale_mwh"] / df["nombre_d_habitants"]

# Определим климат как холодный/теплый (по медиане DJU)
df["climat"] = df["dju_a_tr"].apply(lambda x: "froid" if x >= df["dju_a_tr"].median() else "chaud")

# Средний возраст жилья (примерная метрика на основе долей)
df["age_logement_indice"] = (
    df["residences_principales_avant_1919"] * 100 +
    df["residences_principales_de_1919_a_1945"] * 80 +
    df["residences_principales_de_1946_a_1970"] * 60 +
    df["residences_principales_de_1971_a_1990"] * 40 +
    df["residences_principales_de_1991_a_2005"] * 20 +
    df["residences_principales_de_2006_a_2015"] * 10 +
    df["residences_principales_apres_2016"] * 5
)

# === 3. Тест H1 : Climat vs consommation ===
cold = df[df["climat"] == "froid"]["conso_par_habitant"].dropna()
hot = df[df["climat"] == "chaud"]["conso_par_habitant"].dropna()

t_stat, p_val = ttest_ind(cold, hot, nan_policy="omit")
print("=== H1 : Climat ↔ Consommation ===")
print(f"T = {t_stat:.3f}, p = {p_val:.4f}")
print("✅ Значимые различия" if p_val < 0.05 else "❌ Нет значимых различий", "\n")

# === 4. Тест H2 : Chauffage électrique vs consommation ===
r, p = pearsonr(df["taux_de_chauffage_electrique"].dropna(), df["conso_par_habitant"].dropna())
print("=== H2 : Chauffage électrique ↔ Consommation ===")
print(f"r = {r:.3f}, p = {p:.4f}")
print("✅ Корреляция значима" if p < 0.05 else "❌ Корреляции не выявлено", "\n")

# === 5. Тест H3 : Age logement vs consommation ===
X = sm.add_constant(df["age_logement_indice"])
y = df["conso_par_habitant"]
model = sm.OLS(y, X, missing="drop").fit()
print("=== H3 : Régression âge logement ↔ consommation ===")
print(model.summary())
