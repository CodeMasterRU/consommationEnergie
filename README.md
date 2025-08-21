# ProjetEnedis  
🔎 **Analyse de la consommation d'énergie en France**

---

## 🎯 Objectif du projet
Ce projet vise à analyser la consommation énergétique au niveau des **EPCI**, **départements** et **régions**.  
L’outil permet de :
- comparer les territoires ;
- identifier les facteurs influençant la consommation (climat, âge du logement, chauffage) ;
- fournir des recommandations pour la prise de décision publique.

---

## ⚙️ Installation

### 1. Cloner le projet
```bash
git clone https://github.com/votre_repo/consommationEnergie.git
cd consommationEnergie


### 2. Créer et activer un environnement virtuel

python -m venv myenv
source myenv/bin/activate   # Linux/Mac
myenv\Scripts\activate      # Windows

### 3. Installer les dépendances

pip install -r requirements.txt

## ⚙️ 🚀 Lancement

### Application Streamlit
streamlit run streamlitApp/app.py

➡️ Ouvrir le navigateur à l’adresse indiquée (par défaut http://localhost:8501).


### API (FastAPI)

uvicorn api.main:app --reload

➡️ Documentation interactive disponible via Swagger/OpenAPI :
http://localhost:8000/docs

###📂 Structure du projet
consommationEnergie/
│── streamlitApp/            # Interface utilisateur (visualisations)
│── api/                     # API (FastAPI)
│── pre_analyse_consomation/ # Pré-analyse des données
│── dashboard/               # Tableau de bord
│── hypotheses/              # Tests statistiques (régressions, χ²)
│── data/                    # Données CSV (EPCI, départements, régions)
│── README.md                # Documentation technique
│── guide_utilisateurs.md    # Guide d’utilisation (non technique)

###📈 Analyses intégrées

Régressions linéaires et multiples (influence du climat, chauffage, âge du logement).

Tests du χ² (liens entre variables catégorielles).

Indicateurs principaux :

consommation par habitant,

DJU (degrés-jours unifiés, indicateur climatique),

indice d’âge du logement,

taux de chauffage électrique.