<!-- Generated: 2026-04-28 | Files scanned: ~15 | Token estimate: ~400 -->

# Engine Systems Map

## Input & Interaction Flow
Keyboard Event → Game.handle_input()
INTERACT_KEY → InteractionManager.handle_interaction() → Entity.on_interact()
Entity.on_interact() → DialogueManager / Inventory / WorldState modification

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

## Key Methods
- `InteractionManager.get_closest_entity()`: Distance + Orientation check.
- `MapManager.is_collidable(x, y)`: Bounding box collision query.
- `TmjParser._parse_tilelayer()`: Convert raw GIDs to 2D matrix.
- `Inventory.add_item()`: Stackable item logic + WorldState sync.
