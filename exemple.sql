from pymongo import MongoClient

-- Pour les test en local
client = MongoClient("mongodb://localhost:27017/")


-- Pour les tests en Cloud
client = MongoClient("mongodb://myuser:mypassword@localhost:27017/my_database")

db = client["my_database"]

pipeline = [
    {
        "$lookup": {
            "from": "departements",
            "localField": "code_insee",
            "foreignField": "code_insee",
            "as": "dep_info"
        }
    },
    {"$unwind": "$dep_info"},
    {
        "$group": {
            "_id": "$dep_info.nom_departement",
            "consommation_totale": {"$sum": "$conso_mwh"},
            "conso_par_habitant": {
                "$sum": {"$divide": ["$conso_mwh", "$dep_info.population"]}
            }
        }
    }
]

result = db["consommation_commune"].aggregate(pipeline)

for r in result:
    print(r)