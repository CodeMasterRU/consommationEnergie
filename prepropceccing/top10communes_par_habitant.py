import pandas as pd
import matplotlib.pyplot as plt

commune_data_path = "./DataEnedis10_000/enedis_commune_data.csv"
geo_path = "20230823-communes-departement-region.csv"

df_conso = pd.read_csv(commune_data_path)
df_geo = pd.read_csv(geo_path)

df_conso['code_commune'] = df_conso['code_commune'].astype(str).str.zfill(5)
df_geo['code_commune_INSEE'] = df_geo['code_commune_INSEE'].astype(str).str.zfill(5)

df = df_conso.merge(
    df_geo[['code_commune_INSEE', 'latitude', 'longitude']],
    left_on='code_commune',
    right_on='code_commune_INSEE',
    how='left'
)

df['conso_totale_mwh'] = pd.to_numeric(df['conso_totale_mwh'], errors='coerce')
df['nombre_d_habitants'] = pd.to_numeric(df['nombre_d_habitants'], errors='coerce')
df = df.dropna(subset=['latitude', 'longitude', 'conso_totale_mwh', 'nombre_d_habitants'])
df = df[df['nombre_d_habitants'] > 0]

df['conso_par_habitant'] = df['conso_totale_mwh'] / df['nombre_d_habitants']

secteurs = df.groupby("code_grand_secteur")["conso_totale_mwh"].sum().sort_values(ascending=False)

plt.figure(figsize=(10, 6))
secteurs.plot(kind="bar", color="skyblue")
plt.title("Consommation totale par secteur d'activité (MWh)")
plt.ylabel("Consommation totale (MWh)")
plt.xlabel("Secteur")
plt.xticks(rotation=45)
plt.grid(axis='y')
plt.tight_layout()
plt.show()


top10_communes = df[['nom_commune', 'code_commune', 'conso_par_habitant']].sort_values(
    by='conso_par_habitant', ascending=False
).drop_duplicates().head(10)

print("Top 10 communes par consommation moyenne par habitant (MWh):")
print(top10_communes.to_string(index=False))
