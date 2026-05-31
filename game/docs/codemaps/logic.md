<!-- Generated: 2026-05-27 | Last doc-update: 2026-05-27 (Steps 1-11 remédiation) | Files scanned: 73 | Token estimate: ~1100 -->

# Engine Logic Flow

## GameStateManager State Machine (`src/engine/game_state_manager.py`)
```
TITLE   → GameEvent.new_game()          → _transition_to_playing(None)  → PLAYING
TITLE   → GameEvent.load_requested(N)   → _transition_to_playing(N)     → PLAYING
TITLE   → GameEvent.quit()              → sys.exit()
PLAYING → ESC (filtered, not re-posted) → _transition_to_paused()       → PAUSED
PAUSED  → GameEvent.resume()            → _transition_to_playing(None, resume=True) → PLAYING
PAUSED  → GameEvent.save_requested(N)   → save_manager.save(N, game) + thumbnail → PAUSED
PAUSED  → GameEvent.goto_title()        → _transition_to_title()        → TITLE
```
- `_save_to_first_free_slot()`: scans `list_slots()`, fallback slot 1 if all full.
- `_process_global_events()`: `pygame.QUIT` → `sys.exit()`, fullscreen toggle — every frame.

## Movement Chain
`Player.input()` (WASD/Arrows) → `BaseEntity.move(dt)` → `CollisionChecker.is_collidable()` (tile + obstacle group) → `rect` update + animation frame
- **Footsteps**: frames 1 and 3. `MapManager.get_terrain_material_at()` → depth≤1 tiles only. `AudioManager.play_sfx(footstep_{material})` with fallback.

## Interaction Chain
`INTERACT_KEY (E)` → `InteractionManager.handle_interactions()` (`distance_squared_to`, module-level `_RANGE_SQ_*` constants)
- `_check_npc_interactions()`: `sq_dist < _RANGE_SQ_48` + facing → `NPC.interact()` → `Game._trigger_npc_bubble()`
- `_check_object_interactions()`: `sq_dist < _RANGE_SQ_16/48` + facing 45° → respects `trigger_only` → `InteractiveEntity.interact()` → toggle `is_on` + SFX → `WorldState.set()` → dialogue / `chest_ui.open()`
- `_check_pickup_interactions()`: `sq_dist < _RANGE_SQ_48` → `Inventory.add_item()` → `WorldState.set({looted:True})` → `pickup.kill()`
- `toggle_entity_by_id(target_id)`: lever chains (depth-limited recursion, max 5).

## Inventory UI State Machine (`src/ui/inventory.py`)
```
IDLE → MOUSE_DOWN on item → DRAGGING → MOUSE_UP
  DRAGGING → grid slot   → _transfer_dragged_to_grid(idx)
  DRAGGING → equip slot  → _transfer_dragged_to_equipment(name)
  DRAGGING → empty area  → cancel (item returns to origin)
```
- Equipment: checks `item.slot == target_name`. Stack merge if same `item_id` + `stackable`.
- `INVENTORY_KEY (I)` blocked when `chest_ui.is_open == True`.

## Chest UI State Machine (`src/ui/chest.py`)
```
IDLE → MOUSE_DOWN on chest/inv slot → DRAGGING → MOUSE_UP
  DRAGGING → chest slot   → _transfer_dragged_to_chest(idx)
  DRAGGING → inv slot     → _transfer_dragged_to_inventory(idx)
  ARROW_RIGHT click       → _transfer_chest_to_inventory()
  ARROW_LEFT click        → _transfer_inventory_to_chest()
  INV_ARROW_RIGHT/LEFT    → _scroll_right() / _scroll_left() (18-slot pages)
```
- Auto-close: `InteractionManager._check_chest_auto_close()` when player dist > threshold.

## InteractiveEntity State Machine (`src/entities/interactive.py`)
```
is_on=False → interact() → is_on=True  → animation (start_row..end_row loop)
is_on=True  → interact() → is_on=False → animation reset to frame 0
sub_types: chest | lever | door | sign | animated_decor
```
- `off_position=-1` (default): single-column, no switch. `off_position=N`: col switch on toggle.
- `restore_state({'is_on': bool})` → `_update_col_index()`. Day/night toggle respects col.
- `sfx_ambient`: looping spatial audio when `is_on=True`. Volume scales with distance (20% floor).

## Emote Chain
`InteractionManager.update()` → `_check_proximity_emotes()`
- dist < 48px → `Player.playerEmote('interact')` → `EmoteManager.trigger('!')`
- Failed interaction → `Player.playerEmote('question')` → `EmoteManager.trigger('?')`

## Dialogue & Speech
- **Sign/Book**: `DialogueManager.start_dialogue(text, title)` → `_paginate()` → typewriter → `advance()` → `is_active=False`
- **NPC**: `SpeechBubble(npc, text)` → nine-patch above NPC → `_advance_npc_bubble()` → next page or close

## Lighting Pipeline (`src/engine/lighting.py`)
`LightingManager.create_overlay(screen, sprites, cam_offset, time_alpha)`
1. Dark overlay (`night_alpha` from `TimeSystem`)
2. `_get_beam_surface_for_time()`: slanted window beam polygon
3. Blit beam `BLEND_RGBA_ADD`
4. Per-sprite torch: `_get_torch_mask(radius, intensity)` → radial gradient → `BLEND_RGBA_ADD`
5. Overlay blit on screen

## Map Loading & Teleportation
`Game._check_teleporters()` → `transition_map(target_map, spawn_id, type)`
→ fade out → `MapLoader.load_map()` → `AssetManager.clear()` → `TmjParser.load_map()` → `MapManager` → `EntityFactory.spawn_entities()` → `WorldState.get(key)` restore → fade in

- **EntityFactory dispatch order**: interactive (`03-`) → NPC (`entity_type=='npc'` | `'15-npc'` | `07-`) → teleport (`15-`) → pickup (`08-`). ⚠️ NPC before teleport: `'15-npc'` shares `15-` prefix.

## Time System
`TimeSystem.update(dt)` → `_total_minutes @property` setter → `_compute_world_time()` (cache auto-refresh) → `_cached_world_time` → `world_time @property` → `night_alpha` → `brightness` → `LightingManager` + `GameHUD`

## Rendering Pipeline
`RenderManager.draw_scene()` → pre-computes `_frame_anim_all`/`_frame_anim_by_layer` (1x/frame)
→ `draw_background()` → `_apply_partial_occlusion()` → `_apply_grass_wading_to_images()` → `custom_draw()` → `draw_foreground() → OccludingRect`
- **Partial Occlusion**: sprite rects ∩ foreground tiles (depth > sprite.depth) → composite with `OCCLUSION_ALPHA` (50%). Skips player during scripted intra-map walks.
- **Grass Wading**: `MapManager.get_grass_tile_image_at()` at foot center → reblit grass over bottom 8px. Skips player during scripted walks.
- **Test contract**: tests calling `draw_background()`/`draw_foreground()` directly must pre-populate `_frame_anim_by_layer`/`_frame_anim_all` (see A-PERF-002).
