
---

## 📘 **guide_utilisateurs.md** (version pédagogique)

```markdown
# 📘 Guide d’utilisation : Analyse de la consommation d’énergie

## 🎯 Objectif
Cet outil aide les décideurs (collectivités locales, services techniques, etc.) à comprendre les données de consommation énergétique et à les utiliser pour orienter leurs stratégies.

---

## 🗺️ Utilisation de l’interface (Streamlit)

1. Sélectionnez le niveau d’analyse (**EPCI**, **département**, **région**).  
2. Utilisez les **filtres** pour choisir un territoire spécifique.  
3. La **carte interactive** montre la consommation par couleur :  
   - couleurs foncées → forte consommation,  
   - couleurs claires → faible consommation.  
4. Survolez un territoire pour voir ses indicateurs clés.

---

## 📊 Indicateurs principaux

- **Consommation par habitant** (MWh/hab) → permet de comparer les territoires.  
- **DJU (Degrés-jours unifiés)** → mesure de la rigueur climatique.  
- **Indice d’âge du logement** → reflète l’ancienneté moyenne du parc immobilier.  
- **Taux de chauffage électrique** → % de logements chauffés à l’électricité.  

---

## 📈 Interprétation des résultats

- Forte consommation ↔ climat froid, forte proportion de chauffage électrique, logements anciens.  
- Comparer deux territoires similaires pour isoler l’effet d’un facteur.  
- Les tests statistiques intégrés valident ou infirment certaines hypothèses (ex. lien climat ↔ chauffage électrique).

---

## 📚 Scénarios pratiques

- Identifier les zones prioritaires pour la rénovation énergétique (logements anciens + climat froid).  
- Comparer deux départements voisins pour estimer l’impact du type de chauffage.  
- Préparer un dossier pour demander des subventions (argument basé sur données).  
- Suivre l’évolution de la consommation dans le temps grâce aux mises à jour automatiques (API).  

---

## 🔄 API (FastAPI)

Une API est disponible pour automatiser l’accès aux données.  
➡️ Documentation interactive via **Swagger/OpenAPI** :  
`http://localhost:8000/docs`

Exemple d’usage :
- Intégration des données dans un tableau de bord externe.  
- Automatisation de rapports périodiques.  

---

## ✅ Conclusion

Ce guide permet de :  
- comprendre la logique de l’outil,  
- interpréter les résultats sans connaissances techniques poussées,  
- utiliser les données pour appuyer les décisions stratégiques en matière d’énergie.
