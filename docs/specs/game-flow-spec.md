# Technical Specification — Game Flow & Save System [Implementation]

> Document Type: Implementation

**Document type :** Implementation  
**Date :** 2026-05-02  
**Status :** ✅ Prêt pour BUILD  
**ADRs :** ADR-001, ADR-002, ADR-003  
**Blueprint :** `docs/strategic/blueprint.md`

---

## Assumptions

| # | Assumption | Risk |
|---|---|---|
| A1 | `Item` est un dataclass Python pur — sérialisable via `.__dict__` | LOW — confirmé par `inventory_system.py` |
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
        # SlotInfo = dataclass { slot_id, saved_at, playtime_seconds, location, map_name }

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

### 2.2 `src/ui/title_screen.py` [NEW]

**Responsabilité :** Affichage et navigation du menu principal.

**Layout sur écran 1280×720 :**

```
┌──────────────────────────────────────────────┐  720px
│           [LOGO — centré, y=120]             │
│                                              │
│         [BTN Nouvelle Partie — y=330]        │
│         [BTN Charger         — y=330+70]     │
│         [BTN Options         — y=330+140]    │
│         [BTN Quitter         — y=330+210]    │
└──────────────────────────────────────────────┘ 1280px
```

**Dimensions boutons (scaled) :**
- Source : 341×182 px (1/3 de la spritesheet)
- Cible : **400×86** px (scale=1.173 en largeur, 86px de hauteur)
- Centré horizontalement : `x = (1280 - 400) // 2 = 440`
- Espacement vertical : **70px** entre tops
- 4 boutons → zone de hauteur : `3 * 70 + 86 = 296px`
- Zone de départ : `y_start = (720 - 296) // 2 + 80 = 302` (décalé vers le bas pour laisser de la place au logo)

**Logo :**
- Source : 903×241 px
- Scale : `width = 560px` → `scale = 560/903 = 0.620`
- Hauteur résultante : `int(241 * 0.620) = 149px`
- Position : `x = (1280-560)//2 = 360`, `y = 60`
- Colorkey : `(0, 0, 0)` appliqué après chargement

**État machine de la TitleScreen :**
```
MAIN_MENU → (clic Charger)  → LOAD_MENU  (overlay panel + slots)
MAIN_MENU → (clic Options)  → OPTIONS    (overlay panel + stub)
MAIN_MENU → (clic Quitter)  → QUIT       (pygame.quit + sys.exit)
LOAD_MENU → (clic slot)     → retourne GameEvent.LOAD_GAME(slot_id)
LOAD_MENU → (ESC)           → MAIN_MENU
```

**Interface publique :**
```python
class TitleScreen:
    def __init__(self, screen: pygame.Surface, save_manager: SaveManager)
    def handle_event(self, event: pygame.Event) -> GameEvent | None
    def update(self, dt: float) -> None
    def draw(self) -> None
```

**`GameEvent` (enum) :**
```python
class GameEvent(Enum):
    NONE = "none"
    NEW_GAME = "new_game"
    LOAD_GAME = "load_game"       # .slot_id contient 1..3
    QUIT = "quit"
    PAUSE_REQUESTED = "pause_requested"
    RESUME = "resume"
    GOTO_TITLE = "goto_title"
```

**Rendu des boutons (spritesheet) :**
```python
# Découpe de 02-menu_buttons.png
BTN_W_SRC = 341
BTN_H_SRC = 182
rects = {
    "idle":    pygame.Rect(0,           0, BTN_W_SRC, BTN_H_SRC),
    "hover":   pygame.Rect(BTN_W_SRC,   0, BTN_W_SRC, BTN_H_SRC),
    "pressed": pygame.Rect(BTN_W_SRC*2, 0, BTN_W_SRC, BTN_H_SRC),
}
```

**Rendu des save slots (spritesheet) :**
```python
# Découpe de 04-save_slot.png
SLOT_H_SRC = 512   # moitié de 1024
rects = {
    "idle":  pygame.Rect(0, 0,        1024, SLOT_H_SRC),
    "hover": pygame.Rect(0, SLOT_H_SRC, 1024, SLOT_H_SRC),
}
# Scaled target: 800×120px dans le panel
```

---

### 2.3 `src/engine/game_state_manager.py` [NEW]

**Responsabilité :** Boucle principale, orchestration des états.

**États :**
```python
class GameState(Enum):
    TITLE   = "title"
    PLAYING = "playing"
    PAUSED  = "paused"
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
- Retourne `GameEvent.PAUSE_REQUESTED` si ESC intercepté, sinon `GameEvent.NONE`
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
- Si 3 slots occupés → affiche `LoadMenu` pour choisir lequel écraser
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

3. **Suppression de `Settings.QUIT_KEY`** dans `_handle_events()` :
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

## 3. Anti-Patterns (DO NOT)

| ❌ Don't | ✅ Do Instead | Why |
|---|---|---|
| Appeler `Game()` dans `GameStateManager.__init__()` sans `skip_map_load=True` | `Game(skip_map_load=True)` | Charge une map inutile avant même d'afficher le menu |
| Utiliser `pickle` pour les saves | JSON via `json.dump` | Non lisible, fragile aux refactors de classes |
| Stocker `name`/`description`/`icon` dans le JSON de save | Ne stocker que `id` + `quantity` | Ces champs sont reconstruits depuis `propertytypes.json` |
| `pygame.display.init()` dans `TitleScreen` | Le display est déjà init dans `Game.__init__` | Double init = crash |
| Modifier `Game.run()` | Ajouter `Game.run_frame()` à côté | Les 444 tests existants appellent `run()` |
| Hardcoder les positions de boutons | Calculer depuis `Settings.WINDOW_WIDTH/HEIGHT` | Ne supporte pas le changement de résolution |
| Appeler `sys.exit()` depuis `TitleScreen` | Retourner `GameEvent.QUIT` | Séparation des responsabilités |
| Écrire dans `saves/` sans `os.makedirs(exist_ok=True)` | Toujours créer le dossier d'abord | `saves/` peut ne pas exister au 1er lancement |
| `open(path, "w")` sans `try/except` sur les saves | Wrapper dans `try/except IOError` | Disque plein, permissions, etc. |
| Tester les coordonnées de boutons avec des valeurs hardcodées | Tester les `GameEvent` retournés | Les positions changent avec la résolution |

---

## 4. Test Case Specifications

### Unit Tests — `SaveManager`

| ID | Composant | Input | Expected Output |
|---|---|---|---|
| TC-001 | `list_slots()` | Dossier `saves/` vide | `[None, None, None]` |
| TC-002 | `save(1, game)` | Game avec map + inventory | Fichier `saves/slot_1.json` créé, `version` correct |
| TC-003 | `load(1)` | Slot 1 existant | `SaveData` avec `player.map_name` correct |
| TC-004 | `load(2)` | Slot 2 vide | `None` |
| TC-005 | `load(1)` | JSON corrompu | `None` + log WARNING |
| TC-006 | `delete(1)` | Slot 1 existant | Fichier supprimé, `slot_exists(1) == False` |
| TC-007 | Inventory roundtrip | Item dans slot 3, equip LEFT_HAND | Après load, `slots[3].id == "sword_iron"`, `equipment["LEFT_HAND"].id == "sword_iron"` |
| TC-008 | WorldState roundtrip | `world_state = {"key": {"is_on": True}}` | Après load, `world_state.get("key")["is_on"] == True` |

### Unit Tests — `TitleScreen`

| ID | Composant | Input | Expected Output |
|---|---|---|---|
| TC-009 | `handle_event()` | MOUSEBUTTONDOWN sur bouton "Nouvelle Partie" | `GameEvent.NEW_GAME` |
| TC-010 | `handle_event()` | MOUSEBUTTONDOWN sur bouton "Charger" | Transition vers `LOAD_MENU` (state interne) |
| TC-011 | `handle_event()` | MOUSEBUTTONDOWN sur bouton "Quitter" | `GameEvent.QUIT` |
| TC-012 | `handle_event()` | KEYDOWN K_ESCAPE depuis `LOAD_MENU` | Retour vers `MAIN_MENU` |
| TC-013 | `handle_event()` | Clic sur slot 2 en `LOAD_MENU` | `GameEvent.LOAD_GAME` avec `slot_id=2` |

### Unit Tests — `GameStateManager`

| ID | Composant | Input | Expected Output |
|---|---|---|---|
| TC-014 | `_handle_events()` | `pygame.QUIT` | `pygame.quit()` appelé |
| TC-015 | ESC en `PLAYING` | `K_ESCAPE` event | `state == GameState.PAUSED` |
| TC-016 | ESC en `PAUSED` | `K_ESCAPE` event | `state == GameState.PLAYING` |
| TC-017 | `_transition_to_playing(None)` | New game | `game._load_map()` appelé avec default_map |
| TC-018 | `_transition_to_playing(1)` | Slot 1 existant | `save_manager.load(1)` appelé, state = PLAYING |

### Integration Tests

| ID | Flow | Setup | Verification |
|---|---|---|---|
| IT-001 | Save → Load roundtrip | Game en jeu, save slot 1, reload slot 1 | `player.pos`, `time_system._total_minutes`, `world_state._state` identiques |
| IT-002 | Nouvelle partie depuis menu | `GameStateManager`, clic "Nouvelle Partie" | `game._current_map_name` = default_map, `state == PLAYING` |
| IT-003 | Pause → Save → Resume | En jeu, ESC, Sauvegarder, ESC | state = PLAYING, slot fichier créé |

---

## 5. Error Handling Matrix

| Erreur | Détection | Réponse | Fallback |
|---|---|---|---|
| `saves/slot_N.json` manquant | `FileNotFoundError` dans `load()` | Log DEBUG | Retourner `None` (slot vide) |
| JSON invalide | `json.JSONDecodeError` | Log WARNING "Slot N corrompu" | Retourner `None` |
| Version schéma incompatible | `data["version"] != SCHEMA_VERSION` | Log WARNING | Retourner `None` |
| Écriture disque impossible | `IOError` dans `save()` | Log ERROR | Ne pas crasher, afficher message UI |
| Asset menu manquant | `pygame.error` au chargement | Log ERROR | Surface 32×32 magenta (pattern existant) |
| `item_id` inconnu au chargement | `create_item()` → `tech_data = {}` | Log WARNING | Item avec `stack_max=1`, nom = item_id |
| `K_ESCAPE` hors état valide | Vérification `if state in (PLAYING, PAUSED)` | Ignorer silencieusement | — |

---

## 6. Deep Links

- `Game.__init__` → [game.py L57](src/engine/game.py#L57)
- `Game.run()` préservé → [game.py L546](src/engine/game.py#L546)
- `Game._handle_events()` (QUIT_KEY à supprimer) → [game.py L558-L567](src/engine/game.py#L558)
- `Inventory.create_item()` → [inventory_system.py L44](src/engine/inventory_system.py#L44)
- `Inventory.slots` structure → [inventory_system.py L23](src/engine/inventory_system.py#L23)
- `TimeSystem._total_minutes` → [time_system.py L65](src/engine/time_system.py#L65)
- `WorldState._state` → [world_state.py L4](src/engine/world_state.py#L4)
- `WorldState.make_key()` → [world_state.py L18](src/engine/world_state.py#L18)
- `Settings.QUIT_KEY` (à supprimer) → `src/config.py`
- Blueprint → [blueprint.md](docs/strategic/blueprint.md#architecture--décision-centrale)
- ADR-001 → [ADR-001](docs/ADRs/ADR-001-gamestate-architecture.md#décision)
- ADR-002 → [ADR-002](docs/ADRs/ADR-002-save-format.md#structure-du-fichier-savesslot_njson)
- ADR-003 → [ADR-003](docs/ADRs/ADR-003-key-mapping.md#décision)
