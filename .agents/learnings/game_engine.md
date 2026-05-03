## 🎮 Game Engine

### L-GAME-001 · 2026-04-28 · U · Perfect
**Footprint-based interaction center**

Decouple the visual sprite position (`midbottom` alignment) from the logical interaction center (footprint center). Supports varied asset sizes and tall sprites without breaking grid-consistent interaction math.

---

### A-EVENT-002 · 2026-05-03 · P · Minor Rework
**`pygame.event.post()` re-queues events handled by the orchestrator**

`GameStateManager._handle_playing()` re-posts filtered events via `pygame.event.post()` so `Game._handle_events()` can consume them. If BOTH layers handle the same key (e.g., `TOGGLE_FULLSCREEN_KEY`), the key triggers twice per press — double-toggling fullscreen.

```python
# ❌ Orchestrator handles K_p AND re-posts it to Game which also handles K_p
filtered = [e for e in events if not (e.type == KEYDOWN and e.key == K_ESCAPE)]
for event in filtered:
    pygame.event.post(event)  # K_p survives the filter
# Then Game._handle_events() sees K_p and calls toggle_fullscreen() again

# ✅ Remove the duplicate handler from Game._handle_events()
# The orchestrator (_process_global_events) owns all cross-state keys.
# Game._handle_events() only handles gameplay-local keys (interact, inventory...).
```

**Règle :** Keys handled in the orchestrator's `_process_global_events()` MUST be removed from `Game._handle_events()`. If `pygame.event.post()` is used, the inner game handler is a secondary consumer — it will see every non-filtered event.

**Evidence:** `K_p` toggled fullscreen twice per press. Fixed by removing handler from `Game._handle_events()`. commit `ca94c9c`.

---

### L-ARCH-001 · 2026-04-28 · U · Perfect
**Composite keys for cross-map resource scoping**

Use `{map_base_name}-{element_id}` as keys in WorldState and DialogueManager. Prevents ID collisions across maps (e.g., two maps both with a `chest_01` object).

---

### A-GAME-001 · 2026-04-28 · U · Minor Rework
**Unthrottled spatial polling**

Proximity checks that trigger visual/audio side-effects every frame without a cooldown cause effect stacking and sprite duplication.

✅ Always gate proximity effects with `_emote_cooldown` (or equivalent) before triggering.

---

### A-GAME-002 · 2026-04-28 · U · Minor Rework
**Tile vs pixel coordinate mixups**

Passing pixel coords to functions expecting tile indices (or vice-versa) causes silent out-of-bounds errors (`is_collidable(128, 0)` → wrong tile).

✅ Name all coordinate parameters explicitly (`tile_x`, `pixel_x`) and convert at the boundary.

---

### L-ARCH-002 · 2026-04-30 · U · Major Rework
**Spec must define close sequence, not just close trigger**

Specifying WHEN to close an entity without specifying WHAT the close sequence is generates bugs for each missing step.

| Step | Action | Method |
|------|--------|--------|
| 1 | Toggle entity state | `entity.interact(player)` |
| 2 | Play SFX | `audio_manager.play_sfx(entity.sfx)` |
| 3 | Persist state | `world_state.set(key, {...})` |
| 4 | Close UI | `ui.close()` |
| 5 | Suppress follow-up feedback | reset proximity target + cooldown |

✅ Centralize all steps in `_close_X()`, called from **every** close path (zone exit, action key, etc.).
**Evidence:** 5 separate bugs in ChestUI auto-close. commit `6c7f811`.

---

### L-ARCH-003 · 2026-04-30 · U · Major Rework
**Frame-invariant checks belong in `update()`, not in conditional sub-functions**

A check placed inside a conditional branch only runs when that branch fires. If the check must fire every frame, it must live directly in `update()`.

```python
# ❌ _check_chest_auto_close() only runs when NO entity in proximity range
def _check_proximity_emotes(self):
    ...
    if nothing_in_range:
        self._check_chest_auto_close()  # missed when player is near other entity

# ✅ always-running checks go directly in update()
def update(self, dt):
    self._check_proximity_emotes()  # conditional
    self._check_chest_auto_close()  # always — regardless of proximity state
```

✅ **Spec rule:** State explicitly "Checked every update tick" or "Checked conditionally on [X]" to prevent ambiguous call-site choices.

---

### A-ARCH-003 · 2026-05-01 · U · Minor Rework
**Rendering loop disconnected from dynamic properties**

When an object's state (e.g., `is_on`) transitions from an event-driven boolean to a dynamically computed property (e.g., based on `TimeSystem.brightness`), the rendering state (e.g., sprite index) must be actively synchronized in the `update()` loop.

```python
# ❌ Rendering sprite column only updates on explicit interaction
def interact(self):
    self.is_on = not self.is_on
    self._update_col_index()  # OK for manual, but misses auto-toggles

# ✅ Polling dynamic state in the update loop
def update(self, dt):
    if getattr(self, 'day_night_driven', False):
        self._update_col_index()  # Sync visual state with computed property
```

**Rule:** When replacing static state variables with dynamically computed properties, ensure the `update()` loop polls and synchronizes any visual or layout properties that depend on them.
**Evidence:** Day/night torches computed `is_on=False` correctly at dawn, but rendered the "ON" sprite because `col_index` was only updated during `interact()`.

---

