[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

> Document Type: Implementation
# Save System & Save Menu UI

Ce document spécifie le système de sauvegarde, l'interface utilisateur des emplacements de sauvegarde (Save Slots), et la gestion des miniatures (screenshots) du jeu.

## 1. Architecture Core

Le système repose sur 3 composants majeurs :
1. **`SaveManager`** : Étendu pour supporter la sérialisation des miniatures, du niveau du joueur et du temps en jeu.
2. **`SaveSlotUI`** : Un composant graphique réutilisable pour rendre un emplacement (Save Slot) à l'écran.
3. **`SaveMenuOverlay`** : Un gestionnaire de menu (utilisé par `PauseScreen` et `TitleScreen`) affichant 3 `SaveSlotUI`.

### 1.1 SaveManager & SlotInfo

Le `SaveManager` doit être capable de lire les méta-données très rapidement pour le menu (sans parser les objets lourds comme `world_state` ou `inventory`).

`SlotInfo` étendu :
- `slot_id: int`
- `saved_at: str` (format ISO)
- `playtime_seconds: float`
- `map_name: str`
- `player_name: str` (fallback: "Hero")
- `level: int`

**Gestion de la Miniature** :
- Lors d'une sauvegarde, une capture d'écran carrée centrée sur le joueur (ex: 120x120 pixels) doit être sauvegardée sous `saves/slot_{id}_thumb.png`.
- `SaveManager` expose `save_thumbnail(slot_id, surface)` et `load_thumbnail(slot_id) -> pygame.Surface | None`.

### 1.2 Rendering du Save Slot

Le slot utilise le background `assets/images/menu/03-save_slot.png` (427x200).
- **Miniature** : Dessinée à gauche. La zone disponible est approximativement entre X=40 et X=160.
- **Hover State** : Si le slot est survolé, un halo orange additif (cercle flou ou sprite) est rendu sur les 4 gemmes du cadre :
  - Haut-Gauche : `(26, 27)`
  - Haut-Droite : `(413, 27)`
  - Bas-Gauche : `(26, 170)`
  - Bas-Droite : `(414, 171)`

### 1.3 Bouton Retour (Back Button)

Le `SaveMenuOverlay` inclut un bouton "Retour" positionné en bas à gauche du panneau.
- **Icone** : `assets/images/menu/01-menu_back_cursor.png` (28x25).
- **Label** : Texte "Retour" (I18n: `menu.back`) rendu avec la police `Cormorant Garamond`.
- **Rendu** :
  - **Repos** : Effet gravé ("engraved").
  - **Survol** : Halo cyan intense (`(150, 255, 220)` / glow `(0, 180, 150)`).
- **Interaction** : Cliquer sur ce bouton permet de fermer l'overlay et de retourner à l'état précédent.

## Assumptions

| Assumption | Risk Level | Implication | Validation |
|------------|------------|-------------|------------|
| Screenshot cropping | Low | Player is always centered on screen | If camera shifts, crop might be slightly off. Validate manually. |
| Hover performance | Low | Additive blending (RGBA_ADD) of 4 small halos per slot | 12 small blits per frame is negligible. |
| Fallback fonts | Medium | Cormorant Garamond is available for menu UI | Ensure the font exists in `assets/fonts/` |

## 2. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Charger tout le fichier JSON pour afficher le menu | Lire uniquement les méta-données racine dans `_read_slot_info` | Optimisation des temps de chargement du menu |
| Écraser l'ancien fichier sans vérification | Créer un fichier `.tmp` puis le renommer | Prévenir la corruption si le jeu crash pendant la sauvegarde |
| Gérer les clics de slot directement dans `SaveSlotUI` | Gérer la détection de collision et de clic dans le composant parent (`PauseScreen` / `TitleScreen`) | Le parent doit émettre les `GameEvent` appropriés |
| Prendre le screenshot avec l'interface de pause visible | Prendre le screenshot juste avant l'ouverture du menu de pause ou rendre offscreen la scène | Le screenshot doit refléter le jeu, pas le menu |
| Appliquer le halo de survol avec une simple couleur opaque | Utiliser le flag `pygame.BLEND_RGBA_ADD` | Garantir un effet lumineux/glowing cohérent avec le style |

## 3. Test Case Specifications

### Unit Tests Required

| Test ID | Component | Input | Expected Output | Edge Cases |
|---------|-----------|-------|-----------------|------------|
| SAVE-U-001 | SaveManager | `save_thumbnail(1, valid_surf)` | Crée `saves/slot_1_thumb.png` | Le dossier `saves` n'existe pas |
| SAVE-U-002 | SaveManager | `load_thumbnail(1)` (existe) | Retourne la `pygame.Surface` | Fichier corrompu ou illisible |
| SAVE-U-003 | SaveManager | `_read_slot_info` | Retourne `SlotInfo` complet avec `level` | `level` ou `player_name` manquant dans les vieux JSON |
| SAVE-U-004 | SaveMenuOverlay | `update(dt)` avec souris sur Slot 2 | `_hovered_slot == 1` | Souris en dehors du menu |
| SAVE-U-005 | SaveSlotUI | Rendu avec `info=None` | Affiche le texte "Emplacement X — Vide" | Slot sans thumbnail (fallback icon) |
| SAVE-U-006 | SaveSlotUI | `draw(surface, rect, 1, None, None, False)` | Rendu sans crash | — |
| SAVE-U-007 | SaveSlotUI | `draw(surface, rect, 1, info, thumb, True)` | Rendu avec thumbnail et halo | Thumbnail non carré |
| SAVE-U-008 | SaveMenuOverlay | `__init__` + `refresh()` | `_slots_info[0].map_name` correct | SlotInfo None pour slots vides |
| SAVE-U-009 | SaveMenuOverlay | `get_clicked_slot(event)` | Retourne l'index du slot cliqué | Clic hors des rects → None |
| SAVE-U-010 | SaveMenuOverlay | `update(dt)` + `draw()` | `_hovered_slot` mis à jour, `screen.blit` appelé | — |
| SAVE-U-011 | SaveMenuOverlay | `is_back_clicked(event)` | Retourne True si clic sur bouton retour | Clic hors bouton retour → False |

### Integration Tests Required

| Test ID | Flow | Setup | Verification | Teardown |
|---------|------|-------|--------------|----------|
| SAVE-I-001 | Cycle de Sauvegarde | Joueur dans la map `spawn` niveau 2 | Fichier JSON contient le `level=2` et `thumbnail` existe | Delete `saves/slot_X` |
| SAVE-I-002 | Click sur Sauvegarder dans Pause | Ouvrir Pause, cliquer sur "Sauvegarder" | Le menu `SAVE_MENU` overlay s'affiche, les 3 slots sont visibles | Fermer Pause |
| SAVE-I-003 | Hover sur Slot | `SaveMenuOverlay` ouvert | La méthode de rendu des halos additifs est appelée sur `TitleScreen` | Fermer |

## 4. Error Handling Matrix

| Error Type | Detection | Response | Fallback | Logging | Alert |
|------------|-----------|----------|----------|---------|-------|
| Fichier JSON corrompu | `json.JSONDecodeError` dans `_read_slot_info` | Retourner `None` (considéré vide) | Ne pas crasher le menu | ERROR | Aucun |
| Sauvegarde image échoue | `pygame.error` dans `save_thumbnail` | Ignorer la miniature | Le slot apparaîtra sans image | WARN | Aucun |
| Image introuvable | `load_thumbnail` renvoie une erreur | Retourner `None` | Affiche un carré gris/vide | WARN | Aucun |

## 5. Deep Links
- **`SaveManager` class**: [save_manager.py L36](../../src/engine/save_manager.py#L36)
- **`PauseScreen` overlay**: [pause_screen.py L14](../../src/ui/pause_screen.py#L14)
- **`TitleScreen` load overlay**: [title_screen.py L287](../../src/ui/title_screen.py#L287)
- **`GameStateManager` Events**: [game_state_manager.py L108](../../src/engine/game_state_manager.py#L108)

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| SAVE-U-001 | `test_save_thumbnail_creates_file` | `../../tests/engine/test_save_manager.py` |
| SAVE-U-002 | `test_load_thumbnail_returns_surface` | `../../tests/engine/test_save_manager.py` |
| SAVE-U-003 | `test_list_slots_reflects_saved` | `../../tests/engine/test_save_manager.py` |
| SAVE-U-004 | `test_title_screen_update` | `../../tests/ui/test_title_screen.py` |
| SAVE-U-005 | `test_title_screen_draw_load_menu` | `../../tests/ui/test_title_screen.py` |
| SAVE-U-006 | `test_save_slot_ui_draw_empty` | `../../tests/ui/test_save_menu.py:L24` |
| SAVE-U-007 | `test_save_slot_ui_draw_filled` | `../../tests/ui/test_save_menu.py:L35` |
| SAVE-U-008 | `test_save_menu_overlay_init` | `../../tests/ui/test_save_menu.py:L48` |
| SAVE-U-009 | `test_save_menu_overlay_get_clicked_slot` | `../../tests/ui/test_save_menu.py:L57` |
| SAVE-U-010 | `test_save_menu_overlay_update_and_draw` | `../../tests/ui/test_save_menu.py:L73` |
| SAVE-U-011 | `test_save_menu_overlay_back_clicked` | `../../tests/ui/test_save_menu.py` |
| SAVE-I-001 | `test_save_creates_file` | `../../tests/engine/test_save_manager.py` |
| SAVE-I-002 | `test_pause_screen_handle_event_click_sauvegarder` | `../../tests/ui/test_pause_screen.py` |
| SAVE-I-003 | `test_title_screen_update` | `../../tests/ui/test_title_screen.py` |
