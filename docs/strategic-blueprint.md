# Strategic Blueprint - RPG Inventory Interface

## 🎯 Strategic Thinking

### 1. What exact problem are you solving?
Implementing a premium, interactive RPG Inventory UI that provides players with a central hub to manage equipment, view stats, and browse items. It must integrate into the existing Pygame engine with pause functionality.

### 2. What are your success metrics?
- **Immersive Transition:** Pressing 'I' pauses the game and smoothly displays the UI.
- **Visual Fidelity:** High-quality rendering using the provided assets (slots, tabs, background).
- **Interactive Excellence:** Clickable tabs with visual feedback and a live character preview.
- **Information Clarity:** Clear display of stats (Level, HP, Gold).

### 3. Why will you win?
By prioritizing a "WOW" aesthetic (per user guidelines) and ensuring the UI feels "alive" with character animations and responsive interactions.

### 4. What's the core architecture decision?
A dedicated `InventoryUI` component that manages its own internal state (active tab, hovered slot) and draws directly to the screen overlay. The `Game` class will act as the orchestrator, managing the transition between PLAYING and INVENTORY states.

### 5. What's the tech stack rationale?
Pygame (existing) for low-level rendering control. Modular Python structure for maintainability.

### 6. What are the MVP features?
- Toggleable Inventory UI.
- Game pause and mouse visibility management.
- Character animation preview.
- 8 Equipment slots + 24 Item slots.
- 4-tab system with visual state.
- Player stats display.
- Item pickup system with stacking logic.
- Hover-based item tooltips in Inventory UI.

### 7. What are you NOT building?
- Item movement/dragging (deferred).
- Tab content for tabs 2-4 (empty for now).
- Persistence of inventory state beyond current session (out of scope for this task).

## 🛠 Architecture Decisions (ADRs)

### ADR 1: UI State Management
- **Decision:** The Inventory will be a modal state.
- **Rationale:** Prevents movement and game world interactions while managing items, simplifying input handling.

### ADR 2: Character Preview
- **Decision:** Render a separate instance or a reference to the Player's animation frames within the UI.
- **Rationale:** Provides a visual "paper doll" feel without needing a complex secondary scene graph.
