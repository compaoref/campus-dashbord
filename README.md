# ✂️ PrintCut Pro — Gestion Machine de Découpe

Système de gestion des activités quotidiennes pour machine de découpe d'imprimerie.

## Installation

### Prérequis
- Python 3.9 ou supérieur installé sur votre machine

### Étapes

```bash
# 1. Décompresser le dossier, puis entrer dedans
cd imprimerie_decoupe

# 2. (Optionnel mais recommandé) Créer un environnement virtuel
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'application
streamlit run app.py
```

L'application s'ouvre automatiquement dans votre navigateur à l'adresse :
**http://localhost:8501**

---

## Fonctionnalités

### 🏠 Tableau de bord
- KPIs instantanés : activités du jour, semaine, mois
- Graphique des activités sur 14 jours
- Donut de répartition par type de travail
- Activités du jour en temps réel
- Performance des opérateurs

### ➕ Saisir une activité
- Formulaire complet avec validation
- Champs : date, heures, opérateur, client, type de travail,
  matière, quantité, unité, nombre de poses, statut, priorité, notes
- Notification visuelle à la sauvegarde

### 📋 Historique
- Filtres combinables : date, opérateur, statut, type, client, priorité
- Tableau paginé et triable
- Export CSV pour tout ou partie
- Suppression d'enregistrement

### 📈 Statistiques
- Sélection de période (7j, 30j, mois en cours, tout)
- Répartition des statuts
- Top clients par volume
- Matières les plus utilisées
- Courbe d'évolution quotidienne
- Tableau de performance opérateur

---

## Structure des données

| Champ         | Description                               |
|---------------|-------------------------------------------|
| date          | Date du travail                           |
| heure_debut   | Heure de début (HH:MM)                    |
| heure_fin     | Heure de fin (HH:MM)                      |
| operateur     | Nom de l'opérateur                        |
| client        | Nom du client                             |
| type_travail  | Type de découpe                           |
| description   | Description détaillée du travail          |
| matiere       | Matière utilisée                          |
| quantite      | Quantité traitée                          |
| unite         | Unité (unités, feuilles, m², etc.)        |
| nb_poses      | Nombre de poses                           |
| statut        | Terminé / En cours / En attente / Annulé  |
| priorite      | Normale / Haute / Urgente                 |
| notes         | Notes libres                              |

Les données sont stockées localement dans `decoupe_activites.db` (SQLite).

---

## Personnalisation

Pour ajouter des opérateurs, types de travaux ou matières, modifiez les listes
en haut du fichier `app.py` :

```python
OPERATEURS   = ["Moussa K.", "Fatou S.", "Ibrahim T.", "Autre"]
TYPES_TRAVAIL = ["Découpe étiquettes", ...]
MATIERES      = ["Papier couché", ...]
```
