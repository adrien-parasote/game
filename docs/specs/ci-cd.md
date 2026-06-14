# Spécifications : Pipeline CI/CD GitHub Actions

Ce document décrit les spécifications exactes des fichiers YAML qui seront générés dans le dossier `.github/` lors de la phase BUILD.

---

## 1. Intégration Continue (CI) - `ci.yml`

**Objectif :** La "Quality Gate". Vérifie que le code respecte les standards avant toute fusion sur `main`.

**Déclencheurs (Triggers) :**
- `push` sur la branche `main`
- `pull_request` ciblant `main`

**Environnement :**
- **OS :** `ubuntu-latest` (Linux uniquement pour économiser le budget gratuit).
- **Python :** `3.12` (tel que défini dans `pyproject.toml`).

**Étapes (Steps) :**
1. Cloner le code (`actions/checkout@v4`).
2. Configurer Python 3.12 (`actions/setup-python@v5`).
3. Installer les dépendances :
   - `pip install --upgrade pip`
   - `pip install -r requirements.txt pyright`
4. Vérifier le formatage : `ruff format --check .`
5. Vérifier la qualité du code (Lint) : `ruff check .`
6. Vérifier le typage statique : `pyright`
7. Lancer les tests unitaires : `pytest`

---

## 2. Gestionnaire de Release - `release.yml`

**Objectif :** Créer automatiquement une version publique (Release) avec les notes de mise à jour quand un Tag est poussé.

**Déclencheurs :**
- `push` sur les tags correspondant à `v*` (ex: `v1.0.0`).

**Action :**
- Utilise l'action officielle `softprops/action-gh-release@v2`.
- Active l'option `generate_release_notes: true` pour générer le Changelog automatiquement à partir des Pull Requests mergées.

---

## 3. Auto-Labeler des Pull Requests

**Objectif :** Assigner automatiquement les labels GitHub en fonction du nom de la branche, pour que les Release Notes se catégorisent toutes seules.

**Structure :**
- Un workflow : `.github/workflows/labeler.yml` (se déclenche à l'ouverture d'une PR).
- Un fichier de règles : `.github/labeler.yml`.

**Règles de mapping :**
- Branche `feat/*` ➔ Label `enhancement`
- Branche `bug/*` ➔ Label `bug`
- Branche `refactor/*` ➔ Label `refactor`

---

## 4. Maintenance Automatique (Dependabot)

**Objectif :** Mettre à jour `pygame-ce`, `pytest` et les Actions GitHub de manière hebdomadaire.

**Fichier :** `.github/dependabot.yml`

**Configuration :**
- Écosystème `pip` (scanne le `requirements.txt`).
- Écosystème `github-actions` (scanne les fichiers `.github/workflows/`).
- Fréquence : `weekly` (hebdomadaire).
