import requests
import pandas as pd
import time

# Параметры API
BASE_URL = "https://opendata.agenceore.fr/api/explore/v2.1/catalog/datasets/consommation-annuelle-d-electricite-et-gaz-par-departement/records"
LIMIT = 100
OFFSET = 0
all_records = []

print("⏳ Начинается загрузка данных по consommation électrique par secteur d'activité...")

while True:
    params = {
        "limit": LIMIT,
        "offset": OFFSET
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print(f"❌ Ошибка при запросе с offset={OFFSET}: {response.status_code}")
        break

    data = response.json().get("results", [])

    if not data:
        print("✅ Данные закончились.")
        break

    all_records.extend(data)
    OFFSET += LIMIT

    print(f"📦 Загружено {OFFSET} записей...")
    time.sleep(0.3)

# Преобразуем в DataFrame и сохраняем в CSV
df = pd.DataFrame(all_records)
df.to_csv("./DataAgenceORE/ORE_data_departement.csv", index=False)

print("✅ Готово! Данные сохранены в 'ORE_data_departement.csv'")
