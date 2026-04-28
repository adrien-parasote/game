<!-- Generated: 2026-04-28 | Files scanned: ~10 | Token estimate: ~350 -->

# Data & Config Schemas

## Configuration Files
- **settings.json**: Technical params (display, map, debug, fonts).
- **gameplay.json**: Balancing params (player/npc speed, time, locale).
- **assets/langs/{locale}.json**: Hierarchical translation strings.

## Map Structure (TMJ)
- **Layers Group**:
  - `00-layer` (Ground): depth 0
  - `01-layer` (Walls): depth 1
  - `02-layer` (Decor/Top): depth 2 (foreground)
- **Entities Object Layer**:
  - `InteractiveEntity`: class property links to `InteractiveType` enum.
  - `PickupItem`: type property links to item registry.
  - `Teleport`: destination_map, spawn_id properties.

## Item Properties
- **Type**: e.g., "ether_potion", "potion_red".
- **Category**: consumable, quest, equipment.
- **Stackable**: boolean.
- **Localization Key**: `items.{type}.name`.

## World State
- Persistence of chest states (opened/closed).
- Persistence of switches (on/off).
- Player inventory contents.
