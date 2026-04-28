<!-- Generated: 2026-04-24 | Files scanned: 10 | Token estimate: ~350 -->

# Engine Logic & Data Flow

## Map Loading Flow
Game._load_map(name) → TmjParser.load_map() → TileProperty Resolver → Game._spawn_entities()
Game._spawn_entities() → WorldState.get_state() → InteractiveEntity Init → Game.interactived.add()

## Interaction Chain
Input (E) → Game._handle_interactions() → Player.get_target_rect() → Entity.interact()
Entity.interact() → DialogueManager.start_dialogue() OR Toggle State → Target ID Check
Target ID Check → Game.find_entity(target_id) → Target.interact()

## Collision Logic
Entity.move() → Game._is_collidable() → Obstacles Group + Interactives + NPCs
If collide → move cancelled → move_timer reset

## UI & Dialogue State Machine
1. **Trigger**: `Game._trigger_dialogue(id)` → `HUD._lang.get(key)` → `DialogueManager.start_dialogue(msg)`
2. **Paging**: `_paginate()` wraps text into `_pages` (max 3-5 lines per page).
3. **Animation**: `update()` advances typewriter char index. `_is_page_complete` set when full page revealed.
4. **Input**: `INTERACT_KEY` → `DialogueManager.advance()`:
   - If typing: skip to end of page.
   - If page complete: flip to next page.
   - If last page: set `is_active=False` and restore player control.

## Inventory & Custom Cursor
1. **Init**: `Settings.CURSOR_SIZE` → `InventoryUI` scales `05-pointer` assets (preserves 309x535 ratio).
2. **State**: `InventoryUI.toggle()` handles `mouse.set_visible()`.
3. **Render**: `InventoryUI.draw()` blits the custom pointer at `pygame.mouse.get_pos()` as the absolute final step.

## Teleportation Pipeline
1. **Detection**: `Game.update()` → `_check_teleporters()`
2. **Trigger Types**:
   - **Arrival**: `was_moving=True` + `is_moving=False` (triggers if facing matches).
   - **Intent**: `is_moving=False` + `magnitude > 0` (triggers if facing matches).
3. **Logic**: `Game.transition_map()` → Fade Out → `_load_map()` → `_spawn_entities()` → Fade In.
