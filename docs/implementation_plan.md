# Plan d'implémentation — Fusion et Urbanisation des Noms (Tooling Docs)

Suite à ta remarque, nous allons fusionner et renommer les fichiers pour faire disparaître les notions de "V1", "V2" ou "V3". Puisque les outils sont implémentés et fonctionnels, seule la version "actuelle" a de l'importance. L'historique n'a plus lieu d'encombrer l'arborescence.

---

## User Review Required

> [!IMPORTANT]
> Cette action va **supprimer** les fichiers obsolètes (V1/V2, Edge) et **renommer** les fichiers V3 en noms définitifs, clairs et sans version.
> Les liens internes (Deep Links) et le Master Index (`README.md`) seront tous mis à jour.
> 
> Merci de valider ce plan de renommage/suppression.

---

## Proposed Changes

### 1. Asset Creator (Fusion V3 / V2 / V1)
* **[DELETE]** `docs/tooling/specs/asset_creator_spec.md` (Obsolète)
* **[DELETE]** `docs/tooling/strategic/asset_creator_blueprint.md` (V1, obsolète)
* **[RENAME]** `asset_creator_spec.md` ➔ `asset_creator_spec.md` (Spec officielle unique)
* **[RENAME]** `asset_creator_blueprint.md` ➔ `asset_creator_blueprint.md` (Blueprint officiel unique)

### 2. Autotile Pipeline (Fusion Blob / Edge)
* **[DELETE]** `docs/tooling/specs/autotile_pipeline_spec.md` (Ancienne approche "Edge", obsolète)
* **[RENAME]** `autotile_pipeline_spec.md` ➔ `autotile_pipeline_spec.md` (Spec officielle unique)

### 3. Mise à jour des Liens Croisés (Cross-Spec & README)
* **[MODIFY]** `docs/tooling/README.md` : Mise à jour pour pointer vers les nouveaux fichiers sans version (et retrait de la section "Historique Legacy" qui n'a plus lieu d'être).
* **[MODIFY]** Tous les fichiers dans `docs/tooling/` et `.agents/learnings/tooling.md` : Recherche et remplacement global des anciens noms (`asset_creator_spec.md`, `autotile_pipeline_spec.md`, etc.) par leurs nouveaux noms "urbanisés".

---

## Verification Plan

### Automated Tests
* Lancement du validateur de Spec pour s'assurer qu'aucun `Deep Link` n'a été brisé (le validateur vérifie l'existence des fichiers liés) :
```bash
python3 .agents/skills/spec-gate/scripts/spec_precheck.py --dir docs/tooling/specs
```
