import requests
import pandas as pd
import time

# Параметры API
BASE_URL = "https://data.enedis.fr/api/explore/v2.1/catalog/datasets/consommation-electrique-par-secteur-dactivite-epci/records"
LIMIT = 100
OFFSET = 0
all_records = []

print("⏳ Загрузка данных consommation par secteur EPCI...")

while True:
    params = {
        "limit": LIMIT,
        "offset": OFFSET
    }

    response = requests.get(BASE_URL, params=params)

    if response.status_code != 200:
        print(f"❌ Ошибка на offset={OFFSET}: {response.status_code}")
        break

    data = response.json().get("results", [])

    if not data:
        print("✅ Данные закончились.")
        break

    all_records.extend(data)
    OFFSET += LIMIT

    print(f"📦 Загружено {OFFSET} записей...")
    time.sleep(0.3)

# Сохраняем
df = pd.DataFrame(all_records)
df.to_csv("enedis_epci_data.csv", index=False)

print("✅ Готово! Данные сохранены в 'enedis_data_epci.csv'")
