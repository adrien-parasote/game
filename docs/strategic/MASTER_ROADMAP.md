# 🗺️ Roadmap — The Heir's Awakening v0.5+

> Document Type: Strategic  
> **Evolving** — nothing is set in stone. Full vision: [game_vision.md](./game_vision.md#gameplay-loop)  
> Last Update: 2026-05-15

---

## 📦 Existing Assets Audit

| Category | Files | Status |
|---|---|---|
| Maps | `00-spawn.tmj`, `01-castel.tmj` | ⚠️ Needs rework |
| Maps | `99-debug_room.tmj` | ✅ Reworked and validated |
| Sprites | `01-character.png`, `02-butler.png` | ✅ |
| Interactive Sprites | doors, chests, torches, levers, emotes | ✅ |
| Tilesets | floor, walls, windows, indoor furniture | ✅ (indoor only) |
| BGM | `00-castel.ogg` | ✅ 1 track |
| SFX | door, lever, chest, emote, footstep ×2, fire | ✅ 6 effects |

**Missing:** outdoor tilesets · enemy/NPC/familiar sprites · area BGMs · weather/cooking/nature SFXs

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

## 🌿 Phase 2 — Foundations of the World `v0.7→0.8`

### Development
- **`gameplay.json`**: items (resources, ingredients, monster drops, weather equipment, furniture, `gold`, `ether_crystal`).
- **Player Stats**: `hp, max_hp, attack, defense, speed`.
- **Character Customization**: silhouette, color, outfit · equipment visible on sprite.
- **Seasons**: `TimeSystem` extended → 4 seasons · variable day/night duration.
- **Multi-race NPCs**: `race`, `guild`, `home_tile`, `work_tile`, `leisure_spots[]`.
- **NPC AI Routine**: wake up (6:00) · breakfast (8:00) · work (9:00-18:00) · tavern (18:00-21:00) · sleep (23:00).
- **Available Races**: Humans · Elves · Dwarves · Beastmen · Mecha.

### 🎨 Assets to Produce
**Maps (constructed together):**
| Map | Zone | Tilesets |
|---|---|---|
| `01-chateau_chambre.tmj` | Player's Bedroom (respawn hub) | indoor furniture ✅ |
| `02-chateau_salon.tmj` | Great hall, ruined buildings | stone walls/floor ✅ |
| `03-jardin.tmj` | Outdoor garden, agricultural plots | **outdoor-tileset** ❌ |

**Sprites:** NPCs 4 races · 4 directions · extended emotes.  
**Tilesets:** `tileset-exterieur.png` (grass, path, hedges, flowers, stone walls).  
**Audio:** BGM `01-jardin.ogg` · BGM `02-village.ogg` · grass/dirt footstep SFXs · garden ambient.

**Deliverable:** Playable castle, accessible garden, seasonal and populated world.

---

## 🌧️ Phase 3 — Weather & Contextual Equipment `v0.8→0.9`

### Development
WeatherSystem: 5 weather states + 1 special zone state (`underwater`) · buffs/debuffs · equipped items negate debuffs · `requires_item` in Tiled.

| Weather | Debuff | Negated by |
|---|---|---|
| Rain | Walking -20% · Agriculture +10% | `umbrella` |
| Storm | Walking -40% | `storm_coat` |
| Snow | Walking -15% | `winter_coat` |
| Fog | Vision -50% | `ether_goggles` |
| Aquatic Zone *(special zone)* | Slow swimming / blocked access | `snorkel` |

> **Note:** The aquatic zone is a terrain type (tileset `08-sous_eau`), not a weather condition. It shares the same `requires_item` mechanism as weather states.

`requires_item` in Tiled: `08-sous_eau` → `snorkel` · `09-montagne` → `winter_coat`.

### 🎨 Assets to Produce
**Maps:** `04-village.tmj` · `05-foret.tmj`  
**Sprites:** weather overlays (rain, snow, fog) · visible equipment (umbrella, coat)  
**Tilesets:** `tileset-foret.png` (trees, undergrowth, roots, clearing)  
**Audio:** BGM `03-foret.ogg` · BGM `04-orage.ogg` · rain/storm/snow SFXs.

**Deliverable:** Dynamic weather, contextual equipment, playable forest zone.

---

## 🏗️ Phase 4 — Castle, Buildings & Guilds `v0.9→0.10`

### Development
- **Building System**: 4 levels (ruined→rebuilt→decorated→restored).
- **FurnitureSystem**: free placement, tile-based grid, optional passive effects.
- **GuildSystem**: 6 guilds · ranks (Apprentice→Grand Master) · daily contracts.
- **Extendable Bedroom**: 4×4 → 6×6 → 8×8 → royal suite (based on KingdomState).
- **Furniture purchased exclusively from guilds** (currency: `gold`).
- **Town management managed from the Lord's Study** (castle, no town hall).

**KingdomState** — Integer score [0–100] representing reconstruction progress:

| Score | Threshold | Unlock |
|-------|-------|----------------|
| 0–9 | Ruins | Bedroom 4×4, basic chest |
| 10–24 | Foundations | Barn, Tavern, bedroom 6×6 |
| 25–49 | Reconstruction | Armory, Magic Tour, bedroom 8×8 |
| 50–74 | Restored | Great hall, Library, Treasury room |
| 75–100 | Royal Suite | Pets pen, all buildings, co-op ready |

**KingdomState score calculation (cumulative):**
| Action | Points | Limit |
|---|---|---|
| Rebuild building (lvl 2) | +5 | Per building |
| Restore building (lvl 4) | +10 | Per building |
| Major guild quest | +2 | - |
| Defeat Area Boss | +5 | Once per boss |
| Successful festival | +1 | Per festival |

> See [engine-core.md](../specs/engine-core.md#L1) for KingdomState implementation.

**Castle Rooms:**
| Room | Function | Extendable |
|---|---|---|
| Lord's Study | Town management, guild contracts | No |
| Bedroom | Respawn bed, customizable | ✅ |
| Great Hall | Feasts, indoor festivals | Based on KingdomState |
| Treasury Room | Shared stock (co-op) | Based on reconstruction |
| Library | Sphere Grid, lore, quests | Based on reconstruction |
| Pets Pen | Houses tamed animals | ✅ |

**Guilds & Buildings:**
| Guild | Buildings | Furniture Sold |
|---|---|---|
| ⚔️ Adventurers | Tavern · Armory · Training Hall | Trophies, decorative armor |
| 💰 Commerce | Trading Post · Warehouse · Covered Market | Counters, decorated chests |
| 🔮 Etherists | Magic Tower · Crystal Works · Lab | Glowing crystals, runic carpets |
| 🌾 Sowers | Barn · Greenhouse · Communal Kitchen | Planters, racks |
| 🔨 Crafters | Workshop · Forge · Tailor · Carpentry | Crafted furniture, decorative tools |
| ⚙️ Engineers | Mecha Workshop · Foundry · Depot | Decorative automates, wall gears |

### 🎨 Assets to Produce
**Maps:** `06-mines.tmj` · `07-marais.tmj`  
**Sprites:** buildings 4 visual states per guild  
**Tilesets:** `tileset-village.png` · `tileset-mines.png`  
**Audio:** BGM `05-village-jour.ogg` · BGM `06-village-nuit.ogg` · BGM `07-mines.ogg` · forge/tailoring/mechanisms SFXs.

**Deliverable:** The town is rebuilt guild by guild. The castle is customizable.

---

## 🌾 Phase 5 — Agriculture, Cooking & Monsters `v0.10→0.11` ⭐

### Development
- **Harvestable**: 4 states `seed→sprout→grown→ripe` · driven by `TimeSystem`.
- **Guardian Mecha**: simple orders → `jardin_stock` chest · extendable with Garden level.
- **Hunters**: animals in `05-foret` → meat, pelts, pet captures.
- **Lumberjacks**: fellable trees → wood · **Miners**: ore veins → stone, metal.
- **Crafting System**: unified `recipes.json` for cooking + crafting · filtered by station + building level.
- **Cookable Monsters** (Dungeon Meshi): In-game Culinary Bestiary.

| Monster | Cookable Drop | Dish Effect |
|---|---|---|
| Plant Creature | Filaments, spores | +HP regen 3 days |
| Hostile Mecha Guardian | Oil, crystal steel | +defense 2 days |
| Ice Wolf | Frost meat | +speed |
| Area Boss | Ethereal heart | Minor permanent buff |

**Seasonal Festivals:**
| Season | Festival | Trigger |
|---|---|---|
| Spring | Sowing Festival | Wild herb feast |
| Summer | Sun Festival | Ether fruit feast |
| Autumn | Harvest Festival | Monster feast |
| Winter | Festival of Lights | Hot feast (stew) |

### 🎨 Assets to Produce
**Maps:** `08-sous_eau.tmj` (snorkel required) · `09-montagne.tmj` (coat required)  
**Sprites:** 4-6 enemies (attack, damage, death) · plants 4 stages · cooking effects  
**Tilesets:** `tileset-aquatique.png` · `tileset-montagne.png`  
**Audio:** BGM `08-combat.ogg` · BGM `09-festival.ogg` · BGM `10-sous_eau.ogg` · BGM `11-montagne.ogg` · harvest/cooking/festival/combat SFXs.

**Deliverable:** Cook a monster, trigger a festival, watch the town celebrate.

---

## 🐾 Phase 6 — Familiars & Friendship `v0.11→0.12`

### Development
- **Familiar System**: taming (feeding a weakened animal) · 5 levels of friendship.
- **FriendshipSystem**: 5 levels with NPCs · gifts · progressive access.

**Familiars:**
| Familiar | Ability (lvl 4) |
|---|---|
| Wood Fox | Reveals hidden items |
| Mecha Pup | Alerts castle intrusions |
| Mushroom Fairy | Accelerates crop growth |
| Pocket Dragon | Flame 1×/day |
| Lantern Fish | Navigation in aquatic zones |

**NPC Friendship:** Stranger → Acquaintance → Friend → Close → Confidant  
Lvl 5: NPC joins adventure occasionally + minor permanent passive bonus.

### 🎨 Assets to Produce
**Sprites:** 5-8 familiers (idle, follow, ability, affection)  
**Audio:** SFX per familiar · BGM `12-enclos.ogg`

---

## 🔮 Phase 7 — Sphere Grid & Soft Combat `v0.12→0.13`

### Development
- **SphereGrid**: **Crystallized Ether** as exclusive currency for the Sphere Grid (does not replace store `gold`) · free nodes (no locked paths).
- Fully unlockable in solo · Castle Library unlocks nodes.
- One-time ether sources: quests (+3-15) · crafting (+1) · recipe (+2) · festival (+5) · boss (+10) · completed building (+5).

> [assumption: economic balance to validate in Phase 7 BUILD — average node cost and total node count not defined. Risk of overflow to calibrate via playtesting.]
- **Enemy**: Patrol→Chase→Attack · **gentle death**: Butler carries player back to bed (Penalty: loss of 10% `gold`, inventory preserved).

**Sphere Grid Structure (Free Nodes):**
```
🌱 Harvest ×1.5    🏗️ -30% Costs     🗡️ +15% Damage
🍳 Buffs 2 days    📚 +Ether ×1.2    🛡️ -20% Damage
🎉 +Festivals      🌍 +Hidden Maps   💨 +Monster Drops
🤝 Synergist*      ⚖️ +XP ×1.5       🔥 Berserker
```
*\*Synergist: solo bonus, 2× in co-op*

**Audio:** BGM `13-boss.ogg` · Sphere Grid SFX (activating crystal)

---

## 💰 Phase 8 — Economy, Quests & Endless Play `v0.13→0.14`

- **ShopUI** (derived from `ChestUI`) · guild rank → exclusive items.
- **Quests**: `collect` · `cook` · `build` · `tame` · `befriend` · `festival` · `weather_challenge` · `serve_monster_dish`.
- **Conditional Dialogue** (WorldState + season + weather + friendship).
- **No forced endgame** — infinite seasons, new NPCs, growing KingdomState.

**Audio:** Seasonal BGM variations · commerce/quest/friendship SFXs.

---

## 👥 Phase 9 — Local Co-op `v0.14→1.0`

- 2-3 players · **Shared screen** (camera zooms out, no split-screen) · shared WorldState + KingdomState + **Treasury Room**.
- **Interaction Locking**: The first player to interact with an NPC or event trigger locks the action for others until the dialogue/cutscene ends.
- Independent Sphere Grid per player · independent Familiars.
- Festival triggered by one player → bonus for all.
- Solo save compatible with new players joining.

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
| `0.6.0` | World + Seasons + NPCs + Customization | Castle maps · NPCs · outdoor tileset · garden/village BGMs |
| `0.7.0` | Weather + Contextual Equipment | Weather overlays · forest tileset · forest/storm BGMs |
| `0.8.0` | Castle + Guilds + Buildings + Furniture | Building sprites · village/mines tilesets · mines BGM |
| `0.9.0` | Agriculture + Cooking + Monsters ⭐ | Enemies · aquatic/mountain tilesets · combat/festival BGMs |
| `1.0.0` | Familiars + NPC Friendship | Familiar sprites · animal SFXs |
| `1.1.0` | Sphere Grid + Soft Combat | Boss BGM · Sphere Grid SFX |
| `1.5.0` | Economy + Quests + Endless Play | Seasonal BGMs |
| `2.0.0` | Local Co-op 👥 | — |
