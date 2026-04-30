<!-- Generated: 2026-04-30 | Files scanned: ~15 | Token estimate: ~400 -->

# Engine Systems Map

## Input & Interaction Flow
Keyboard Event → Game.handle_input()
INTERACT_KEY → InteractionManager.handle_interactions() → NPC/Object/Pickup
NPC → NPC.interact() → Game._trigger_dialogue()
Object → InteractiveEntity.interact() → Toggle State + SFX + WorldState
Pickup → Inventory.add_item() → pickup.kill()

## Rendering Pipeline
Game._draw_background() (Pre-rendered Layer Surfaces)
  → VisibleSprites.custom_draw() (Y-sorted Entities)
    → Game._draw_foreground() (Depth-sorted Top Layers + Occlusion)
      → Game._draw_hud() (UI Overlays)

## Map Loading Lifecycle
Game._load_map() → AssetManager.clear()
  → TmjParser.load_map() (Parse JSON + Tilesets)
    → MapManager(map_data) (Initialize logic/layers)
      → Game._spawn_entities() (Interactive/NPC/Teleport)

## State & Time
- **WorldState**: Singleton tracking global flags (opened_chests, quest_progress).
- **TimeSystem**: 24h clock logic. Minute → Season transitions.
- **Night Overlay**: Dynamic alpha calculation for screen tinting based on hour.

## Localization & Assets
- **I18nManager**: Singleton loading localized text strings (`fr.json`), serving UI components directly.
- **AssetManager**: Singleton caching fonts (Noble, Narrative, Tech) and image resources.

## Key Methods
- `InteractionManager._check_proximity_emotes()`: Distance + Orientation check to trigger emotes.
- `InteractionManager._check_chest_auto_close()`: Called every tick from `update()` — auto-closes ChestUI when player exits zone.
- `InteractionManager._close_chest(chest, chest_ui)`: Centralized chest close sequence (animation + sfx + world_state + UI close + emote suppression).
- `InteractionManager.handle_interactions()`: Unified pickup/NPC/object dispatcher on key press.
- `MapManager.is_collidable(x, y)`: Bounding box collision query.
- `TmjParser._parse_tilelayer()`: Convert raw GIDs to 2D matrix.
- `Inventory.add_item(item_id, quantity) -> int`: Stackable item logic, returns remaining quantity.
