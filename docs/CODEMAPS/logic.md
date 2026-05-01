<!-- Generated: 2026-05-01 | Files scanned: 34 | Token estimate: ~430 -->

# Engine Logic Flow

## Movement Chain
`Player.input()` (WASD/Arrows) → `BaseEntity.move(dt)` → `Game._is_collidable()` (MapManager tile check + obstacle group) → `rect` update + animation frame

## Interaction Chain
`INTERACT_KEY (E)` → `InteractionManager.handle_interactions()`
- `_check_npc_interactions()`: dist < 48px + facing → `NPC.interact()` → `Game._trigger_npc_bubble()`
- `_check_object_interactions()`: orthogonal dist < 45px + facing within 45° → `InteractiveEntity.interact()` → toggle `is_on` + SFX → `WorldState.set()` → `Game._trigger_dialogue()` / `chest_ui.open()`
- `_check_pickup_interactions()`: dist < 48px → `Inventory.add_item()` → `WorldState.set({looted:True})` → `pickup.kill()`
- `toggle_entity_by_id(target_id)`: lever chains to linked doors/events (depth-limited recursion, max 5)

## Inventory UI State Machine (`src/ui/inventory.py`)
```
IDLE → MOUSE_DOWN on item → DRAGGING → MOUSE_UP
  DRAGGING → on grid slot   → _transfer_dragged_to_grid(target_idx)
  DRAGGING → on equip slot  → _transfer_dragged_to_equipment(target_name)
  DRAGGING → on empty area  → cancel drag (item returns to origin)
```
- Equipment slot validity: checks `item.slot == target_name` before placing.
- Grid D&D: stack merge if same `item_id` and `stackable`; swap otherwise.
- `INVENTORY_KEY (I)` blocked when `chest_ui.is_open == True`.

## Chest UI State Machine (`src/ui/chest.py`)
```
IDLE → MOUSE_DOWN on chest/inv slot → DRAGGING → MOUSE_UP
  DRAGGING → chest slot    → _transfer_dragged_to_chest(target_idx)
  DRAGGING → inv slot      → _transfer_dragged_to_inventory(target_idx)
  ARROW_RIGHT click        → _transfer_chest_to_inventory() (all items)
  ARROW_LEFT click         → _transfer_inventory_to_chest() (all items)
  INV_ARROW_RIGHT/LEFT     → _scroll_right() / _scroll_left() (page = 18 slots)
```
- Chest storage: fixed-size `list[dict | None]` padded to `CHEST_MAX_SLOTS (20)`.
- Auto-close: `InteractionManager._check_chest_auto_close()` when player dist > threshold.

## InteractiveEntity Animated State Machine (`src/entities/interactive.py`)
```
is_on=False → interact() → is_on=True  → animation plays (start_row..end_row loop)
is_on=True  → interact() → is_on=False → animation resets to frame 0
sub_types: chest | lever | door | sign | animated_decor
```
- Animated decor `off_position`: spritesheet column switch on toggle.
  - `off_position=-1` (default) → single-column, no switch (backward compat).
  - `off_position=N` → `col_index=N` when `is_on=False`, `col_index=on_position` when `True`.
  - `restore_state({'is_on': bool})` also updates `col_index` via `_update_col_index()`.
- Linked entities (levers→doors): toggled via `Game.toggle_entity_by_id(target_id)`.

## Emote Chain
`InteractionManager.update()` → `_check_proximity_emotes()`
- `_check_interactive_emote()` / `_check_npc_emote()` / `_check_pickup_emote()`: dist < 48px → `Player.playerEmote('interact')` → `EmoteManager.trigger('!')`.
- Failed interaction check → `Player.playerEmote('question')` → `EmoteManager.trigger('?')`.

## Dialogue & Speech Bubbles
- **Sign/Book (DialogueManager)**: `start_dialogue(text, title)` → `_paginate()` → typewriter render → `advance()` pages → `is_active=False`.
- **NPC (SpeechBubble)**: `SpeechBubble(npc, text)` → nine-patch above NPC, name plate, paginated. `_advance_npc_bubble()` → next page or close.

## Lighting Pipeline (`src/engine/lighting.py`)
`LightingManager.create_overlay(screen, sprites, cam_offset, time_alpha)`
1. Create dark overlay (`night_alpha` from `TimeSystem`).
2. `_get_beam_surface_for_time()`: slanted window beam polygon (UV-mapped quad via `_compute_slant()`).
3. Blit beam with `BLEND_RGBA_ADD` over overlay.
4. Per-sprite torch: `_get_torch_mask(radius, intensity)` → radial gradient → `BLEND_RGBA_ADD` punch-through.
5. Overlay blit on screen.

## Map Loading & Teleportation
`Game._check_teleporters()` → on arrival tile or intent tile → `transition_map(target_map, spawn_id, type)`
`transition_map()` → fade out → `_load_map()` → `AssetManager.clear()` → `TmjParser.load_map()` → `MapManager` → `_spawn_entities()` → entities call `WorldState.get(key)` to restore state → fade in.

## Time System
`TimeSystem.update(dt)` → accumulates `elapsed_seconds` → `world_time` (hour/minute/season) → `night_alpha` (0–200) → `brightness` (float 0.0–1.0) → drives `LightingManager` and `GameHUD` clock display.
