# Adversarial Review Results

Reviewer source: `self` (Round 0)

## Epistemic Pre-Scan
- **Cross-Doc Consistency**: PASS.
- **Externally Verifiable Claims**: PASS (None).
- **Hidden Assumptions**: PASS. All assumptions handled.
- **POC Gate**: PASS. No external APIs involved.

## Findings

**[CRITICAL] — `_apply_grass_wading` missing depth filter**
Location: §4.6
Problem: The anti-pattern explicitly states to skip wading for sprites with `depth < player.depth`. However, the algorithm in §4.6 loops through all sorted sprites without filtering them by depth. Background entities (Pass 2) will incorrectly receive grass wading.
Fix: Add `if getattr(sprite, "depth", 1) < self.game.player.depth: continue` inside the sprite loop in `_apply_grass_wading()`.

**[HIGH] — Global `walk_active` disables effects for all NPCs**
Location: §4.3.3 and §4.6
Problem: The `walk_active` guard is applied globally in `draw_scene()`. If `walk_active` is True, `_apply_partial_occlusion` and `_apply_grass_wading` are completely skipped. This means that while the player is in a scripted walk, all other NPCs will suddenly lose their occlusion and grass wading effects.
Fix: Remove the global `walk_active` guard from `draw_scene()`. Instead, pass `walk_active` into both methods (or evaluate it inside) and skip only the player sprite: `if walk_active and sprite == self.game.player: continue`.

