# Cross-Spec Validation Report

**Project:** Master Specification Index [Strategic]
**Language:** mixed
**Specs validated:** 23 modules + 1 Master
**Date:** 2026-06-10

## Summary

| Check | Status | Issues |
|---|---|---|
| 1. Global Access Patterns | ⏭️ SKIP | 0 |
| 2. Constant Naming | ❌ FAIL | 7 |
| 3. Numeric Mapping Consistency | ✅ PASS | 0 |
| 4. Callback Safety Rules | ⏭️ SKIP | 0 |
| 5. Coverage Matrix | ⏭️ SKIP | 0 |
| 6. Dependency Acyclicity | ⏭️ SKIP | 0 |
| 7. Shared Artifact Schema | ✅ PASS | 0 |
| 8. Cross-Spec Invocation Contract | ⏭️ SKIP | 0 |
| 9. File Tree Completeness | ❌ FAIL | 90 |
| 10. Concept Coherence | ✅ PASS | 0 |

**Total: 97 issues, 97 critical**

## Detailed Issues

### ⏭️ 1. Global Access Patterns — SKIPPED

Reason: Check 'global_access_patterns' not activated by any preset. Active presets: python, universal

### ❌ 2. Constant Naming (7 issues)

**Issue C1** — Possible typo: `BLEND_RGBA_MIN` used but `BLEND_RGBA_MULT` declared (similarity: 80%).
- Used in: pixel-perfect-occlusion.md
- Suggested fix: Rename `BLEND_RGBA_MIN` to `BLEND_RGBA_MULT` or declare `BLEND_RGBA_MIN` explicitly.

**Issue C2** — Undeclared constant `FALLBACK_SURF_SIZE` used in 1 spec(s).
- Used in: code-quality-constants-i18n.md
- Suggested fix: Declare `FALLBACK_SURF_SIZE` in the canonical constants source or remove the reference.

**Issue C3** — Undeclared constant `IT_` used in 1 spec(s).
- Used in: pixel-perfect-occlusion.md
- Suggested fix: Declare `IT_` in the canonical constants source or remove the reference.

**Issue C4** — Undeclared constant `MAX_AUDIO_DISTANCE` used in 1 spec(s).
- Used in: audio-system.md
- Suggested fix: Declare `MAX_AUDIO_DISTANCE` in the canonical constants source or remove the reference.

**Issue C5** — Undeclared constant `PANEL_H` used in 1 spec(s).
- Used in: code-quality-constants-i18n.md
- Suggested fix: Declare `PANEL_H` in the canonical constants source or remove the reference.

**Issue C6** — Undeclared constant `PANEL_W` used in 1 spec(s).
- Used in: code-quality-constants-i18n.md
- Suggested fix: Declare `PANEL_W` in the canonical constants source or remove the reference.

**Issue C7** — Undeclared constant `UT_` used in 1 spec(s).
- Used in: pixel-perfect-occlusion.md
- Suggested fix: Declare `UT_` in the canonical constants source or remove the reference.

### ✅ 3. Numeric Mapping Consistency — PASS

Found 1 numeric mapping tables across 24 specs.

### ⏭️ 4. Callback Safety Rules — SKIPPED

Reason: Check 'callback_safety_rules' not activated by any preset. Active presets: python, universal

### ⏭️ 5. Coverage Matrix — SKIPPED

Reason: No Coverage Matrix table found in Master Spec — check skipped. Expected a table with 'Feature ID' and 'Spec file' columns under a '## Coverage Matrix' heading.

### ⏭️ 6. Dependency Acyclicity — SKIPPED

Reason: No `Depends on:` / `Dépend de:` headers found in module specs — check skipped.

### ✅ 7. Shared Artifact Schema — PASS

Audited 0 cross-spec artifact paths across 24 specs.

### ⏭️ 8. Cross-Spec Invocation Contract — SKIPPED

Reason: No cross-spec invocations detected (no CLI calls, HTTP routes, or env var usage).

### ❌ 9. File Tree Completeness (90 issues)

**Issue F1** — Spec `00_MASTER.md` references path `time_system.py` but no spec's file tree declares it.
- Used in: 00_MASTER.md
- Suggested fix: Either: (a) add `time_system.py` to the file tree of the spec that owns this deliverable, or (b) mark `time_system.py` as an external dependency if it's not produced by this project.

**Issue F2** — Spec `audio-system.md` references path `../../tests/entities/test_bridge_sfx.py` but no spec's file tree declares it.
- Used in: audio-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_bridge_sfx.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_bridge_sfx.py` as an external dependency if it's not produced by this project.

**Issue F3** — Spec `audio-system.md` references path `../../tests/engine/test_bridge_sfx_interaction.py` but no spec's file tree declares it.
- Used in: audio-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_bridge_sfx_interaction.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_bridge_sfx_interaction.py` as an external dependency if it's not produced by this project.

**Issue F4** — Spec `audio-system.md` references path `../../tests/entities/test_bridge_sfx_player.py` but no spec's file tree declares it.
- Used in: audio-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_bridge_sfx_player.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_bridge_sfx_player.py` as an external dependency if it's not produced by this project.

**Issue F5** — Spec `chest-ui.md` references path `chest_constants.py` but no spec's file tree declares it.
- Used in: chest-ui.md
- Suggested fix: Either: (a) add `chest_constants.py` to the file tree of the spec that owns this deliverable, or (b) mark `chest_constants.py` as an external dependency if it's not produced by this project.

**Issue F6** — Spec `chest-ui.md` references path `chest.py` but no spec's file tree declares it.
- Used in: chest-ui.md
- Suggested fix: Either: (a) add `chest.py` to the file tree of the spec that owns this deliverable, or (b) mark `chest.py` as an external dependency if it's not produced by this project.

**Issue F7** — Spec `chest-ui.md` references path `chest_transfer.py` but no spec's file tree declares it.
- Used in: chest-ui.md
- Suggested fix: Either: (a) add `chest_transfer.py` to the file tree of the spec that owns this deliverable, or (b) mark `chest_transfer.py` as an external dependency if it's not produced by this project.

**Issue F8** — Spec `chest-ui.md` references path `../../tests/test_chest_ui.py` but no spec's file tree declares it.
- Used in: chest-ui.md
- Suggested fix: Either: (a) add `../../tests/test_chest_ui.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/test_chest_ui.py` as an external dependency if it's not produced by this project.

**Issue F9** — Spec `chest-ui.md` references path `../../tests/test_transfer_logic.py` but no spec's file tree declares it.
- Used in: chest-ui.md
- Suggested fix: Either: (a) add `../../tests/test_transfer_logic.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/test_transfer_logic.py` as an external dependency if it's not produced by this project.

**Issue F10** — Spec `chest-ui.md` references path `../../tests/test_interaction.py` but no spec's file tree declares it.
- Used in: chest-ui.md
- Suggested fix: Either: (a) add `../../tests/test_interaction.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/test_interaction.py` as an external dependency if it's not produced by this project.

**Issue F11** — Spec `code-quality-constants-i18n.md` references path `_constants.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `_constants.py` to the file tree of the spec that owns this deliverable, or (b) mark `_constants.py` as an external dependency if it's not produced by this project.

**Issue F12** — Spec `code-quality-constants-i18n.md` references path `ui_colors.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `ui_colors.py` to the file tree of the spec that owns this deliverable, or (b) mark `ui_colors.py` as an external dependency if it's not produced by this project.

**Issue F13** — Spec `code-quality-constants-i18n.md` references path `engine_constants.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `engine_constants.py` to the file tree of the spec that owns this deliverable, or (b) mark `engine_constants.py` as an external dependency if it's not produced by this project.

**Issue F14** — Spec `code-quality-constants-i18n.md` references path `save_menu_constants.py` but no spec's file tree declares it.
- Used in: code-quality-constants-i18n.md
- Suggested fix: Either: (a) add `save_menu_constants.py` to the file tree of the spec that owns this deliverable, or (b) mark `save_menu_constants.py` as an external dependency if it's not produced by this project.

**Issue F15** — Spec `development-quality.md` references path `inventory_system.py` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `inventory_system.py` to the file tree of the spec that owns this deliverable, or (b) mark `inventory_system.py` as an external dependency if it's not produced by this project.

**Issue F16** — Spec `development-quality.md` references path `spritesheet.py` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `spritesheet.py` to the file tree of the spec that owns this deliverable, or (b) mark `spritesheet.py` as an external dependency if it's not produced by this project.

**Issue F17** — Spec `development-quality.md` references path `emote_sprite.py` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `emote_sprite.py` to the file tree of the spec that owns this deliverable, or (b) mark `emote_sprite.py` as an external dependency if it's not produced by this project.

**Issue F18** — Spec `development-quality.md` references path `teleport.py` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `teleport.py` to the file tree of the spec that owns this deliverable, or (b) mark `teleport.py` as an external dependency if it's not produced by this project.

**Issue F19** — Spec `development-quality.md` references path `game/src/` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `game/src/` to the file tree of the spec that owns this deliverable, or (b) mark `game/src/` as an external dependency if it's not produced by this project.

**Issue F20** — Spec `development-quality.md` references path `settings.json` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `settings.json` to the file tree of the spec that owns this deliverable, or (b) mark `settings.json` as an external dependency if it's not produced by this project.

**Issue F21** — Spec `development-quality.md` references path `../../tests/scripts/build/test_release.py` but no spec's file tree declares it.
- Used in: development-quality.md
- Suggested fix: Either: (a) add `../../tests/scripts/build/test_release.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/scripts/build/test_release.py` as an external dependency if it's not produced by this project.

**Issue F22** — Spec `dialogue-system.md` references path `../../tests/ui/test_dialogue.py` but no spec's file tree declares it.
- Used in: dialogue-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_dialogue.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_dialogue.py` as an external dependency if it's not produced by this project.

**Issue F23** — Spec `dialogue-system.md` references path `../../tests/ui/test_speech_bubble.py` but no spec's file tree declares it.
- Used in: dialogue-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_speech_bubble.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_speech_bubble.py` as an external dependency if it's not produced by this project.

**Issue F24** — Spec `dialogue-system.md` references path `../../tests/ui/test_inventory.py` but no spec's file tree declares it.
- Used in: dialogue-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_inventory.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_inventory.py` as an external dependency if it's not produced by this project.

**Issue F25** — Spec `dialogue-system.md` references path `test_dialogue.py` but no spec's file tree declares it.
- Used in: dialogue-system.md
- Suggested fix: Either: (a) add `test_dialogue.py` to the file tree of the spec that owns this deliverable, or (b) mark `test_dialogue.py` as an external dependency if it's not produced by this project.

**Issue F26** — Spec `engine-core.md` references path `../../tests/engine/test_game.py` but no spec's file tree declares it.
- Used in: engine-core.md
- Suggested fix: Either: (a) add `../../tests/engine/test_game.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_game.py` as an external dependency if it's not produced by this project.

**Issue F27** — Spec `engine-core.md` references path `../../tests/engine/test_game_state_manager.py` but no spec's file tree declares it.
- Used in: engine-core.md
- Suggested fix: Either: (a) add `../../tests/engine/test_game_state_manager.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_game_state_manager.py` as an external dependency if it's not produced by this project.

**Issue F28** — Spec `engine-core.md` references path `../../tests/engine/test_collision_checker.py` but no spec's file tree declares it.
- Used in: engine-core.md
- Suggested fix: Either: (a) add `../../tests/engine/test_collision_checker.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_collision_checker.py` as an external dependency if it's not produced by this project.

**Issue F29** — Spec `engine-core.md` references path `../../tests/engine/test_spatial_utils.py` but no spec's file tree declares it.
- Used in: engine-core.md
- Suggested fix: Either: (a) add `../../tests/engine/test_spatial_utils.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_spatial_utils.py` as an external dependency if it's not produced by this project.

**Issue F30** — Spec `engine-core.md` references path `../../tests/engine/test_phase15_game.py` but no spec's file tree declares it.
- Used in: engine-core.md
- Suggested fix: Either: (a) add `../../tests/engine/test_phase15_game.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_phase15_game.py` as an external dependency if it's not produced by this project.

**Issue F31** — Spec `engine-core.md` references path `../../tests/ui/test_title_screen.py` but no spec's file tree declares it.
- Used in: engine-core.md
- Suggested fix: Either: (a) add `../../tests/ui/test_title_screen.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_title_screen.py` as an external dependency if it's not produced by this project.

**Issue F32** — Spec `entities-system.md` references path `propertytypes.json` but no spec's file tree declares it.
- Used in: entities-system.md
- Suggested fix: Either: (a) add `propertytypes.json` to the file tree of the spec that owns this deliverable, or (b) mark `propertytypes.json` as an external dependency if it's not produced by this project.

**Issue F33** — Spec `entities-system.md` references path `../../tests/entities/test_interactive.py` but no spec's file tree declares it.
- Used in: entities-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_interactive.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_interactive.py` as an external dependency if it's not produced by this project.

**Issue F34** — Spec `entities-system.md` references path `../../tests/entities/test_sprite_frame_loading.py` but no spec's file tree declares it.
- Used in: entities-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_sprite_frame_loading.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_sprite_frame_loading.py` as an external dependency if it's not produced by this project.

**Issue F35** — Spec `entities-system.md` references path `../../tests/entities/test_entities.py` but no spec's file tree declares it.
- Used in: entities-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_entities.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_entities.py` as an external dependency if it's not produced by this project.

**Issue F36** — Spec `entities-system.md` references path `../../tests/engine/test_interaction.py` but no spec's file tree declares it.
- Used in: entities-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_interaction.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_interaction.py` as an external dependency if it's not produced by this project.

**Issue F37** — Spec `intra-map-teleport.md` references path `interaction.py` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `interaction.py` to the file tree of the spec that owns this deliverable, or (b) mark `interaction.py` as an external dependency if it's not produced by this project.

**Issue F38** — Spec `intra-map-teleport.md` references path `map_loader.py` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `map_loader.py` to the file tree of the spec that owns this deliverable, or (b) mark `map_loader.py` as an external dependency if it's not produced by this project.

**Issue F39** — Spec `intra-map-teleport.md` references path `map-world-system.md` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `map-world-system.md` to the file tree of the spec that owns this deliverable, or (b) mark `map-world-system.md` as an external dependency if it's not produced by this project.

**Issue F40** — Spec `intra-map-teleport.md` references path `../../tests/engine/test_intra_map_teleport.py` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `../../tests/engine/test_intra_map_teleport.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_intra_map_teleport.py` as an external dependency if it's not produced by this project.

**Issue F41** — Spec `intra-map-teleport.md` references path `../../tests/engine/test_render_order.py` but no spec's file tree declares it.
- Used in: intra-map-teleport.md
- Suggested fix: Either: (a) add `../../tests/engine/test_render_order.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_render_order.py` as an external dependency if it's not produced by this project.

**Issue F42** — Spec `inventory-system.md` references path `propertytypes.json` but no spec's file tree declares it.
- Used in: inventory-system.md
- Suggested fix: Either: (a) add `propertytypes.json` to the file tree of the spec that owns this deliverable, or (b) mark `propertytypes.json` as an external dependency if it's not produced by this project.

**Issue F43** — Spec `inventory-system.md` references path `loot_table.json` but no spec's file tree declares it.
- Used in: inventory-system.md
- Suggested fix: Either: (a) add `loot_table.json` to the file tree of the spec that owns this deliverable, or (b) mark `loot_table.json` as an external dependency if it's not produced by this project.

**Issue F44** — Spec `inventory-system.md` references path `../../tests/ui/test_inventory.py` but no spec's file tree declares it.
- Used in: inventory-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_inventory.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_inventory.py` as an external dependency if it's not produced by this project.

**Issue F45** — Spec `inventory-system.md` references path `../../tests/engine/test_loot_table.py` but no spec's file tree declares it.
- Used in: inventory-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_loot_table.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_loot_table.py` as an external dependency if it's not produced by this project.

**Issue F46** — Spec `lighting-system.md` references path `../../tests/engine/test_lighting.py` but no spec's file tree declares it.
- Used in: lighting-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_lighting.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_lighting.py` as an external dependency if it's not produced by this project.

**Issue F47** — Spec `lighting-system.md` references path `lighting_constants.py` but no spec's file tree declares it.
- Used in: lighting-system.md
- Suggested fix: Either: (a) add `lighting_constants.py` to the file tree of the spec that owns this deliverable, or (b) mark `lighting_constants.py` as an external dependency if it's not produced by this project.

**Issue F48** — Spec `lighting-system.md` references path `../../tests/engine/test_lighting_modes.py` but no spec's file tree declares it.
- Used in: lighting-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_lighting_modes.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_lighting_modes.py` as an external dependency if it's not produced by this project.

**Issue F49** — Spec `lighting-system.md` references path `engine-core.md` but no spec's file tree declares it.
- Used in: lighting-system.md
- Suggested fix: Either: (a) add `engine-core.md` to the file tree of the spec that owns this deliverable, or (b) mark `engine-core.md` as an external dependency if it's not produced by this project.

**Issue F50** — Spec `lighting-system.md` references path `map-world-system.md` but no spec's file tree declares it.
- Used in: lighting-system.md
- Suggested fix: Either: (a) add `map-world-system.md` to the file tree of the spec that owns this deliverable, or (b) mark `map-world-system.md` as an external dependency if it's not produced by this project.

**Issue F51** — Spec `lighting-system.md` references path `map_loader.py` but no spec's file tree declares it.
- Used in: lighting-system.md
- Suggested fix: Either: (a) add `map_loader.py` to the file tree of the spec that owns this deliverable, or (b) mark `map_loader.py` as an external dependency if it's not produced by this project.

**Issue F52** — Spec `map-world-system.md` references path `../../tests/engine/test_interaction.py` but no spec's file tree declares it.
- Used in: map-world-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_interaction.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_interaction.py` as an external dependency if it's not produced by this project.

**Issue F53** — Spec `map-world-system.md` references path `../../tests/engine/test_map_loader.py` but no spec's file tree declares it.
- Used in: map-world-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_map_loader.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_map_loader.py` as an external dependency if it's not produced by this project.

**Issue F54** — Spec `map-world-system.md` references path `../../tests/engine/test_phase15_game.py` but no spec's file tree declares it.
- Used in: map-world-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_phase15_game.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_phase15_game.py` as an external dependency if it's not produced by this project.

**Issue F55** — Spec `npc-system.md` references path `test_npc.py` but no spec's file tree declares it.
- Used in: npc-system.md
- Suggested fix: Either: (a) add `test_npc.py` to the file tree of the spec that owns this deliverable, or (b) mark `test_npc.py` as an external dependency if it's not produced by this project.

**Issue F56** — Spec `npc-system.md` references path `sprites/` but no spec's file tree declares it.
- Used in: npc-system.md
- Suggested fix: Either: (a) add `sprites/` to the file tree of the spec that owns this deliverable, or (b) mark `sprites/` as an external dependency if it's not produced by this project.

**Issue F57** — Spec `npc-system.md` references path `characters/` but no spec's file tree declares it.
- Used in: npc-system.md
- Suggested fix: Either: (a) add `characters/` to the file tree of the spec that owns this deliverable, or (b) mark `characters/` as an external dependency if it's not produced by this project.

**Issue F58** — Spec `npc-system.md` references path `../../tests/entities/test_entities.py` but no spec's file tree declares it.
- Used in: npc-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_entities.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_entities.py` as an external dependency if it's not produced by this project.

**Issue F59** — Spec `npc-system.md` references path `../../tests/entities/test_npc.py` but no spec's file tree declares it.
- Used in: npc-system.md
- Suggested fix: Either: (a) add `../../tests/entities/test_npc.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/entities/test_npc.py` as an external dependency if it's not produced by this project.

**Issue F60** — Spec `npc-system.md` references path `../../tests/engine/test_interaction.py` but no spec's file tree declares it.
- Used in: npc-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_interaction.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_interaction.py` as an external dependency if it's not produced by this project.

**Issue F61** — Spec `p001-foreground-rendering.md` references path `./research/p001-foreground-rendering.md` but no spec's file tree declares it.
- Used in: p001-foreground-rendering.md
- Suggested fix: Either: (a) add `./research/p001-foreground-rendering.md` to the file tree of the spec that owns this deliverable, or (b) mark `./research/p001-foreground-rendering.md` as an external dependency if it's not produced by this project.

**Issue F62** — Spec `p001-foreground-rendering.md` references path `pytest tests/engine/test_render_manager.py tests/engine/test_render_manager_coverage.py` but no spec's file tree declares it.
- Used in: p001-foreground-rendering.md
- Suggested fix: Either: (a) add `pytest tests/engine/test_render_manager.py tests/engine/test_render_manager_coverage.py` to the file tree of the spec that owns this deliverable, or (b) mark `pytest tests/engine/test_render_manager.py tests/engine/test_render_manager_coverage.py` as an external dependency if it's not produced by this project.

**Issue F63** — Spec `p001-foreground-rendering.md` references path `camera-rendering.md` but no spec's file tree declares it.
- Used in: p001-foreground-rendering.md
- Suggested fix: Either: (a) add `camera-rendering.md` to the file tree of the spec that owns this deliverable, or (b) mark `camera-rendering.md` as an external dependency if it's not produced by this project.

**Issue F64** — Spec `p001-foreground-rendering.md` references path `pixel-perfect-occlusion.md` but no spec's file tree declares it.
- Used in: p001-foreground-rendering.md
- Suggested fix: Either: (a) add `pixel-perfect-occlusion.md` to the file tree of the spec that owns this deliverable, or (b) mark `pixel-perfect-occlusion.md` as an external dependency if it's not produced by this project.

**Issue F65** — Spec `performance-system.md` references path `../../tests/engine/test_performance_optimizations.py` but no spec's file tree declares it.
- Used in: performance-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_performance_optimizations.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_performance_optimizations.py` as an external dependency if it's not produced by this project.

**Issue F66** — Spec `pygame_ce_python_312_best_practices.md` references path `pyproject.toml` but no spec's file tree declares it.
- Used in: pygame_ce_python_312_best_practices.md
- Suggested fix: Either: (a) add `pyproject.toml` to the file tree of the spec that owns this deliverable, or (b) mark `pyproject.toml` as an external dependency if it's not produced by this project.

**Issue F67** — Spec `remediation_01_dt_text_cache.md` references path `best_practices_remediation_blueprint.md` but no spec's file tree declares it.
- Used in: remediation_01_dt_text_cache.md
- Suggested fix: Either: (a) add `best_practices_remediation_blueprint.md` to the file tree of the spec that owns this deliverable, or (b) mark `best_practices_remediation_blueprint.md` as an external dependency if it's not produced by this project.

**Issue F68** — Spec `remediation_01_dt_text_cache.md` references path `pygame_ce_python_312_best_practices.md` but no spec's file tree declares it.
- Used in: remediation_01_dt_text_cache.md
- Suggested fix: Either: (a) add `pygame_ce_python_312_best_practices.md` to the file tree of the spec that owns this deliverable, or (b) mark `pygame_ce_python_312_best_practices.md` as an external dependency if it's not produced by this project.

**Issue F69** — Spec `remediation_01_dt_text_cache.md` references path `../../tests/engine/test_dt_clamp.py` but no spec's file tree declares it.
- Used in: remediation_01_dt_text_cache.md
- Suggested fix: Either: (a) add `../../tests/engine/test_dt_clamp.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_dt_clamp.py` as an external dependency if it's not produced by this project.

**Issue F70** — Spec `remediation_01_dt_text_cache.md` references path `../../tests/ui/test_text_cache.py` but no spec's file tree declares it.
- Used in: remediation_01_dt_text_cache.md
- Suggested fix: Either: (a) add `../../tests/ui/test_text_cache.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_text_cache.py` as an external dependency if it's not produced by this project.

**Issue F71** — Spec `remediation_02_saves_assets_pyright.md` references path `best_practices_remediation_blueprint.md` but no spec's file tree declares it.
- Used in: remediation_02_saves_assets_pyright.md
- Suggested fix: Either: (a) add `best_practices_remediation_blueprint.md` to the file tree of the spec that owns this deliverable, or (b) mark `best_practices_remediation_blueprint.md` as an external dependency if it's not produced by this project.

**Issue F72** — Spec `remediation_02_saves_assets_pyright.md` references path `pygame_ce_python_312_best_practices.md` but no spec's file tree declares it.
- Used in: remediation_02_saves_assets_pyright.md
- Suggested fix: Either: (a) add `pygame_ce_python_312_best_practices.md` to the file tree of the spec that owns this deliverable, or (b) mark `pygame_ce_python_312_best_practices.md` as an external dependency if it's not produced by this project.

**Issue F73** — Spec `remediation_02_saves_assets_pyright.md` references path `asset_manager.py` but no spec's file tree declares it.
- Used in: remediation_02_saves_assets_pyright.md
- Suggested fix: Either: (a) add `asset_manager.py` to the file tree of the spec that owns this deliverable, or (b) mark `asset_manager.py` as an external dependency if it's not produced by this project.

**Issue F74** — Spec `remediation_02_saves_assets_pyright.md` references path `engine-core.md` but no spec's file tree declares it.
- Used in: remediation_02_saves_assets_pyright.md
- Suggested fix: Either: (a) add `engine-core.md` to the file tree of the spec that owns this deliverable, or (b) mark `engine-core.md` as an external dependency if it's not produced by this project.

**Issue F75** — Spec `remediation_02_saves_assets_pyright.md` references path `lighting.py` but no spec's file tree declares it.
- Used in: remediation_02_saves_assets_pyright.md
- Suggested fix: Either: (a) add `lighting.py` to the file tree of the spec that owns this deliverable, or (b) mark `lighting.py` as an external dependency if it's not produced by this project.

**Issue F76** — Spec `remediation_03_modernization.md` references path `best_practices_remediation_blueprint.md` but no spec's file tree declares it.
- Used in: remediation_03_modernization.md
- Suggested fix: Either: (a) add `best_practices_remediation_blueprint.md` to the file tree of the spec that owns this deliverable, or (b) mark `best_practices_remediation_blueprint.md` as an external dependency if it's not produced by this project.

**Issue F77** — Spec `remediation_03_modernization.md` references path `pygame_ce_python_312_best_practices.md` but no spec's file tree declares it.
- Used in: remediation_03_modernization.md
- Suggested fix: Either: (a) add `pygame_ce_python_312_best_practices.md` to the file tree of the spec that owns this deliverable, or (b) mark `pygame_ce_python_312_best_practices.md` as an external dependency if it's not produced by this project.

**Issue F78** — Spec `remediation_03_modernization.md` references path `collision_checker.py` but no spec's file tree declares it.
- Used in: remediation_03_modernization.md
- Suggested fix: Either: (a) add `collision_checker.py` to the file tree of the spec that owns this deliverable, or (b) mark `collision_checker.py` as an external dependency if it's not produced by this project.

**Issue F79** — Spec `remediation_03_modernization.md` references path `entities-system.md` but no spec's file tree declares it.
- Used in: remediation_03_modernization.md
- Suggested fix: Either: (a) add `entities-system.md` to the file tree of the spec that owns this deliverable, or (b) mark `entities-system.md` as an external dependency if it's not produced by this project.

**Issue F80** — Spec `remediation_03_modernization.md` references path `asset_manager.py` but no spec's file tree declares it.
- Used in: remediation_03_modernization.md
- Suggested fix: Either: (a) add `asset_manager.py` to the file tree of the spec that owns this deliverable, or (b) mark `asset_manager.py` as an external dependency if it's not produced by this project.

**Issue F81** — Spec `save-system.md` references path `saves/slot_1_thumb.png` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `saves/slot_1_thumb.png` to the file tree of the spec that owns this deliverable, or (b) mark `saves/slot_1_thumb.png` as an external dependency if it's not produced by this project.

**Issue F82** — Spec `save-system.md` references path `saves/` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `saves/` to the file tree of the spec that owns this deliverable, or (b) mark `saves/` as an external dependency if it's not produced by this project.

**Issue F83** — Spec `save-system.md` references path `saves/slot_X` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `saves/slot_X` to the file tree of the spec that owns this deliverable, or (b) mark `saves/slot_X` as an external dependency if it's not produced by this project.

**Issue F84** — Spec `save-system.md` references path `../../tests/engine/test_save_manager.py` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `../../tests/engine/test_save_manager.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/engine/test_save_manager.py` as an external dependency if it's not produced by this project.

**Issue F85** — Spec `save-system.md` references path `../../tests/ui/test_title_screen.py` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_title_screen.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_title_screen.py` as an external dependency if it's not produced by this project.

**Issue F86** — Spec `save-system.md` references path `../../tests/ui/test_save_menu.py` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_save_menu.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_save_menu.py` as an external dependency if it's not produced by this project.

**Issue F87** — Spec `save-system.md` references path `../../tests/ui/test_pause_screen.py` but no spec's file tree declares it.
- Used in: save-system.md
- Suggested fix: Either: (a) add `../../tests/ui/test_pause_screen.py` to the file tree of the spec that owns this deliverable, or (b) mark `../../tests/ui/test_pause_screen.py` as an external dependency if it's not produced by this project.

**Issue F88** — Spec `stair-movement.md` references path `camera-rendering.md` but no spec's file tree declares it.
- Used in: stair-movement.md
- Suggested fix: Either: (a) add `camera-rendering.md` to the file tree of the spec that owns this deliverable, or (b) mark `camera-rendering.md` as an external dependency if it's not produced by this project.

**Issue F89** — Spec `stair-movement.md` references path `game/tests/entities/test_stair_movement.py` but no spec's file tree declares it.
- Used in: stair-movement.md
- Suggested fix: Either: (a) add `game/tests/entities/test_stair_movement.py` to the file tree of the spec that owns this deliverable, or (b) mark `game/tests/entities/test_stair_movement.py` as an external dependency if it's not produced by this project.

**Issue F90** — Spec `stair-movement.md` references path `game/tests/integration/test_stairs_integration.py` but no spec's file tree declares it.
- Used in: stair-movement.md
- Suggested fix: Either: (a) add `game/tests/integration/test_stairs_integration.py` to the file tree of the spec that owns this deliverable, or (b) mark `game/tests/integration/test_stairs_integration.py` as an external dependency if it's not produced by this project.

### ✅ 10. Concept Coherence — PASS

C1 tracked: 0 concepts. C3 advisory: 6 concepts mentioned in ≥ 3 specs.
