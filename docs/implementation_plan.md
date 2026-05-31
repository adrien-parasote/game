# Plan d'implémentation — Nettoyage de la V1 (Tooling)

Ce plan décrit la suppression complète de la logique V1 (basée sur un découpage de bruit à 4 couleurs) dans le code, la documentation et les tests de l'outil de création d'assets, afin de simplifier la base de code et ne conserver que le pipeline V2 haute qualité (rampes OKLCh et dithering).

---

## User Review Required

> [!WARNING]
> La suppression de la V1 supprime la compatibilité descendante pour toute palette YAML externe ou personnalisée qui n'inclurait pas la section `ramp`. Les palettes devront obligatoirement spécifier une configuration de rampe de couleurs (`ramp`). Les 6 palettes par défaut du projet possèdent déjà cette configuration.

> [!NOTE]
> Plusieurs tests unitaires historiques axés sur le comportement V1 seront complètement supprimés.

---

## Proposed Changes

### Documentation de l'outil

#### [DELETE] [asset_creator_spec.md](file:///Users/adrien.parasote/Documents/perso/game/docs/tooling/specs/asset_creator_spec.md)
* Suppression complète de la spécification originale V1.

#### [MODIFY] [README.md](file:///Users/adrien.parasote/Documents/perso/game/docs/README.md)
* Retirer les références et liens vers `asset_creator_spec.md`.

#### [MODIFY] [asset_creator_v2_texture_quality.md](file:///Users/adrien.parasote/Documents/perso/game/docs/tooling/specs/asset_creator_v2_texture_quality.md)
* Nettoyer les références à la V1 et supprimer les notes de rétrocompatibilité.

#### [MODIFY] [asset_creator_v3_gui.md](file:///Users/adrien.parasote/Documents/perso/game/docs/tooling/specs/asset_creator_v3_gui.md)
* Nettoyer les mentions et cas de tests liés à la V1.

---

### Moteur de création d'assets (`tools/asset_creator`)

#### [MODIFY] [palette.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/core/palette.py)
* Rendre le champ `ramp` du fichier YAML obligatoire. Lever une `ValueError` explicite si le bloc `ramp` est absent.
* Nettoyer la propriété `extended_colors` pour ne plus avoir de fallback sur `self.colors`.

#### [MODIFY] [texture.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/core/texture.py)
* Supprimer la fonction `generate_noise_texture` (moteur V1).
* Renommer ou simplifier `generate_pattern_texture` pour qu'elle délègue directement à `generate_noise_texture_v2`.
* Simplifier `TextureParams` en retirant les paramètres V1 obsolètes (`thresholds` et `use_smooth_ramp`, ce dernier devenant implicitement toujours vrai).

#### [MODIFY] [cli.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/cli.py)
* Retirer l'option de ligne de commande `--quality`.
* Nettoyer la fonction `_generate_terrain` pour appeler directement le pipeline V2 (textures et détails).

#### [MODIFY] [state.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/gui/state.py)
* Supprimer l'attribut `quality` de l'état de l'application et de la fonction `state_from_preset`.

#### [MODIFY] [app.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/gui/app.py) & [pipeline.py](file:///Users/adrien.parasote/Documents/perso/game/tools/asset_creator/gui/pipeline.py)
* Supprimer les vérifications de `state.quality == "v2"` (puisque tout passe désormais en V2).

---

### Tests unitaires et d'intégration (`tests/tools`)

#### [MODIFY] [test_texture.py](file:///Users/adrien.parasote/Documents/perso/game/tests/tools/asset_creator/test_texture.py)
* Supprimer les tests `test_v1_texture_still_works` et `test_v1_pattern_noise_still_delegates_correctly`.
* Adapter les autres tests aux modifications de signatures de `TextureParams`.

#### [MODIFY] [test_palette.py](file:///Users/adrien.parasote/Documents/perso/game/tests/tools/asset_creator/test_palette.py)
* Supprimer les tests de compatibilité V1 (`test_v1_palette_no_ramp_section`, `test_v1_extended_colors_returns_original`, `test_v1_interpolate_works`).

#### [MODIFY] [test_cli.py](file:///Users/adrien.parasote/Documents/perso/game/tests/tools/asset_creator/test_cli.py)
* Supprimer les cas de test de génération basés sur `--quality v1`.

#### [MODIFY] [test_gui_state.py](file:///Users/adrien.parasote/Documents/perso/game/tests/tools/asset_creator/test_gui_state.py) & [test_gui_integration.py](file:///Users/adrien.parasote/Documents/perso/game/tests/tools/asset_creator/test_gui_integration.py)
* Supprimer la classe `TestIT005V1Quality` et les tests de validation de la qualité V1.

---

## Verification Plan

### Automated Tests
```bash
# Lancer toute la suite de tests pour valider le refactoring et s'assurer que tout reste au vert en V2
venv/bin/pytest tests/tools/asset_creator/
```
