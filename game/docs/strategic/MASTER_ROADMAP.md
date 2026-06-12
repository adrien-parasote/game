# 🗺️ Roadmap — The Heir's Awakening v0.5+

> Document Type: Strategic  
> **Evolving** — nothing is set in stone. Full vision: [game_vision.md](./game_vision.md#gameplay-loop)  
> Last Update: 2026-06-12

---

## 🎯 Vision

**Solo v1.0:** Endless Cozy RPG. Seasons, weather, friendship, familiars, and a living town.  
**Local Co-op v2.0:** 2-3 players. Shared treasury. Amplified synergies.

### Complete Synergy Loop
```
🪓 Lumberjacks + ⛏️ Miners + 🏹 Hunters
          ↓ raw resources
🔨 Crafters  → weapons, armor, furniture, ornaments
🌾 Sowers    → crops + cooked monsters → feasts
⚙️ Engineers → Guardian Mecha, automation
          ↓
💰 Commerce + 🔮 Etherists → Sphere Grid, enchantements
          ↓
🏰 Castle → town management, familiars, NPC friendship
```

---

## ✅ Phase 1 — Game Flow & Persistence `v0.5` COMPLETED

GameStateManager · Save/Load 3 slots · TitleScreen · PauseScreen · SaveMenuOverlay

---

## ✅ Phase 1.5/1.6 — Technical Refactoring & Directional Autotiles `v0.7.0` COMPLETED

### Refactoring (1.5)

Files exceeding the 400-line limit were refactored. Extracted by domain following the `Manager(game: Any)` pattern.

| File | LOC Before | LOC After | Result |
|---------|-----------|-----------|---------|
| `src/engine/game.py` | 732 | 446 | ✅ `EntityFactory` + `MapLoader` + `InputHandler` extracted |
| `src/engine/interaction.py` | 474 | 400 | ✅ `CollisionChecker` extracted |
| `src/ui/chest.py` | 421 | 343 | ✅ `chest_draw`, `chest_transfer`, `chest_layout` mixins |

### Directional & Animated Autotiles (1.6)

Replaced the binary `collidable` model with `walkable` + `direction_flags`. Integrated Tiled animated autotiles using Dynamic Batching.

| Component | Result |
|-----------|--------|
| `TileMapData` | ✅ `walkable`, `direction_flags`, `frames` |
| `TmjParser` | ✅ parses `<animation>`, `direction`, `walkable` |
| `MapManager.is_walkable()` | ✅ replaces `is_collidable` |
| `MapManager.get_direction_flags()` | ✅ directional constraints per tile |
| `MapManager.get_visible_animated_chunks()` | ✅ Dynamic Batching — static cache preserved |
| `CollisionChecker` | ✅ migrated to `is_walkable` |
| `BaseEntity.start_move()` | ✅ directional interception (cardinal priority) |
| `AnimationMapManager` (`src/map/animation.py`) | ✅ frame resolution via `pygame.time.get_ticks()` |

**Results:** 793 tests, all passing ✅ · 0 regressions  
**Specs:** [`engine-core.md`](../specs/engine-core.md) · [`map-parser-spec.md`](../specs/map-parser-spec.md) · [`npc-system.md`](../specs/npc-system.md)  
**Bug Fix (2026-05-15):** NPC stuck/spinning in debug room resolved (BUG-1: `spawn_npc` did not set `npc.game`, BUG-2: `direction` not cleared on blocked move).

---

## ✅ Phase 1.7 — Hardening & Urbanization `v0.7.0` COMPLETED

Technical and documentation integrity finalized. 100% TDD traceability.

| Component | Result |
|-----------|--------|
| `verify.py` | ✅ VERDICT: PASS (11/11 gates) |
| `spec_conformance.py` | ✅ 0 divergence (dotted Python members supported) |
| Traceability | ✅ 793 tests mapped, 100% coverage FR/REQ |
| Security | ✅ Sanitization `release.py` (0 findings) |
| Hardening | ✅ `.tdd_lock` refreshed (78 files), dead code removed |

---

## 🌿 Phase 2 — Foundations of the World `v0.7.0 → v0.7.5`

### Development Breakdown by Micro-Versions

#### 🏰 v0.7.0 — Castle Map Completion & Indoor/Outdoor Transitions
*   **Objectives:** Player completes the main layout of `01-castel.tmj` integrating interior rooms. The system implements dynamic indoor/outdoor transition management, hiding roofs/ceilings and showing building interiors when the player steps inside. Review and enhance the management of lights through interior windows, and implement the lighting system for exterior windows to illuminate correctly at night.
*   **Component Impacts:**
    *   `src/engine/map_manager.py` / `src/graphics/renderer.py`: Parse layer names (e.g., layers prefixed with `roof_`, `ceiling_`, or containing properties `is_roof=true`) and dynamically adjust their rendering alpha or visibility. Enhance management of window light effects (e.g., `18-light` type objects) for both interior window projections and exterior night-time window emissions.
    *   `src/entities/player.py` / `src/engine/collision_checker.py`: Detect player entry/exit in interior spaces (via `interior` floor tile properties or Tiled rectangular trigger zones). Smoothly transition layer alpha between `255` (fully visible) and `0` (hidden).
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Complete the layout of `01-castel.tmj`. Label layers that represent roofs/upper levels with `is_roof=true` or naming conventions, and mark interior floor tiles with custom property `interior=true` or place interior trigger zones. Add light objects/properties for window light emissions.
    *   **Graphical Assets:** None.
    *   **Audio Assets:** None.
*   **Test Cases (TDD):**
    *   `TC-TRANS-01`: Verify that stepping on an interior-designated tile triggers the indoor state.
    *   `TC-TRANS-02`: Verify that when the indoor state is active, layers marked as `is_roof` are smoothly hidden (alpha reaches `0`).
    *   `TC-TRANS-03`: Verify that exiting the interior zone restores roof visibility (alpha reaches `255`).
    *   `TC-TRANS-04`: Verify that interior window lighting renders correctly when player is indoors.
    *   `TC-TRANS-05`: Verify that exterior windows emit light correctly when the night-time cycle is active.

#### 📦 v0.7.1 — Core Stats & Gameplay Database Integration
*   **Objectives:** Load item definitions, equipment properties, and base stats dynamically from `gameplay.json`. Define character stats structure in memory.
*   **Component Impacts:**
    *   `gameplay.json`: Expand JSON schema to register items (resources, weapons, outfits, crystal) with attributes: `id`, `name`, `type`, `stats_modifier` (e.g. `{"attack": 5, "speed": -10}`).
    *   `src/config.py`: Add settings mappings to support new item types and gameplay variables.
    *   `src/entities/player.py`: Integrate dynamic stats: `attack`, `defense`, `speed` in addition to existing `hp`, `max_hp`, `gold`. Add modifiers calculation function `get_effective_stats()`.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Setup `gameplay.json` with item schemas, starting stats, inventory bounds, and crystal types.
    *   **Graphical Assets:** 5 raw item icons (`assets/images/items/00-item_iron_ore.png`, `01-item_wood.png`, `02-item_crystal.png`, `03-item_gold.png`, `04-item_ether_crystal.png`) sized 32x32px.
*   **Test Cases (TDD):**
    *   `TC-STATS-01`: Verify player initializes with correct base stats (`hp=100, attack=10, defense=5, speed=Settings.PLAYER_SPEED`).
    *   `TC-STATS-02`: Verify loading custom `gameplay.json` returns updated speed and items definitions without crash.
    *   `TC-STATS-03`: Test `player.get_effective_stats()` correctly aggregates base stats and active equipment modifiers.

#### 🕒 v0.7.2 — Extended Seasonal Time & Environmental System
*   **Objectives:** Modulate day/night cycle curves, twilight durations, and global ambient shading color profiles depending on the active season (Spring, Summer, Autumn, Winter).
*   **Component Impacts:**
    *   `src/engine/time_system.py`: Update `TimeSystem` properties. Dynamic day duration scaling:
        *   *Summer:* Longer day (14h of daylight, peak noon brightness offset).
        *   *Winter:* Longer night (10h of daylight, twilight compression).
    *   `src/engine/lighting.py` / `src/engine/game.py`: Integrate seasonal color palettes into ambient shader:
        *   *Spring:* Warm amber twilight.
        *   *Summer:* Intense golden daylight, deep blue night.
        *   *Autumn:* Rusty copper/bronze dusk overlay.
        *   *Winter:* Cold violet twilight, dense dark blue night overlay (max alpha 200).
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Seasonal settings (daylight multipliers, dusk start/end hours) added to `gameplay.json`.
    *   **Graphical Assets:** Color profiles for ambient overlay: Spring (rose/amber `#ffccd5`), Summer (bright gold `#fff2cc`), Autumn (copper/bronze `#fce5cd`), Winter (indigo/violet `#d9d2e9`).
    *   **Audio Assets:** Seasonal background ambient wind/weather loop track placeholders (e.g. `assets/audio/sfx/ambient-winter_wind.ogg`).
*   **Test Cases (TDD):**
    *   `TC-TIME-01`: Verify season transitions exactly every `Settings.DAYS_PER_SEASON`.
    *   `TC-TIME-02`: Verify ambient daylight curve reaches its peak at different times or durations in Winter vs Summer.
    *   `TC-TIME-03`: Check that maximum night overlay alpha is modulated by season (e.g., darker nights in Winter).

#### 🎨 v0.7.3 — Character Customization & Composite Sprite Layering
*   **Objectives:** Draw the player sprite dynamically by overlaying base silhouette, hair/color, and visible equipment layers, using high-performance surface caching.
*   **Component Impacts:**
    *   `src/graphics/spritesheet.py`: Introduce `CompositeSpriteLoader` to slice and combine layers onto a single Pygame Surface.
    *   `src/entities/player.py`:
        *   Replace single spritesheet loading (`01-character.png`) with dynamic composite layering.
        *   Properties: `silhouette` (base body color tint/id), `outfit_id` (current armor/clothes), `hair_id` (style/color).
        *   Generate and cache composite spritesheet whenever equipment changes. Update `self.image` using cached composite frames during animation cycles.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Dynamic trait registries (outfits, hairstyles, silhouettes) and filenames mapped in `gameplay.json`.
    *   **Graphical Assets:**
        *   Player base templates (`assets/images/characters/01-character_silhouette.png`)
        *   Hair sheets (`assets/images/characters/01-hair_style1.png`, `01-hair_style2.png`, etc.)
        *   Outfit/Armor sheets (`assets/images/characters/01-outfit_basic.png`, `01-outfit_knight.png`) sharing exact player frames layout (`32x48`px, rows=directions, cols=frames).
*   **Test Cases (TDD):**
    *   `TC-LAY-01`: Verify that modifying `player.outfit_id` triggers composite recalculation and updates active sprite textures.
    *   `TC-LAY-02`: Test that animated walk cycles are preserved across all composite layers (no offsets or cropping).
    *   `TC-LAY-03`: Verify that calling `_update_animation` uses cached frames and does not cause frame rate drops (retains constant 60 FPS).

#### 👥 v0.7.4 — Multi-Race NPCs & AI Routine Scheduler
*   **Objectives:** Populate the world with Humans, Elves, Dwarves, Beastmen, and Mechas. Implement time-based AI routines that drive NPCs to home, work, and leisure tiles.
*   **Component Impacts:**
    *   `src/entities/npc.py`:
        *   Add properties: `race` (Human, Elf, Dwarf, Beastman, Mecha), `guild` (Adventurers, Commerce, etc.), `home_tile` (spawn/sleep), `work_tile`, `leisure_spots[]`.
        *   Implement `RoutineScheduler` update checks triggered hourly or on time state changes.
        *   Time routines: `6:00` wake up, `9:00` move to work, `18:00` move to leisure spot, `23:00` sleep (de-spawn or go to bed).
    *   `src/engine/interaction.py` / `src/engine/collision_checker.py`: Ensure moving NPCs correctly recheck spatial walkability and player proximity.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Race and schedule template dictionaries in `gameplay.json`. In Tiled maps, configure NPC objects with properties `race`, `guild`, `home_tile`, `work_tile`, and `leisure_spots` coordinates.
    *   **Graphical Assets:** Spritesheets for 4 races (Human, Elf, Dwarf, Beastman) + Mecha, each in 4-direction layout (rows=directions, columns=frames) matching character sheets standard.
*   **Test Cases (TDD):**
    *   `TC-AI-01`: Verify NPC changes target position when in-game time crosses schedule thresholds (e.g., 9:00 work).
    *   `TC-AI-02`: Verify that off-screen NPCs skip pathfinding execution but restore to correct schedule position upon viewport entry.
    *   `TC-AI-03`: Check that NPC collision logic behaves correctly while NPC is transitioning between daily routine locations.

#### 🏰 v0.7.5 — Castle Hub & Garden Map Integration
*   **Objectives:** Assemble the initial playable world: Player's Bedroom, Castel Salon, and Castle Garden. Load external tilesets and BGM/ambient tracks.
*   **Component Impacts:**
    *   `assets/maps/`: Add `01-chateau_chambre.tmj` (Bedroom, respawn), `02-chateau_salon.tmj` (Great Hall), `03-jardin.tmj` (Garden).
    *   `src/engine/map_loader.py` / `src/engine/game.py`: Load maps and spawn default NPCs in their home positions.
    *   `src/engine/audio.py`: Integrate new audio files: BGM `01-jardin.ogg`, BGM `02-village.ogg`, and grass footstep sound effects.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Completed Tiled map files `01-chateau_chambre.tmj` (Bedroom), `02-chateau_salon.tmj` (Salon), `03-jardin.tmj` (Garden) with layers, collision walls, autotiles, and teleporters.
    *   **Graphical Assets:** Outdoor garden tileset sheet (`assets/images/tilesets/tileset-exterieur.png` with grass, paths, hedges, flowers, stones).
    *   **Audio Assets:**
        *   BGM: `assets/audio/bgm/01-jardin.ogg` and `assets/audio/bgm/02-village.ogg`.
        *   SFX: Grass and dirt footstep sounds (`assets/audio/sfx/04-footstep_grass.ogg`, `04-footstep_dirt.ogg`).
        *   Ambient: Garden ambient sound loop (`assets/audio/sfx/ambient-jardin.ogg`).
*   **Test Cases (TDD):**
    *   `TC-MAP-01`: Verify player correctly teleports and spawns in `01-chateau_chambre.tmj` on new game or player defeat.
    *   `TC-MAP-02`: Verify map change triggers BGM fade-out/fade-in transitions (e.g. from castle to garden).
    *   `TC-MAP-03`: Run full quality verification loop (`verify.py`) to confirm zero regressions across all 5 sub-versions.


---

## 🌧️ Phase 3 — Weather & Contextual Equipment `v0.8.0 → v0.8.3`

### Development Breakdown by Micro-Versions

#### 📦 v0.8.1 — Weather Engine & Overlay Shaders
*   **Objectives:** Implement the central weather scheduler with five states (Clear, Rain, Storm, Snow, Fog) and apply full-screen visual overlay effects.
*   **Component Impacts:**
    *   `src/engine/weather_system.py`: New `WeatherSystem` managing active state, weather transitions, and state duration based on seasonal probabilities (e.g., more snow in winter).
    *   `src/graphics/renderer.py`: Render moving particles (rain drops, snow flakes) or a full-screen alpha-pulsing surface (fog) overlaid on the viewport.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Setup seasonal weather transition probabilities in `gameplay.json`.
    *   **Graphical Assets:** Raindrop particle texture (`assets/images/particles/rain.png`), snowflake texture (`assets/images/particles/snow.png`), and procedural fog noise alpha mask.
    *   **Audio Assets:** Ambient rain loop (`assets/audio/sfx/weather-rain.ogg`), thunderclap effects (`assets/audio/sfx/weather-thunder.ogg`), and howling wind (`assets/audio/sfx/weather-wind.ogg`).
*   **Test Cases (TDD):**
    *   `TC-WEATH-01`: Verify weather state transition triggers and probability calculations.
    *   `TC-WEATH-02`: Verify particle system updates positions dynamically and loops upon reaching screen boundary.

#### 🧣 v0.8.2 — Contextual Equipment, Debuffs & Tiled Constraints
*   **Objectives:** Integrate weather-induced gameplay debuffs (speed, agricultural growth rate, vision) and negate them if the player has specific equipment items. Implement Tiled tile properties to restrict terrain access.
*   **Component Impacts:**
    *   `src/entities/player.py` / `src/engine/collision_checker.py`: Apply modifiers to speed (`-20%` in Rain, `-40%` in Storm, `-15%` in Snow). Check player active equipment slots for negation items (`umbrella` for rain, `storm_coat` for storm, `winter_coat` for snow, `ether_goggles` for fog, `snorkel` for aquatic).
    *   `src/map/manager.py`: Intercept player movement or entry onto tiles containing custom Tiled property `requires_item` (e.g. `snorkel` for underwater tiles, `winter_coat` for mountain passes).
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Register weather equipment in `gameplay.json` with attributes and debuff negation mappings.
    *   **Graphical Assets:** Composite spritesheets overlays for player walking while holding an umbrella or wearing coats.
    *   **Audio Assets:** None.
*   **Test Cases (TDD):**
    *   `TC-DEBUFF-01`: Verify player speed drops during weather states and is fully restored when holding the required equipment.
    *   `TC-DEBUFF-02`: Verify movement into a tile with `requires_item` is blocked if the player does not possess the correct item in inventory/equipment.

#### 🌲 v0.8.3 — Forest Zone Map Integration
*   **Objectives:** Assemble map `04-village.tmj` and `05-foret.tmj` with forest tilesets, forest BGMs, and custom weather-affected objects.
*   **Component Impacts:**
    *   `src/engine/map_loader.py` / `src/engine/game.py`: Load map files and trigger forest zone properties (e.g. higher storm probabilities).
    *   `src/engine/audio.py`: Integrate forest BGM and sound layers.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Map files `04-village.tmj` and `05-foret.tmj` configured with trees, clearings, and autotiles.
    *   **Graphical Assets:** Forest tileset sheet (`assets/images/tilesets/tileset-foret.png` - giant trees, hollow logs, clearing ground, roots).
    *   **Audio Assets:** BGM `03-foret.ogg` (mysterious woods), BGM `04-orage.ogg` (epic storm theme).
*   **Test Cases (TDD):**
    *   `TC-ZONE-01`: Verify zone changes correctly update BGM tracks and load correct collisions.
    *   `TC-ZONE-02`: Run complete `verify.py` loop to guarantee zero regressions.

---

## 🏗️ Phase 4 — Castle, Buildings & Guilds `v0.9.0 → v0.9.3`

### Development Breakdown by Micro-Versions

#### 🔨 v0.9.1 — Rebuilding, Guild System & Lord's Study
*   **Objectives:** Rebuild town buildings through 4 tiers. Manage construction and guild contracts from the castle's Lord's Study.
*   **Component Impacts:**
    *   `src/engine/kingdom_state.py` / `src/engine/world_state.py`: Centralize the `KingdomState` score [0-100] tracking reconstruction progress. Calculate scores based on built tiers, boss kills, and quests.
    *   `src/engine/interaction.py`: Interaction trigger in the Lord's Study (`01-castel.tmj`) displaying a Reconstruction and Guild Contract UI.
    *   `src/engine/guild_system.py`: Register 6 guilds, their rank progression (Apprentice to Grand Master), and track contract completions.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Setup guild contracts database in `gameplay.json`.
    *   **Graphical Assets:** Guild banners icons (`assets/images/ui/guild_banners.png`) and tier-level sprites for buildings (Ruined, Rebuilt, Decorated, Restored).
    *   **Audio Assets:** Building reconstruction success fanfares (`assets/audio/sfx/rebuild_success.ogg`).
*   **Test Cases (TDD):**
    *   `TC-KING-01`: Verify KingdomState score increases correctly on actions and unlocks correct castle bedroom extension bounds.
    *   `TC-KING-02`: Verify Lord's Study UI displays available reconstruction projects and available daily contracts.

#### 🪑 v0.9.2 — Furniture System, Grid Placement & Bedroom Customization
*   **Objectives:** Free placement of decorative/functional furniture on a tile-aligned grid inside customizable castle rooms.
*   **Component Impacts:**
    *   `src/entities/furniture.py`: New `Furniture` class carrying static dimensions, collider bounds, and passive buffs (e.g. +10% HP regen).
    *   `src/engine/furniture_manager.py`: Handle furniture placement mode (WASD to rotate/move, Enter to place, ESC to cancel). Enforce placement bounds and collision checks against wall colliders and other furniture.
    *   `src/engine/map_manager.py`: Extend map data to save and reload dynamically placed entities in castle save blocks.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Register furniture properties (cost, placement size, passive buffs) in `gameplay.json`.
    *   **Graphical Assets:** Spritesheets for 12 custom furniture items (beds, tables, trophy cases, crystal lanterns, runic rugs) in `assets/images/furniture/`.
    *   **Audio Assets:** Grid snapping sound effects (`assets/audio/sfx/furniture-snap.ogg`) and placement thud SFX.
*   **Test Cases (TDD):**
    *   `TC-FURN-01`: Verify furniture placement checks walkability and blocks overlaps.
    *   `TC-FURN-02`: Verify that passive furniture buffs correctly affect player stats when placed in the bedroom.

#### ⛏️ v0.9.3 — Town, Mines & Swamp Map Integration
*   **Objectives:** Load the fully populated Town and deep Mines/Swamps map, integrating village themes and mine soundscapes.
*   **Component Impacts:**
    *   `src/engine/map_loader.py`: Assemble and load maps: `06-mines.tmj` and `07-marais.tmj`.
    *   `src/engine/audio.py`: Integrate day/night dynamic BGM in the village and low echo in mines.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Tiled files `06-mines.tmj` and `07-marais.tmj` with raw mineral nodes and marsh paths.
    *   **Graphical Assets:** Tilesets `tileset-village.png` and `tileset-mines.png`.
    *   **Audio Assets:** BGM `05-village-jour.ogg`, BGM `06-village-nuit.ogg`, BGM `07-mines.ogg` (subterranean echo), and forge/carpentry environment loops.
*   **Test Cases (TDD):**
    *   `TC-TOWN-01`: Verify day/night transitions smoothly swap village day BGM to village night BGM.
    *   `TC-TOWN-02`: Run comprehensive build/lint/test gates via `verify.py`.

---

## 🌾 Phase 5 — Agriculture, Cooking & Monsters `v0.10.0 → v0.10.3` ⭐

### Development Breakdown by Micro-Versions

#### 🌽 v0.10.1 — Crop Growth & Tamed Guardian Mechas
*   **Objectives:** Plant seeds that grow through 4 distinct stages. Deploy automated Guardian Mechas to collect ripe crops and store them in custom chests.
*   **Component Impacts:**
    *   `src/entities/crop.py`: New `Crop` entity with 4 states (`seed -> sprout -> grown -> ripe`) driven by time system ticks and seasonal growth rate multipliers.
    *   `src/entities/guardian_mecha.py` / `src/entities/npc.py`: Custom AI for Guardian Mecha patrolling agricultural plots, harvesting ripe crops, navigating to `jardin_stock` chest, and depositing inventory.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Register plant growth times and season preferences in `gameplay.json`.
    *   **Graphical Assets:** Spritesheets for agricultural plants at 4 growth stages, and spritesheets for the Guardian Mecha (walking, harvesting, depositing).
    *   **Audio Assets:** Harvesting rustling SFX (`assets/audio/sfx/harvest_crop.ogg`), robotic gear hums.
*   **Test Cases (TDD):**
    *   `TC-AGRI-01`: Verify crop advances stages only when receiving time system ticks, taking seasonal modifiers into account.
    *   `TC-AGRI-02`: Verify Guardian Mecha successfully harvests ripe crops and paths correctly to `jardin_stock` chest without gettings stuck.

#### 🍳 v0.10.2 — Hunting, Harvesting & Unified Recipe Database
*   **Objectives:** Cut trees for wood, mine ore veins, and hunt wild creatures for cooking ingredients. Implement a unified recipe loading engine for both cooking and crafting.
*   **Component Impacts:**
    *   `src/entities/resource_node.py`: New `ResourceNode` class supporting wood cutting and mining interactions, spawning item drop particles upon exhaustion, and scheduling regeneration.
    *   `src/engine/crafting_manager.py`: Central recipe loading from `recipes.json`. Display crafting/cooking interface filtering recipes based on active station type (Stove, Workbench, Anvil) and tier.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Write `recipes.json` compiling ingredients and outputs for all cooking and blacksmith projects.
    *   **Graphical Assets:** 4-6 monster cooking drop items, and particle sprites for chopped wood chips and mined stone shards.
    *   **Audio Assets:** Wood chopping impact SFX (`assets/audio/sfx/chop_wood.ogg`) and pickaxe mining strikes (`assets/audio/sfx/mine_ore.ogg`).
*   **Test Cases (TDD):**
    *   `TC-CRAFT-01`: Verify resource nodes correctly deduct health, spawn drop items, and enter cooldown sleep.
    *   `TC-CRAFT-02`: Verify crafting checks player inventory, deducts correct ingredients, and adds completed item.

#### 🌊 v0.10.3 — Aquatic & Mountain Zone Maps & Seasonal Festivals
*   **Objectives:** Load the challenging Subterranean Aquatic Zone and high Mountain paths. Implement seasonal festivals with dynamic NPC gatherings and themed buff feasts.
*   **Component Impacts:**
    *   `src/engine/map_loader.py` / `src/engine/festival_manager.py`: Assemble and load maps `08-sous_eau.tmj` and `09-montagne.tmj`.
    *   `src/engine/festival_manager.py`: Schedule seasonal festivals (Sowing in Spring, Sun in Summer, Harvest in Autumn, Lights in Winter). Group NPCs in specific coordinates during festival days, and apply temporary food buffs (e.g. +HP regen 3 days).
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Map files `08-sous_eau.tmj` and `09-montagne.tmj` with underwater autotiles and mountain steep steps.
    *   **Graphical Assets:** Tilesets `tileset-aquatique.png`, `tileset-montagne.png`, and festival banners.
    *   **Audio Assets:** BGM `08-combat.ogg`, BGM `09-festival.ogg` (celebration lute), BGM `10-sous_eau.ogg`, BGM `11-montagne.ogg`.
*   **Test Cases (TDD):**
    *   `TC-FEST-01`: Verify seasonal festivals trigger on schedule, NPCs move to festival positions, and eating festival food applies correct stat buffs.
    *   `TC-FEST-02`: Run all build and code coverage checks using `verify.py`.

---

## 🐾 Phase 6 — Familiars & Friendship `v0.11.0 → v0.11.2`

### Development Breakdown by Micro-Versions

#### 🦊 v0.11.1 — Familiar Capture, Taming & Abilities
*   **Objectives:** Capture weakened wild animals, tame them in the Pets Pen by feeding them specific foods, and trigger unique abilities (item radar, castle alarm, crop acceleration).
*   **Component Impacts:**
    *   `src/entities/familiar.py`: New `Familiar` entity following the player, displaying affection emotes, and executing timed abilities (e.g. Wood Fox scanning and highlighting nearby hidden chest coordinates).
    *   `src/engine/familiar_manager.py`: Manage taming probability curves, taming item consumption, and Pets Pen storage capacity.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Setup taming food preferences and ability cooldown metrics in `gameplay.json`.
    *   **Graphical Assets:** Spritesheets for 5 familiars (Wood Fox, Mecha Pup, Mushroom Fairy, Pocket Dragon, Lantern Fish) in walk/idle/emote animations.
    *   **Audio Assets:** Unique animal sound clips for each familiar, Pets Pen BGM `12-enclos.ogg`.
*   **Test Cases (TDD):**
    *   `TC-FAM-01`: Verify taming succeeds only when matching correct feed ingredients to taming curves.
    *   `TC-FAM-02`: Verify that Mushroom Fairy familiar correctly accelerates crop growth rates when active.

#### 🤝 v0.11.2 — NPC Friendship & Companions
*   **Objectives:** Track 5 levels of NPC friendship (Stranger to Confidant) through gift-giving and quests, unlocking progressive dialogues and companion combat aid.
*   **Component Impacts:**
    *   `src/engine/friendship_manager.py`: Manage friendship levels per NPC. Register liked/disliked items database. Intercept gift-giving interactions and apply daily limits.
    *   `src/entities/npc.py` / `src/entities/player.py`: If friendship level is 5, enable "Companion Option" allowing the NPC to join player exploration, walking alongside and providing passive attribute bonuses.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Setup gifts database and liked/disliked items index in `gameplay.json`.
    *   **Graphical Assets:** Friendship heart UI icons.
    *   **Audio Assets:** Affection chime sound effects (`assets/audio/sfx/friendship_up.ogg`).
*   **Test Cases (TDD):**
    *   `TC-FRND-01`: Verify that giving a liked gift increases friendship score and displays happy emote.
    *   `TC-FRND-02`: Verify NPC joins as a companion at level 5, applying the correct passive stat bonus.

---

## 🔮 Phase 7 — Sphere Grid & Soft Combat `v0.12.0 → v0.12.2`

### Development Breakdown by Micro-Versions

#### 🌀 v0.12.1 — Sphere Grid Skill Tree & Ether Progression
*   **Objectives:** Unlock character upgrades (Harvest rate, Rebuilding cost discounts, Attack buffs) using exclusive crystallized ether currency.
*   **Component Impacts:**
    *   `src/ui/sphere_grid_ui.py`: Custom fullscreen grid interface displaying unlockable nodes. Read node connectivity and purchase states from save files.
    *   `src/engine/ether_manager.py`: Track player `crystallized_ether` totals (independent of store gold). Award ether on quests, boss defeats, crafting, and completed buildings.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Register Sphere Grid node layouts, connection vectors, and unlock costs in `gameplay.json`.
    *   **Graphical Assets:** Sphere Grid node icons and background grid sheet.
    *   **Audio Assets:** Sphere node activation chimes (`assets/audio/sfx/sphere_activate.ogg`).
*   **Test Cases (TDD):**
    *   `TC-GRID-01`: Verify purchasing a node deducts correct ether, marks it unlocked, and applies passive buffs to player stats.
    *   `TC-GRID-02`: Verify only contiguous nodes can be unlocked, blocking skips.

#### ⚔️ v0.12.2 — AI Combat Patrols & Gentle Defeat Penalty
*   **Objectives:** Enemy pathfinding for patrol, chase, and attack behaviors. Gentle defeat mechanic where the Butler carries the player back to bed with a slight gold penalty.
*   **Component Impacts:**
    *   `src/entities/enemy.py`: New `Enemy` base entity carrying patrol coordinates, sight radius checks, and pursuit pathfinding.
    *   `src/entities/player.py` / `src/engine/game.py`: Track player HP. On zero HP, trigger "Gentle Defeat" sequence: fade screen to black, deduct 10% gold (keeping inventory intact), teleport player to Castle Bedroom bed, and spawn a dialogue bubble from the Butler.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Enemy spawners in maps.
    *   **Graphical Assets:** 4 basic enemy walk/attack spritesheets.
    *   **Audio Assets:** BGM `13-boss.ogg` (epic final boss fight), combat swing SFXs, and defeat harp chords.
*   **Test Cases (TDD):**
    *   `TC-COMB-01`: Verify enemy pursues player only when entering sight radius, and returns to patrol route on escape.
    *   `TC-COMB-02`: Verify player defeat triggers 10% gold deduction, retains inventory items, and spawns player in Castle Bedroom.

---

## 💰 Phase 8 — Economy, Quests & Endless Play `v0.13.0 → v0.13.2`

### Development Breakdown by Micro-Versions

#### 🛍️ v0.13.1 — Shop UI, Currencies & Guild Ranks
*   **Objectives:** Implement a dynamic buy/sell Shop UI derived from chest layouts, offering exclusive items unlocked by active guild ranks.
*   **Component Impacts:**
    *   `src/ui/shop_ui.py` / `src/ui/chest.py`: Inherit chest rendering to display the buy/sell merchant grid. Check player gold and item stock.
    *   `src/engine/guild_system.py`: Bind shop item inventories to the player's active guild rank, locking rare blueprints and special equipment until rank achievements.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Register shop inventory catalogues and price tables in `gameplay.json`.
    *   **Graphical Assets:** Merchant shop UI headers.
    *   **Audio Assets:** Shop transaction success coins chimes (`assets/audio/sfx/shop_purchase.ogg`).
*   **Test Cases (TDD):**
    *   `TC-SHOP-01`: Verify purchasing an item deducts correct gold, adds item to inventory, and checks merchant stock limits.
    *   `TC-SHOP-02`: Verify that shop items marked with rank constraints are completely locked unless the player possesses the required guild rank.

#### 📜 v0.13.2 — Quest System & Conditional Dialogues
*   **Objectives:** Dynamic quest tracking engine (collect, cook, rebuild, taming) and conditional NPC dialogue based on time, weather, and world state variables.
*   **Component Impacts:**
    *   `src/engine/quest_manager.py`: Quest state tracking (Active, Completed). Intercept harvest, crafting, and building event triggers to update active quest objectives.
    *   `src/ui/dialogue.py`: Dynamically load NPC dialogue lines from a localized JSON database, filtering paths by checking active quest status, current season, weather, and friendship levels.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Build localized `quests.json` and NPC dialogues database.
    *   **Graphical Assets:** Quest progress HUD indicators.
    *   **Audio Assets:** Quest accepted and quest completed chime SFXs.
*   **Test Cases (TDD):**
    *   `TC-QST-01`: Verify gathering required items automatically updates quest progress and enables submission interaction.
    *   `TC-QST-02`: Verify NPC displays weather/seasonal dialogues only during matching environment states.

---

## 🤝 Phase 9 — Local Co-op `v0.13.2 → v1.0.1`

### Development Breakdown by Micro-Versions

#### 👥 v1.0.0 — Dynamic Multi-Player Controller & Shared Camera
*   **Objectives:** Add support for 2-3 players on a shared local screen. Implement a dynamic camera that zooms out to keep all players within view.
*   **Component Impacts:**
    *   `src/engine/input_handler.py`: Parse controls for multiple keyboards/gamepads, mapping unique player instances (`Player 1`, `Player 2`, `Player 3`).
    *   `src/graphics/camera.py`: Dynamic `CameraGroup` centering coordinates between all active players, adjusting camera zoom bounds dynamically to keep everyone on screen.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Setup second/third player spawn positions and controls mapping.
    *   **Graphical Assets:** Distinct body templates or color indicators for Player 2 and Player 3.
    *   **Audio Assets:** Multiplayer join/leave chime sound effects.
*   **Test Cases (TDD):**
    *   `TC-COOP-01`: Verify pressing Start on second controller successfully spawns Player 2 in the current map.
    *   `TC-COOP-02`: Verify camera scales and zooms smoothly as players move apart, clamping to map margins.

#### 🗝️ v1.0.1 — Shared Treasury & Interaction Locking
*   **Objectives:** Implement a centralized Treasury Room to pool gold and resources. Set up interaction locking to ensure only one player can converse with an NPC or open a chest at a time.
*   **Component Impacts:**
    *   `src/engine/world_state.py` / `src/engine/save_manager.py`: Pool gold and stored resources in a unified `TreasuryState` instance.
    *   `src/engine/interaction.py`: Interaction locking mechanism. The first player to interact with a chest or NPC sets an `interaction_locked` flag on the entity, preventing other players from interrupting until the dialogue or transfer completes.
*   **🎨 Assets & Configurations to Produce:**
    *   **Tiled & JSON configs:** Treasury Room layout in `01-castel.tmj` mapping chest placement.
    *   **Graphical Assets:** Lock UI indicators above occupied chests or busy NPCs.
    *   **Audio Assets:** Interaction lock rejection buzz SFX.
*   **Test Cases (TDD):**
    *   `TC-LOCK-01`: Verify Player 2 cannot interact with an NPC that is currently conversing with Player 1.
    *   `TC-LOCK-02`: Verify that spending gold in multiplayer deducts correctly from the pooled shared Treasury account.

---

## 🔗 Phase Dependencies

> Phases must be developed in the order of the following dependencies. A BUILD agent must not begin Phase N+1 until Phase N prerequisites are satisfied.

| Phase | Depends on | Reason |
|-------|-----------|--------|
| Phase 1.5/1.6 | Phase 1 ✅ | Refactoring + directional autotiles (delivered together) |
| Phase 2 | Phase 1.5/1.6 ✅ | Cleaned engine + directional walkability required before NPCs/Seasons |
| Phase 3 | Phase 2 | Extended `TimeSystem` required for WeatherSystem |
| Phase 4 | Phase 2 | KingdomState initialized by NPCs (Phase 2) |
| Phase 5 | Phase 3 | Aquatic/mountain zones require WeatherSystem |
| Phase 5 | Phase 4 | **Crafting System** depends on guild buildings |
| Phase 6 | Phase 5 | Familiars captured during hunting (Phase 5) |
| Phase 7 | Phase 4 | SphereGrid unlocked by the Library (KingdomState ≥ 50) |
| Phase 8 | Phase 6 | Quests and conditional dialogues require NPC friendship |
| Phase 9 | Phase 7 + KingdomState ≥ 75 | Co-op requires Treasury Room and complete Sphere Grid |

---

## Anti-Patterns

> **Note:** Technical implementation anti-patterns are located in their respective spec documents (e.g. `engine-core.md`, `chest-ui-spec.md`). Strategic global anti-patterns are listed below.

| # | Anti-Pattern | Strategic Violation | Correct Behavior |
|---|---|---|---|
| 1 | **Scope Creep** | Adding features not listed in the vision (e.g. online multiplayer). | Stick to local co-op (Phase 9) and the current cozy design. |
| 2 | **Phase Dissonance** | Implementing Phase N+1 elements while Phase N is incomplete. | Strictly follow the phase dependency table. |
| 3 | **Business Hardcoding** | Hardcoding game data instead of reading from `gameplay.json` or Tiled. | Item, quest, and recipe definitions must be data-driven. |
| 4 | **UI Cognitive Overload** | Creating complex custom interfaces for every subsystem. | Reuse existing UI paradigms (e.g. ShopUI derived from `ChestUI`). |
| 5 | **Blocking Endgame** | Forcing a game-over or hard ending that prevents continued exploration. | Maintain the infinite season and non-limiting evolution design. |

---

## 📐 Versions

| Version | Dev | Priority Assets |
|---|---|---|
| `0.5.x` | Phase 1-1.6 (Game Flow, Refactor, Autotiles) | — |
| `0.7.0` | Hardening & Urbanization (Traceability, 100% verify) | ✅ |
| `0.7.0` | Phase 2.0: Castle Map & Indoor/Outdoor Transitions | Completed `01-castel.tmj` map |
| `0.7.1` | Phase 2.1: Core Stats & Gameplay Database | `gameplay.json` schema ✅ |
| `0.7.2` | Phase 2.2: Extended Seasonal Time & Environmental System | Twilight shade assets |
| `0.7.3` | Phase 2.3: Character Customization & Layering | Dynamic equipment overlays |
| `0.7.4` | Phase 2.4: Multi-Race NPCs & AI Routine Scheduler | NPC sprites 4 races |
| `0.7.5` | Phase 2.5: Castle Hub & Garden Map Integration | Castle maps · outdoor tileset · garden BGMs |
| `0.8.1` | Phase 3.1: Weather Engine & Overlay Shaders | Rain/snow/fog particles |
| `0.8.2` | Phase 3.2: Contextual Equipment & Debuffs | Equipment composites sheets |
| `0.8.3` | Phase 3.3: Forest Zone Map Integration | Village & Forest maps |
| `0.9.1` | Phase 4.1: Reconstruction & Guild Lord's Study | Guild state trackers |
| `0.9.2` | Phase 4.2: Dynamic Grid Furniture System | 12 custom furniture sheets |
| `0.9.3` | Phase 4.3: Town, Mines & Swamp Maps | Mines & Swamps maps |
| `0.10.1`| Phase 5.1: Crop Growth & Automated Mechas | Crop sheets & Mecha sheets |
| `0.10.2`| Phase 5.2: Harvesting & Crafting recipes.json | Mineral nodes, wood particles |
| `0.10.3`| Phase 5.3: Aquatic & Mountain Maps, Festivals | Aquatic & Mountain maps |
| `0.11.1`| Phase 6.1: Familiar Capture & Pets Pen | 5 taming animal sheets |
| `0.11.2`| Phase 6.2: NPC Friendship & Companions | Heart UI & companion follow |
| `0.12.1`| Phase 7.1: Sphere Grid UI & Ether Nodes | Fullscreen skill tree UI |
| `0.12.2`| Phase 7.2: AI Combat Pursuit & Defeat Penalty | 4 basic enemy sheets |
| `0.13.1`| Phase 8.1: dynamic Shop UI & Guild Catalogues | Shop headers, coin sound chimes |
| `0.13.2`| Phase 8.2: Quest System & dialogues.json | Quests & dialogues databases |
| `1.0.0` | Phase 9.1: Multi-Player & Shared Camera | Spawning Players 2 & 3 |
| `1.0.1` | Phase 9.2: Centralized Treasury & Locks | Shared gold & entity lock icons |
