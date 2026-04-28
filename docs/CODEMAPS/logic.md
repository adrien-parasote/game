<!-- Generated: 2026-04-28 | Files scanned: 25 | Token estimate: ~500 -->

# Engine Logic Flow

## Movement Chain
`Player.input` (Keys) → `BaseEntity.move` (Calculation) → `Game._is_collidable` (Validation) → `rect` update

## Interaction Chain
`INTERACT_KEY` (E) → `InteractionManager.handle_interactions`
- `_check_npc_interactions`: rect projection at 1-tile range
- `_check_object_interactions`: distance (<45px) + orientation check
- `_check_pickup_interactions`: distance (<48px) → `Inventory.add_item`
- Door Relaxation (Bypass orientation for open doors, `is_on=True`)
- SFX → `audio_manager.play_sfx(obj.sfx)`
- `Game.toggle_entity_by_id(target_id, depth=1)` (Chaining)

## Emote Chain
`InteractionManager.update` → `_check_proximity_emotes`
- Check proximity to interactives/NPCs (<48px)
- `Player.playerEmote('interact')` → `EmoteManager.trigger` → `EmoteSprite` spawn
`InteractionManager.handle_interactions` (Failed check)
- `Player.playerEmote('question')` (Optional via `Settings.ENABLE_FAILED_INTERACTION_EMOTE`)
`EmoteSprite.update`
- Follow player + Rise 15px
- Self-destruct after 1s

## Dialogue Chain
`Game._trigger_dialogue` → `DialogueManager.start_dialogue`
- Pre-calculates wrapping via `_paginate`
- `update()` handles character-by-character typewriter animation
- `advance()` handles page skipping and closing

## Inventory Chain
`INVENTORY_KEY` (I) → `InventoryUI.toggle`
- Sets `is_open = !is_open`
- Toggles `pygame.mouse.set_visible()`
- Pauses/Unpauses `TimeSystem` (via `Game` loop)
- Custom cursor rendering takes over when open

## Teleport Chain
`Game._check_teleporters` (Arrival/Intent)
- `TransitionType` (Fade/Instant)
- `transition_map` → `_load_map`
- Full group cleanup + Player repositioning

## Time & Environment
`TimeSystem.update(dt)`
- `minutes` → `hours` → `days` → `seasons`
- `night_alpha` modulation (Sinusoidal)
- `InteractiveEntity.draw_effects` (Halo intensity scaling)
