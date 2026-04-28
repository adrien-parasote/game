# STRATEGIC BLUEPRINT - Engine Hardening & UX Polish

## 1. What exact problem are you solving?
We are addressing a set of regression bugs (missing layer), UX friction (slow emotes, dialogue-based inventory-full feedback), and architectural debt (scattered font loading, hardcoded item names, fragmented tests).

## 2. What are your success metrics?
- **Visibility**: `00-layer` is rendered correctly in all maps.
- **UX**: Inventory-full feedback is instantaneous (emote) rather than interruptive (dialogue). Emote animations are snappy (<0.7s).
- **Architecture**: Single point of truth for fonts (settings) and item metadata (lang files).
- **Reliability**: Consolidated test suite with 80%+ coverage maintained.

## 3. Why will you win?
Centralizing the font and lang systems reduces future maintenance cost. Moving to emotes for non-critical feedback improves the game's "flow" and player engagement.

## 4. What's the core architecture decision?
- **Localization Injection**: `Inventory` system will pull translations from the active lang file instead of `propertytypes.json`.
- **Font Singleton**: `Settings` will pre-load a global font to avoid redundant `SysFont` calls in every UI component.
- **Layer Mapping**: `MapManager` will explicitly track layer names to allow name-based rendering priorities.

## 5. What's the tech stack rationale?
Pygame/Python. Reusing existing JSON-based configuration and localization patterns to minimize learning curve and integration risk.

## 6. What are the MVP features?
- Fixed `00-layer` rendering.
- snappier `frustration` emote on full inventory.
- Localized item names/descriptions.
- Centralized font configuration.
- Consolidated test suite.

## 7. What are you NOT building?
- New item types or mechanics.
- New UI layouts or major redesigns.
- Advanced font features (kerning, custom shaders).
