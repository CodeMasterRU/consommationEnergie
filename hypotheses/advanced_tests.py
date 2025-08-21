# -*- coding: utf-8 -*-
"""
Advanced statistical tests (OLS + VIF + χ²)
"""

import os
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

LEVEL_FILES = {
    "epci": "enedis_epci_data.csv",
    "departement": "enedis_departement_data.csv",
    "region": "enedis_region_data.csv",
}

# -------------------- PATH --------------------
def resolve_data_dir(cli_dir: str | None) -> Path:
    if cli_dir:
        return Path(cli_dir).expanduser().resolve()
    base_dir = Path(__file__).parent.resolve()
    guess1 = (base_dir / ".." / "streamlitApp" / "data").resolve()
    if guess1.exists():
        return guess1
    return Path.cwd().resolve()

def resolve_csv_path(level: str, data_dir: Path) -> Path:
    fn = LEVEL_FILES[level]
    candidate = (data_dir / fn).resolve()
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Not found {fn} in {data_dir}")

# -------------------- FEATURES --------------------
def build_age_index(df: pd.DataFrame) -> pd.DataFrame:
    """Nous construisons un indice d'âge des logements = 2025 - l'année moyenne pondérée de construction"""
    cols_years = [
        ("residences_principales_avant_1919", 1910),
        ("residences_principales_de_1919_a_1945", 1930),
        ("residences_principales_de_1946_a_1970", 1960),
        ("residences_principales_de_1971_a_1990", 1980),
        ("residences_principales_de_1991_a_2005", 2000),
        ("residences_principales_de_2006_a_2015", 2010),
        ("residences_principales_apres_2016", 2020),
    ]
    weights_sum = np.zeros(len(df))
    year_weighted_sum = np.zeros(len(df))

    for col, year in cols_years:
        if col in df.columns:
            vals = df[col].fillna(0).astype(float)
            weights_sum += vals.values
            year_weighted_sum += vals.values * year

    mean_year = np.where(weights_sum > 0, year_weighted_sum / weights_sum, np.nan)
    df["age_logement_indice"] = 2025 - mean_year
    return df

def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    df["conso_par_habitant"] = df["conso_totale_mwh"] / df["nombre_d_habitants"].replace(0, np.nan)
    med = df["dju_a_tr"].median(skipna=True) if "dju_a_tr" in df.columns else np.nan
    df["climat_categorie"] = np.where(df["dju_a_tr"] >= med, "froid", "chaud")
    return df

def vif_table(X_df: pd.DataFrame) -> pd.DataFrame:
    """Nous calculons le VIF et supprimons les fonctionnalités avec VIF>10"""
    X_df = X_df.dropna()
    while True:
        if X_df.shape[1] <= 1:
            break
        vifs = [variance_inflation_factor(X_df.values, i) for i in range(X_df.shape[1])]
        max_vif = max(vifs)
        if max_vif > 10:
            drop_col = X_df.columns[vifs.index(max_vif)]
            print(f"VIF>10 : supprimer {drop_col} (VIF={max_vif:.2f})")
            X_df = X_df.drop(columns=[drop_col])
        else:
            break
    return X_df

# -------------------- ANALYSIS --------------------
def multiple_regression(df: pd.DataFrame, label: str):
    df = build_age_index(df)
    df = add_targets(df)

    features = [f for f in ["dju_a_tr", "taux_de_chauffage_electrique", "age_logement_indice"] if f in df.columns]
    X_df = vif_table(df[features])
    if X_df.empty:
        print(f"[{label}] Aucun signe de régression.")
        return

    formula = "conso_par_habitant ~ " + " + ".join(X_df.columns)
    model = smf.ols(formula=formula, data=df).fit()
    print(f"\n=== Régression multiple [{label}] ===")
    print(model.summary())

def chi_square_tests(df: pd.DataFrame, label: str):
    df = add_targets(df)
    print(f"\n=== χ² tests [{label}] ===")

    if "code_grand_secteur" in df.columns:
        df = df.dropna(subset=["conso_par_habitant"])
        df["conso_level"] = pd.qcut(df["conso_par_habitant"], 3, labels=["bas", "moyen", "haut"])
        tab = pd.crosstab(df["code_grand_secteur"], df["conso_level"])
        if tab.shape[0] >= 2 and tab.shape[1] >= 2:
            chi2, p, dof, _ = chi2_contingency(tab)
            print("\n[χ²] code_grand_secteur ↔ niveau de consommation")
            print(tab)
            print(f"χ²={chi2:.2f}, ddl={dof}, p={p:.4f}")

    if "taux_de_chauffage_electrique" in df.columns:
        med_he = df["taux_de_chauffage_electrique"].median(skipna=True)
        df["chauffage_cat"] = np.where(df["taux_de_chauffage_electrique"] >= med_he, "élevé", "faible")
        tab2 = pd.crosstab(df["climat_categorie"], df["chauffage_cat"])
        if tab2.shape[0] >= 2 and tab2.shape[1] >= 2:
            chi2, p, dof, _ = chi2_contingency(tab2)
            print("\n[χ²] climat (chaud/froid) ↔ chauffage électrique (faible/élevé)")
            print(tab2)
            print(f"χ²={chi2:.2f}, ddl={dof}, p={p:.4f}")

# -------------------- MAIN --------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("level", choices=["epci", "departement", "region"])
    parser.add_argument("--data-dir", type=str, default=None)
    args = parser.parse_args()

    data_dir = resolve_data_dir(args.data_dir)
    csv_path = resolve_csv_path(args.level, data_dir)

    print(f"J'utilise: {csv_path}")
    df = pd.read_csv(csv_path).replace([np.inf, -np.inf], np.nan)

    multiple_regression(df, args.level.upper())
    chi_square_tests(df, args.level.upper())

if __name__ == "__main__":
    main()
