[assumption: "All implicit constants and defaults are documented here – pending detailed entries"] – risk: Low

# Technical Specification — Game Flow & Save System [Implementation]

> Document Type: Implementation

**Document type :** Implementation  
**Date :** 2026-05-02  
**Status :** ✅ Prêt pour BUILD  
**ADRs :** ADR-001, ADR-002, ADR-003  
**Blueprint :** `docs/strategic/game_vision.md`

---

## Assumptions

| # | Assumption | Risk |
|---|---|---|
| A1 | `Item` est une structure de données Python pure — sérialisable via `.__dict__` | LOW — confirmé par `inventory_system.py` |
| A2 | `TimeSystem._total_minutes` est le seul état interne à sauvegarder | LOW — toutes les propriétés sont dérivées |
| A3 | `WorldState._state` est un `dict[str, dict]` de types JSON-natifs | LOW — confirmé par `world_state.py` |
| A4 | `Game.__init__` charge toujours une map au démarrage — ce comportement est modifié : `Game.__init__` ne charge plus de map si appelé en mode "shell" | MEDIUM — nécessite un flag `skip_map_load` |
| A5 | Les assets menu ont un fond noir → `colorkey=(0,0,0)` pour le logo uniquement | LOW — confirmé lors de la session assets |

---

## 1. Asset Dimensions (mesurées)

| Asset | Fichier | Dimensions totales | Par état |
|---|---|---|---|
| Logo | `00-title_logo.png` | 903×241 | — (fond noir, colorkey) |
| Background | `01-menu_background.png` | 1024×1024 | — (scaled to 1280×720) |
| Boutons | `02-menu_buttons.png` | 1024×182 | **341×182** (3 états : idle/hover/pressed) |
| Panel | `03-panel_background.png` | 1024×1024 | — (scaled to target size) |
| Save Slot | `04-save_slot.png` | 1024×1024 | **1024×512** (2 états : idle=top, hover=bottom) |

---

## 2. Modules à créer

### 2.1 `src/engine/save_manager.py` [NEW]

**Responsabilité :** Sérialisation/désérialisation des slots de sauvegarde.

```
SAVES_DIR = "saves/"
MAX_SLOTS = 3
SCHEMA_VERSION = "0.4.0"
SLOT_FILENAME = "slot_{n}.json"   # n = 1, 2, 3
```

**Interface publique :**

```python
class SaveManager:
    def list_slots(self) -> list[SlotInfo | None]
        # Retourne liste de 3 éléments. None = slot vide.
        # SlotInfo = dataclass { slot_id, saved_at, playtime_seconds, location, map_name, map_display_name }

    def save(self, slot_id: int, game: Game) -> None
        # slot_id: 1..3. Sérialise game state → saves/slot_{id}.json

    def load(self, slot_id: int) -> SaveData | None
        # Retourne SaveData ou None si slot vide/corrompu

    def delete(self, slot_id: int) -> None
        # Supprime saves/slot_{id}.json

    def slot_exists(self, slot_id: int) -> bool
```

**Structure JSON (ADR-002) :**

```json
{
  "version": "0.4.0",
  "saved_at": "2026-05-02T14:30:00",
  "playtime_seconds": 3600,
  "player": {
    "map_name": "01-castle_hall.tmj",
    "x": 320.0,
    "y": 480.0,
    "facing": "down",
    "level": 1,
    "hp": 100,
    "max_hp": 100,
    "gold": 0
  },
  "time_system": {
    "total_minutes": 7200.0
  },
  "inventory": {
    "slots": [
      {"id": "sword_iron", "quantity": 1},
      null
    ],
    "equipment": {
      "HEAD": null,
      "LEFT_HAND": {"id": "sword_iron", "quantity": 1},
      "RIGHT_HAND": null,
      "UPPER_BODY": null,
      "LOWER_BODY": null,
      "SHOES": null,
      "BAG": null,
      "BELT": null
    }
  },
  "world_state": {
    "castle_hall_chest_01": {"is_on": true}
  }
}
```

**Sérialisation de `Inventory` :**
- `slots` : liste de 28 éléments. Chaque slot = `{"id": str, "quantity": int}` ou `null`
- `equipment` : dict slot_name → `{"id": str, "quantity": int}` ou `null`
- Champs `name`, `description`, `icon`, `stack_max` sont **omis** → reconstruits depuis `propertytypes.json` au chargement via `Inventory.create_item(id, quantity)`

**Désérialisation :**
- Valider `version` — si mismatch majeur, logger WARNING et retourner None
- `Inventory.slots[i] = inventory.create_item(d["id"], d["quantity"])` si not null
- `TimeSystem._total_minutes = data["time_system"]["total_minutes"]`
- `WorldState._state = data["world_state"]`

---

### 2.2 `src/ui/title_screen.py` [MODIFIED]

**Responsabilité :** Affichage et navigation du menu principal.

**Layout sur écran 1280×720 :**

```
┌────────────────────────────────────────────────┐  720px
│  [01-menu_background.png — 1280×720, fullscreen]  │
│  [TITRE TEXT (Cormorant, 90pt, cyan) — y=80, centred]│
│                                                   │
│           [Menu items x=1055, y_start=360]        │
│           Nouvelle Partie, Charger, Options, Quitter│
└────────────────────────────────────────────────┘ 1280px
```

**Rendu du titre (texte dynamique) :**
- Police : `assets/fonts/cormorant-garamond-regular.ttf`, taille 90pt
- Couleur : `(150, 255, 220)` — cyan/turquoise clair
- Halo glow : `(0, 180, 150)` — cyan intense (rendu via `_blit_halo_text`)
- Position : centré x=640, y=80
- Aucun asset image pour le titre (supprimé : `00-title_logo_main_title.png`, `00-title_logo_separator.png`, `00-title_logo_subtitle.png`, `00-title_logo_moon.png`, `00-title_logo_gear.png`)

**Halos animés sur l'arrière-plan (`BACKGROUND_LIGHTS`) :**
- **33 positions** calibrées via `scripts/calibration/calibrate_halos.py` (mode FIRE)
- 3 tiers de rayon : `45` (lanternes), `28` (fenêtres), `18` (petites fenêtres)
- Halos pré-générés à l'init : surface noire par rayon distinct, dégradé quadratique `(255, 120, 20)`, `BLEND_RGB_ADD`
- **Indépendance résolution** : coordonnées en espace logique 1280×720 ; `_light_scale_x / _light_scale_y` depuis `screen.get_size()`
- Scintillement : `sin(t*0.4 + i*1.1) * 0.06 + sin(t*0.9 + i*2.3) * 0.04`, base 0.92 — bougie
- Flag `HALO_DEBUG = False` : activer pour croix de calibration (rouge=feu, cyan=champignon)

**Halos champignon bioluminescents (`MUSHROOM_LIGHTS`) :**
- **25 positions** calibrées via `scripts/calibration/calibrate_halos.py` (mode MUSHROOM, touche M)
- Format : `(x, y, radius, (R, G, B))` — couleur par champignon
- Couleur cyan : `(70, 220, 200)` pour les champignons turquoise ; rouge `(220, 80, 60)` disponible
- Tiers : r=22 (grands), r=16 (moyens), r=11 (petits)
- Halos pré-générés à l'init par couple `(color_key, radius)` unique — dict `_mushroom_halos`
- Respiration lente : `sin(t*0.15 + i*1.3) * 0.10 + sin(t*0.37 + i*2.1) * 0.06`, base 0.84 — bioluminescent

**Calibration workflow (dual-mode) :**
```bash
python3 scripts/calibration/calibrate_halos.py
# Mode FIRE (défaut) : cliquer sur lanternes/fenêtres
# Touche M : switcher vers mode MUSHROOM → cliquer sur champignons
# Shift+Click = moyen, Ctrl+Click = petit
# S = sauvegarder les deux listes
python3 scripts/calibration/apply_calibration.py  # injecter BACKGROUND_LIGHTS + MUSHROOM_LIGHTS
```

**Rendu des items du menu :**
- Au repos : effet "engraved in stone" (texte + ombre + reflet via `_blit_engraved`)
- Au survol : halo cyan `_blit_halo_text` couleur `(150, 255, 220)` / glow `(0, 180, 150)`

**État machine de la TitleScreen :**
```
MAIN_MENU → (clic Charger)       → LOAD_MENU  (overlay panel + slots)
MAIN_MENU → (clic Options)       → OPTIONS    (overlay panel + stub)
MAIN_MENU → (clic Quitter)       → QUIT       (pygame.quit + sys.exit)
LOAD_MENU → (clic slot)          → retourne GameEvent.LOAD_GAME(slot_id)
LOAD_MENU → (ESC ou bouton retour) → MAIN_MENU
```

**Interface publique :**
```python
class TitleScreen:
    def __init__(self, screen: pygame.Surface, save_manager: SaveManager)
    def handle_event(self, event: pygame.Event) -> GameEvent | None
    def update(self, dt: float) -> None  # incrèmente _light_time
    def draw(self) -> None
```

**Constantes (dans `title_screen_constants.py`) :**
- `BACKGROUND_LIGHTS` : 33 tuples `(x, y, radius)` en espace logique 1280×720
- `BG_LIGHT_COLOR = (255, 120, 20)` — couleur ambre/feu
- `MUSHROOM_LIGHTS` : 25 tuples `(x, y, radius, (R, G, B))` — couleur cyan `(70, 220, 200)` par défaut
- `HALO_DEBUG = False` — croix de calibration (rouge=feu, cyan=champignon)
- `LOGO_MAIN_COLOR = (150, 255, 220)`, `LOGO_MAIN_HALO = (0, 180, 150)`
- `MENU_HOVER_COLOR = (150, 255, 220)`, `MENU_HOVER_HALO = (0, 180, 150)`

---

### 2.3 `src/engine/game_state_manager.py` [NEW]

**Responsabilité :** Boucle principale, orchestration des états.

**États :**
```python
class GameState(Enum):
    TITLE = "title"
    PLAYING = "playing"
    PAUSED = "paused"
```

**Boucle principale :**
```python
class GameStateManager:
    def __init__(self)
    def run(self) -> None   # boucle principale, remplace Game.run()

    def _handle_title(self, events) -> None
    def _handle_playing(self, events, dt) -> None
    def _handle_paused(self, events) -> None

    def _transition_to_playing(self, slot_id: int | None) -> None
        # slot_id=None → nouvelle partie, slot_id=1..3 → chargement
    def _transition_to_title(self) -> None
        # MUST call: game.inventory_ui._init_state() + game.chest_ui.close()
        # Raison: les deux UI sont des objets persistants — si ouverts en jeu,
        # ils doivent être réinitialisés avant toute nouvelle partie ou chargement.
        # (BUG-GSM-001 : inventaire ouvert après retour au menu)
    def _transition_to_paused(self) -> None
```

**Interception de ESC (ADR-003) :**
- Si `state == PLAYING` et `K_ESCAPE` → `_transition_to_paused()`
- Si `state == PAUSED` et `K_ESCAPE` → `_transition_to_playing()` (resume)
- `pygame.QUIT` → `pygame.quit() + sys.exit()` depuis tous les états

**Initialisation de `Game` :**
- `Game.__init__(skip_map_load=False)` — nouveau paramètre
- Si `skip_map_load=True` : skip le bloc `self._load_map(default_map)`
- `GameStateManager` instancie `Game(skip_map_load=True)` au démarrage
- `_transition_to_playing(slot_id=None)` → appelle `game._load_map(default_map)`
- `_transition_to_playing(slot_id=N)` → applique `SaveData` puis `game._load_map(data.player.map_name)`

**`Game.run_frame(dt) -> GameEvent` :**
- Remplace `Game.run()` pour le mode tick-par-tick
- Appelle `_handle_events()`, `_update(dt)`, `_draw()`
- Retourne GameEvent.PAUSE_REQUESTED si ESC intercepté, sinon GameEvent.NONE
- **`Game.run()` est préservé intact** pour les tests existants

---

### 2.4 `src/ui/pause_screen.py` [NEW]

**Responsabilité :** Overlay Pause sur le jeu en cours.

**Layout (centré sur 1280×720, panel 600×400) :**
```
┌─── PANEL 600×400 — centré ───┐
│      [Titre "PAUSE"]         │
│   [BTN Reprendre  — y+0]     │
│   [BTN Sauvegarder — y+70]   │
│   [BTN Menu Principal — y+140]│
└──────────────────────────────┘
```

**Interface publique :**
```python
class PauseScreen:
    def __init__(self, screen: pygame.Surface, save_manager: SaveManager)
    def handle_event(self, event: pygame.Event) -> GameEvent | None
    def update(self, dt: float) -> None
    def draw(self) -> None
    # Overlay semi-transparent: surface noire alpha=160 plein écran avant panel
```

**Bouton Sauvegarder :**
- Si 3 slots occupés → affiche un overlay interne de sélection de slot (SaveSlotUI partagé) pour choisir lequel écraser
- Sinon → sauvegarde dans le premier slot vide, affiche confirmation 2s

---

### 2.5 Modifications `src/engine/game.py` [MODIFY]

**Seules modifications autorisées :**

1. **`__init__` — ajout du paramètre `skip_map_load`** :
```python
def __init__(self, skip_map_load: bool = False):
    ...
    # Fin de __init__, remplacer le bloc final par :
    if not skip_map_load:
        self._load_map(default_map)
```

2. **`run_frame(dt: float) -> GameEvent`** — nouvelle méthode :
```python
def run_frame(self, dt: float) -> GameEvent:
    self._handle_events()
    self._update(dt)
    self._draw()
    return GameEvent.NONE
```

3. **Suppression de Settings.QUIT_KEY** dans `_handle_events()` :
```python
# ❌ Supprimer ces lignes (géré par GameStateManager)
if event.key == Settings.QUIT_KEY:
    pygame.quit()
    sys.exit()
```

4. **`get_state() -> dict`** — nouvelle méthode pour serialisation :
```python
def get_state(self) -> dict:
    """Retourne l'état complet du jeu pour la sauvegarde."""
    return {
        "map_name": self._current_map_name,
        "player_pos": (self.player.pos.x, self.player.pos.y),
        "player_facing": self.player.current_state,
        "player_level": self.player.level,
        "player_hp": self.player.hp,
        "player_max_hp": self.player.max_hp,
        "player_gold": self.player.gold,
        "time_total_minutes": self.time_system._total_minutes,
        "inventory_slots": self.player.inventory.slots,
        "inventory_equipment": self.player.inventory.equipment,
        "world_state": self.world_state._state,
    }
```

**`run()` est préservé sans modification** (444 tests existants).

---

### 2.6 Modifications `src/main.py` [MODIFY]

```python
from src.engine.game_state_manager import GameStateManager

def main():
    try:
        manager = GameStateManager()
        manager.run()
    except Exception as e:
        logging.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
```

---

### 2.7 Modifications `gameplay.json` [MODIFY]

Supprimer la clé `quit_key` :
```json
"controls": {
    "move_up": "K_UP",
    "move_down": "K_DOWN",
    "move_left": "K_LEFT",
    "move_right": "K_RIGHT",
    "interact_key": "K_e",
    "inventory_key": "K_i",
    "toggle_fullscreen_key": "K_p"
}
```

Et dans `src/config.py` : supprimer `QUIT_KEY` de la classe `Settings`.

---

## 2.8 Global Controls & Constants [NEW]

| Constant | Value (Default) | Source |
|----------|-----------------|--------|
| `GameState.TITLE` | `"title"` | `src/engine/game_state_manager.py` |
| `GameState.PLAYING` | `"playing"` | `src/engine/game_state_manager.py` |
| `GameState.PAUSED` | `"paused"` | `src/engine/game_state_manager.py` |
| `Settings.MAP_SIZE` | `32` | `src/config.py` |
| `Settings.TOGGLE_FULLSCREEN_KEY` | `pygame.K_p` | `src/config.py` (via `gameplay.json`) |

---

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|---|---|---|
| Appeler `Game()` dans `GameStateManager.__init__()` sans `skip_map_load=True` | `Game(skip_map_load=True)` | Charge une map inutile avant même d'afficher le menu |
| Utiliser `pickle` pour les saves | JSON via `json.dump` | Non lisible, fragile aux refactors de classes |
| Stocker `name`/`description`/`icon` dans le JSON de save | Ne stocker que `id` + `quantity` | Ces champs sont reconstruits depuis `propertytypes.json` |
| `pygame.display.init()` dans `TitleScreen` | Le display est déjà init dans `Game.__init__` | Double init = crash |
| Modifier `Game.run()` | Ajouter `Game.run_frame()` à côté | Les 444 tests existants appellent `run()` |
| Hardcoder les positions de boutons | Calculer depuis `Settings.WINDOW_WIDTH/HEIGHT` | Ne supporte pas le changement de résolution |
| Appeler `sys.exit()` depuis `TitleScreen` | Retourner GameEvent.QUIT | Séparation des responsabilités |
| Écrire dans `saves/` sans `os.makedirs(exist_ok=True)` | Toujours créer le dossier d'abord | `saves/` peut ne pas exister au 1er lancement |
| `open(path, "w")` sans `try/except` sur les saves | Wrapper dans `try/except IOError` | Disque plein, permissions, etc. |
| Tester les coordonnées de boutons avec des valeurs hardcodées | Tester les `GameEvent` retournés | Les positions changent avec la résolution |
| Dans les tests: sauvegarder dans `tmp_saves_dir` mais laisser `GameStateManager` lire le dossier `saves/` réel | Patcher `gsm._save_manager.load` avec `side_effect=sm.load` | Le GSM crée son propre `SaveManager("saves/")` — sans patch, il lit des saves de production (BUG-GSM-002). |

---

## 4. Test Case Specifications

### Unit Tests — `SaveManager`

| ID | Composant | Input | Expected Output |
|---|---|---|---|
### Unit Tests — `SaveManager` & Core Systems

| ID | Composant | Input | Expected Output | Failure Mode |
|---|---|---|---|---|
| GF-001 | `SaveManager.save()` | Sauvegarde valide (Slot 1) | Création `slot_1.json` + Thumbnail | Espace disque plein |
| GF-002 | `SaveManager.load()` | Chargement Slot 1 existant | État du jeu restauré (Map, Pos, Inv) | Fichier corrompu |
| GF-003 | `Game.get_state()` | Appel pendant le jeu | Retourne dict complet (Map, Player, WS) | WS vide |
| GF-004 | `InteractionManager.update()` | Proximité objet (Chest) | `is_interactable` = True | Objet hors vue |
| GF-005 | `InteractionManager.handle_interactions()` | Appui sur E (Interaction) | Déclenche `target.interact()` | Plusieurs cibles (Proximité prioritaire) |
| GF-006 | `DialogueManager.start_dialogue()` | Texte brut ("Hello") | UI active + Début typewriter | Texte très long (> 5 pages) |
| GF-007 | `DialogueManager.advance()` | Appui sur E (Pendant typing) | Skip typewriter (Full page) | Page déjà complète |
| GF-008 | `DialogueManager.advance()` | Appui sur E (Page complète) | Passage page suivante | Dernière page (Fermeture) |
| GF-009 | `InputHandler.handle_event()` | Appui sur I (Inventory) | `inventory_ui.is_open` bascule | Dialogue actif (Bloqué) |
| GF-010 | `InputHandler.handle_event()` | Appui sur ESC (Pause) | `GameState` -> `PAUSED` | Depuis Dialogue (Permis) |
| GF-011 | `SaveMenuOverlay.handle_event()` | Clic bouton "Save" | Déclenche `save_requested` event | Slot déjà pris (Overwrite) |
| GF-012 | `InputHandler.handle_event()` | KEYDOWN K_ESCAPE depuis `LOAD_MENU` | Retour vers `MAIN_MENU` |
| GF-013 | `SaveMenuOverlay.handle_event()` | Clic Slot 2 (Libre) | Sauvegarde sur Slot 2 | Slot 2 plein |
| GF-014 | `GameStateManager.run()` | `pygame.QUIT` | Sortie propre du processus |
| GF-015 | `GameStateManager.run()` | `Settings.TOGGLE_FULLSCREEN_KEY` | Bascule `is_fullscreen` | Fallback si échec |
| GF-016 | `GameStateManager.run()` | `K_ESCAPE` (En jeu) | Bascule `GameState.PAUSED` |
| GF-017 | `GameStateManager.run()` | `K_ESCAPE` (En pause) | Bascule `GameState.PLAYING` |
| GF-018 | `Game.transition_map()` | Map A -> Map B (Fade) | Ecran noir progressif + Load Map B | Map B inexistante |

### Unit Tests — `GameStateManager`

| ID | Composant | Input | Expected Output | Failure Mode |
|---|---|---|---|---|
| GF-019 | Init | État par défaut | `state == TITLE` |
| GF-020 | Title | Event `NEW_GAME` | Transition vers `PLAYING` |
| GF-021 | Title | Event `LOAD_REQUESTED` | Chargement Slot + Transition `PLAYING` | Slot corrompu |
| GF-022 | Title | Event `QUIT` | `sys.exit()` |
| GF-023 | Playing | Event `PAUSE_REQUESTED` | Transition vers `PAUSED` |
| GF-024 | Paused | Event `RESUME` | Transition vers `PLAYING` |
| GF-025 | Paused | Event `SAVE_REQUESTED` | Appel `SaveManager.save()` + Notification | Echec I/O |
| GF-026 | Paused | Event `GOTO_TITLE` | Transition vers `TITLE` + Reset UIs | UI restée ouverte |
| GF-027 | Paused | Auto-save (First Free) | Sauvegarde sur premier slot vide | Tous les slots pleins (Overwrite Slot 1) |
| GF-028 | Paused | Auto-save (Fallback) | Overwrite Slot 1 si tous pleins |
| GF-029 | Playing | ESC Key | Transition vers `PAUSED` |
| GF-030 | Paused | ESC Key | Transition vers `PLAYING` |
| GF-031 | Loading | Load Time | World time restauré exactement | Drift temporel |
| GF-032 | Playing | Filter Events | Filtrage des inputs internes (ex: ESC) | Double processing |
| GF-033 | Transition | Title Screen Reset | Inventory/Chest UIs forcées à close | Persistent overlays |

### Integration Tests

| ID | Flow | Setup | Verification |
|---|---|---|---|
| IT-001 | Save → Load roundtrip | Game en jeu, save slot 1, reload slot 1 | `player.pos`, `time_system._total_minutes`, `world_state._state` identiques |
| IT-002 | Nouvelle partie depuis menu | `GameStateManager`, clic "Nouvelle Partie" | `game._current_map_name` = default_map, `state == PLAYING` |
| IT-003 | Pause → Save → Resume | En jeu, ESC, Sauvegarder, ESC | state = PLAYING, slot fichier créé |
| TC-IH-01 | Quit Event | sys.exit() | Process terminates |
| TC-IH-04 | Inventory Key | Chest closed | Toggles inventory | Chest open (blocked) |
| TC-IH-06 | Interaction Guard | Inventory open | E key does not trigger interaction | Inventory closed |

---

### Linked Test Functions

| Test ID | Test Function | File |
|---------|---------------|------|
| GF-001 | `test_save_thumbnail_creates_file` | `../../tests/engine/test_save_manager.py:L14` |
| GF-002 | `test_save_manager_load_valid` | `../../tests/engine/test_save_manager.py:L40` |
| GF-003 | `test_get_state_has_keys` | `../../tests/engine/test_game.py:L681` |
| GF-004 | `test_interaction_manager_is_interactable` | `../../tests/engine/test_interaction.py:L60` |
| GF-005 | `test_interaction_manager_handle_interactions` | `../../tests/engine/test_interaction.py:L150` |
| GF-006 | `test_dialogue_manager_start` | `../../tests/ui/test_dialogue.py:L40` |
| GF-007 | `test_dialogue_manager_skip` | `../../tests/ui/test_dialogue.py:L60` |
| GF-008 | `test_dialogue_manager_paging` | `../../tests/ui/test_dialogue.py:L100` |
| GF-009 | `test_game_ui_toggles` | `../../tests/engine/test_game.py:L90` |
| GF-010 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py:L186` |
| GF-011 | `test_save_menu_save_clicked` | `../../tests/ui/test_save_menu.py:L100` |
| GF-012 | `test_save_menu_overlay_back_clicked` | `../../tests/ui/test_save_menu.py:L120` |
| GF-013 | `test_save_menu_overlay_slot_clicked` | `../../tests/ui/test_save_menu.py:L140` |
| GF-014 | `test_handle_events_quit` | `../../tests/engine/test_game.py:L438` |
| GF-015 | `test_toggle_fullscreen_success` | `../../tests/engine/test_game.py:L497` |
| GF-016 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py:L186` |
| GF-017 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py:L186` |
| GF-018 | `test_game_transition_map_fade` | `../../tests/engine/test_game.py:L250` |
| GF-019 | `test_initial_state` | `../../tests/engine/test_game_state_manager.py:L72` |
| GF-020 | `test_handle_title_new_game` | `../../tests/engine/test_game_state_manager.py:L77` |
| GF-021 | `test_handle_title_load_game` | `../../tests/engine/test_game_state_manager.py:L84` |
| GF-022 | `test_handle_title_quit` | `../../tests/engine/test_game_state_manager.py:L104` |
| GF-023 | `test_handle_playing_pause_requested` | `../../tests/engine/test_game_state_manager.py:L112` |
| GF-024 | `test_handle_paused_resume` | `../../tests/engine/test_game_state_manager.py:L123` |
| GF-025 | `test_handle_paused_save_requested` | `../../tests/engine/test_game_state_manager.py:L131` |
| GF-026 | `test_handle_paused_goto_title` | `../../tests/engine/test_game_state_manager.py:L142` |
| GF-027 | `test_save_to_first_free_slot` | `../../tests/engine/test_game_state_manager.py:L167` |
| GF-028 | `test_save_to_first_free_slot_all_full` | `../../tests/engine/test_game_state_manager.py:L175` |
| GF-029 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py:L186` |
| GF-030 | `test_on_escape` | `../../tests/engine/test_game_state_manager.py:L186` |
| GF-031 | `test_load_game_time_restored` | `../../tests/engine/test_game_state_manager.py:L221` |
| GF-032 | `test_handle_events_filtering` | `../../tests/engine/test_game_state_manager.py:L241` |
| GF-033 | `test_transition_to_title_resets_inventory_and_chest_ui` | `../../tests/engine/test_game_state_manager.py:L153` |
| GF-034 | `test_title_screen_draw_main_menu` | `../../tests/ui/test_title_screen.py:L20` |
| GF-035 | `test_title_screen_light_scale_factors` | `../../tests/ui/test_title_screen.py:L45` |
| GF-036 | `test_title_screen_options_state_transitions` | `../../tests/ui/test_title_screen.py:L70` |
| TC-IH-01 | `test_quit_event_calls_sys_exit` | `../../tests/engine/test_phase15_game.py:L1` |
| TC-IH-02 | `test_interact_key_no_dialogue_calls_handle_interactions` | `../../tests/engine/test_phase15_game.py:L1` |
| TC-IH-03 | `test_interact_key_with_dialogue_advances_dialogue` | `../../tests/engine/test_phase15_game.py:L1` |
| TC-IH-04 | `test_inventory_key_chest_closed_toggles_inventory` | `../../tests/engine/test_phase15_game.py:L1` |
| TC-IH-05 | `test_inventory_key_chest_open_does_not_toggle` | `../../tests/engine/test_phase15_game.py:L1` |
| TC-IH-06 | `test_interact_key_inventory_open_does_not_trigger_interaction` | `../../tests/engine/test_phase15_game.py:L1` |
| IT-IH-01 | `test_game_handle_events_delegates_to_input_handler` | `../../tests/engine/test_phase15_game.py:L1` |
