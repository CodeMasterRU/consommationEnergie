import streamlit as st

st.set_page_config(page_title="Énergie France – Tableau de bord", layout="wide")

st.title("🇫🇷 Énergie France – Tableau de bord")
st.markdown("""
Bienvenue ! Sélectionnez une page dans le menu **Pages** (à gauche/en haut) :

- **⚡ Consommation (Enedis)** — consommation par régions / départements / communes / EPCI / IRIS.
- **⚙️ Production (RTE)** — (en développement) production et mix énergétique (éco2mix).

Si le menu des pages n’apparaît pas, lancez le projet avec :
```bash
streamlit run streamlitApp/app.py
""")

st.subheader("Liens rapides")
col1, col2 = st.columns(2)
with col1:
    st.page_link("pages/consommation.py", label="Ouvrir ⚡ Consommation (Enedis)", icon="⚡")
with col2:
    st.page_link("pages/production.py", label="Ouvrir ⚙️ Production (RTE)", icon="⚙️")