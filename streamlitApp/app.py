# app.py
import streamlit as st

st.set_page_config(page_title="Énergie France – Tableau de bord", layout="wide")

st.title("🇫🇷 Énergie France – Tableau de bord")
st.markdown("""
Bienvenue ! Sélectionnez une page dans le menu **Pages** (à gauche/en haut) :

- **⚡ Consommation (Enedis)** — consommation par régions / départements / communes / EPCI / IRIS.
- **⚙️ Production (RTE)** — production et mix énergétique (éco2mix).
- **📊 Analyse nationale (eco2mix)** — analyses exploratoires, corrélations et prévisions.

Si le menu des pages n’apparaît pas, lancez le projet avec :
```bash
streamlit run streamlitApp/app.py       
""")

st.subheader("Liens rapides")
col1, col2, col3 = st.columns(3)

with col1:
    st.page_link("pages/01_production.py", label="Ouvrir ⚙️ Production (RTE)", icon="⚙️")
with col2:
    st.page_link("pages/02_consommation.py", label="Ouvrir ⚡ Consommation (Enedis)", icon="⚡")
with col3:
    st.page_link("pages/03_energie_analyse.py", label="Ouvrir 📊 Analyse nationale (eco2mix)", icon="📊")            