<!-- Generated: 2026-05-01 | Files scanned: 32 | Token estimate: ~350 -->

# Engine Logic Flow

## Movement Chain
`Player.input` (Keys) → `BaseEntity.move` (Calculation) → `Game._is_collidable` (Validation via MapManager & Groups) → `rect` update

## Interaction Chain
`INTERACT_KEY` (E) → `InteractionManager.handle_interactions`
- `_check_npc_interactions`: 1-tile distance check → `NPC.interact()` → `Game._trigger_npc_bubble()`
- `_check_object_interactions`: Orthogonal distance/facing check (<45px) → `InteractiveEntity.interact()` → Toggle State + SFX → `Game._trigger_dialogue` / `chest_ui.open()`
- `_check_pickup_interactions`: Orthogonal distance check (<48px) → `Inventory.add_item()` → `pickup.kill()`
`Game.toggle_entity_by_id(target_id)` (Chains switches to doors/events)

## Chest & Inventory UI
`CHEST_UI / INVENTORY_UI` open blocks player input and pauses `TimeSystem`.
- **Drag & Drop**: Retains absolute slot indexing. Padding with `None` matches `CHEST_MAX_SLOTS`.
- `add_item(id, qty)` / `create_item(id, qty)` → Updates slot data → UI redraw.
- `remove_item(index)` → `None`.

## Emote Chain
`InteractionManager.update` → `_check_proximity_emotes`
- Check proximity to interactives/NPCs (<48px).
- `Player.playerEmote('interact')` → Spawns `EmoteSprite` (!).
`InteractionManager.handle_interactions` (Failed check)
- `Player.playerEmote('question')` (?).

## Dialogue & Speech Bubbles
- **Speech Bubble (NPCs)**: Nine-patch bubble rendered above NPC. Auto-wraps 224px. Paginated text. Includes Name Plate (`23-bubble_name.png`).
- **Dialogue (Signs)**: `DialogueManager.start_dialogue` → `_paginate` → Typewriter text animation on HUD overlay.

## Map Loading & Teleportation
`Game._check_teleporters` (Arrival / Intent) → `transition_map()` (Fade)
`_load_map()` → `AssetManager.clear()` → `TmjParser.load_map()` → `MapManager` → `_spawn_entities()`
Entities spawned load their state from `WorldState` via `_world_state_key`.
