[CRITICAL] — Undefined Map Loading Failure State
Location: map-world-system.md / Loading
Problem: If a map chunk fails to load due to missing tileset asset, the spec does not define whether the game crashes, shows a fallback texture, or silently skips. An AI would guess, potentially leading to fatal crashes.
Fix: Add explicit fallback handling for missing map tilesets (e.g., "Render a magenta/black checkerboard tile").

[CRITICAL] — Missing Serialization Contract for Active Dialogue
Location: save-system.md / Serialization
Problem: If a player saves while in a dialogue, the spec does not define if the active dialogue node is serialized or if the player resumes in a free state. Code generated would have undefined behavior upon load.
Fix: Explicitly state: "Active dialogue state is NOT serialized. Loading a game always spawns the player in the overworld, cancelling any active dialogue."
