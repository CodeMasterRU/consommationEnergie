# pages/energie_analyse.py
import streamlit as st
from pathlib import Path
from Data_Analysis import (
    load_data, CSV_PATH,
    plot_energy_consumption_by_source,
    plot_energy_consumption_over_time,
    plot_energy_co2_relation,
    plot_correlation_heatmap,
    boxplot_energy_consumption,
    violinplot_energy_consumption,
    year_with_highest_consumption,
    plot_consumption_by_year,
)

st.title("📊 Analyse nationale – eco2mix")

# Chargement des données
df = load_data(CSV_PATH)

option = st.sidebar.selectbox(
    "Choisissez le graphique à afficher :",
    (
        "Consommation par source",
        "Consommation au fil du temps",
        "Relation énergie-CO2",
        "Heatmap de corrélation",
        "Boxplot de la consommation",
        "Consommation par année",
        "Violon de la consommation",
    )
)

if option == "Consommation par source":
    plot_energy_consumption_by_source(df)

elif option == "Consommation au fil du temps":
    plot_energy_consumption_over_time(df)

elif option == "Relation énergie-CO2":
    plot_energy_co2_relation(df)

elif option == "Heatmap de corrélation":
    plot_correlation_heatmap(df)

elif option == "Boxplot de la consommation":
    boxplot_energy_consumption(df)

elif option == "Consommation par année":
    max_row, df_year = year_with_highest_consumption(df)
    plot_consumption_by_year(df_year, max_row)

elif option == "Violon de la consommation":
    violinplot_energy_consumption(df)



#HEATMAP DE CORRELATION
# 🔎 1. Corrélation avec la consommation
# Consommation ↔ prévision_j : très forte corrélation positive (≈ 1.0). Это логично — прогнозы (prévision_j, prévision_j-1) построены именно на основе consommation réelle.
# Consommation ↔ gaz, nucléaire, hydraulique : corrélation assez élevée (0.6–0.7). → То есть основное покрытие потребления обеспечивается именно этими источниками.
# Consommation ↔ fioul, charbon : corrélation faible ou légèrement positive. → Они не являются основными драйверами, больше «d’appoint».
# 🔎 2. Corrélation entre les sources de production
# Gaz ↔ taux de CO2 : forte corrélation positive (≈ 0.77). → Когда возрастает потребление газа, выбросы CO2 растут.
# Charbon ↔ taux de CO2 : aussi corrélation positive (≈ 0.55). → Подтверждает, что fossiles = gros pollueurs.
# Nucléaire ↔ consommation : correlation élevée (≈ 0.66), mais faible corrélation avec CO2. → Подтверждает, что nucléaire — базовая нагрузка, но «bas-carbone».
# 🔎 3. Corrélation entre les échanges commerciaux et production
# Некоторые échanges commerciaux (ex: ech_comm_allemagne, ech_comm_espagne) montrent des corrélations avec certaines productions (gaz, nucléaire).
# 👉 Cela peut refléter l’équilibre du réseau : quand la France produit beaucoup de nucléaire, elle exporte. Quand la demande augmente (consommation), certaines importations (gaz, charbon) montent.
# 🔎 4. Insights plus stratégiques
# Décarbonation : réduire la dépendance au gaz/charbon impacte directement les émissions (corrélation forte avec CO2).
# Sécurité énergétique : la consommation est couverte surtout par le nucléaire, le gaz et l’hydraulique.
# Export/import : certaines variations de consommation influencent directement les échanges transfrontaliers.
