# ✂️ PrintCut Pro v2 — Avec Authentification & Factures

## Installation rapide

```bash
cd imprimerie_decoupe
pip install -r requirements.txt
streamlit run app.py
```
Ouvre → **http://localhost:8501**

---

## Comptes par défaut

| Identifiant | Mot de passe    | Rôle            | Accès |
|-------------|-----------------|-----------------|-------|
| `admin`     | `Admin@2024!`   | Administrateur  | Tout  |
| `manager`   | `Manager@2024!` | Manager         | Sauf gestion users |
| `operateur` | `Operateur@2024!` | Opérateur     | Saisie + ses activités uniquement |

> ⚠️ Changez les mots de passe dès la première connexion !

---

## Fonctionnalités

### 🔐 Authentification sécurisée
- Hachage PBKDF2-HMAC-SHA256 (310 000 itérations — standard NIST 2023)
- Sessions isolées par utilisateur
- Verrouillage des comptes inactifs
- Journal des connexions

### 👥 Gestion des utilisateurs (Admin uniquement)
- Créer / modifier / désactiver des comptes
- 3 rôles : Administrateur, Manager, Opérateur
- Changement de mot de passe sécurisé
- Validation : 8 car. min, 1 majuscule, 1 chiffre

### 🏠 Tableau de bord
- KPIs jour/semaine/mois
- Graphique 14 jours + donut types
- Activités du jour en temps réel

### ➕ Saisie activités
- Formulaire validé
- Date, heures, opérateur, client, type, matière, quantité, poses, statut, priorité

### 📋 Historique
- Filtres multi-critères
- Export CSV
- Suppression

### 📈 Statistiques
- Statuts, top clients, matières, évolution, performance opérateurs

### 🧾 Factures / Reçus
- Création de factures avec lignes multiples
- Calcul automatique HT/TVA/TTC (taux configurables)
- PDF professionnel téléchargeable (format A4)
- Numérotation automatique F-AAAA-NNNN
- Suivi statut paiement (Payé / En attente / Partiel)
- Historique et re-téléchargement

---

## Fichiers
```
app.py          — Application principale Streamlit
auth.py         — Module authentification + gestion users
facture.py      — Générateur PDF ReportLab
requirements.txt
README.md
decoupe_activites.db  — Base SQLite (créée au 1er lancement)
```
