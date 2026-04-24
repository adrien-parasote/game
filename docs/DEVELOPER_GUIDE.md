# Developer & AI Prompting Guide

This document serves as the primary handoff for future developers and AI agents. It defines how to interact with this engine to ensure stability and velocity.

## 1. The Handoff Context (MUST READ)

When starting a new task, always load the following context in order:
1.  **Strategic**: `docs/specs/ENGINE_CORE.md` (The "Bible")
2.  **Implementation**: `docs/specs/INTERACTIVE_OBJECTS.md` or `NPC_SYSTEM.md`
3.  **Global Rules**: `.agent/rules/coding-standards.md`
4.  **Local State**: `src/config.py` (For current thresholds)

## 2. Prompting Strategy

To get the best code generation, follow this prompting pattern:

### A. The Spec Gate
Never implement without a spec. Ask: *"Based on ENGINE_CORE.md, can you draft a spec for [Feature X] including Anti-patterns and Test Cases?"*

### B. The TDD Cycle
Before implementation: *"Write the RED tests in `tests/test_new_feature.py` using the mocks defined in the Developer Guide."*

### C. Implementation
Once tests are RED: *"Implement the feature to satisfy the tests, ensuring zero duplication with InteractionManager."*

## 3. Mocking Standards

The engine has complex environmental dependencies (Pygame display, Audio, Assets). Use these mocking patterns to avoid test regressions:

### SpriteSheet Mocking
**Anti-Pattern**: Patching `__init__` to return None.
**Correct Pattern**:
```python
@pytest.fixture
def mock_spritesheet():
    with patch('src.graphics.spritesheet.SpriteSheet') as MockSheet:
        instance = MockSheet.return_value
        instance.valid = True
        instance.sheet = pygame.Surface((128, 128))
        instance.load_grid_by_size.return_value = [pygame.Surface((32, 32))] * 16
        yield MockSheet
```

### Game Engine Mocking
Avoid starting the full `Game.run()` loop in tests. Mock `_load_map` and `hud` translation data.
```python
def test_feature():
    with patch('src.engine.game.Game._load_map'):
        game = Game()
        game.hud._lang = {"dialogues": {"map-id": "text"}}
        # Test logic here
```

## 4. Directory Map

| Path | Purpose |
|------|---------|
| `src/engine/` | Core coordination (Game, Time, Audio, Interaction) |
| `src/entities/` | All sprite-based objects (Base, Player, NPC, Interactive) |
| `src/map/` | Data parsing and tile management |
| `src/ui/` | HUD and Dialogue rendering |
| `assets/` | Shared Tiled project, images, and audio |
| `tests/` | Consolidated test suites (Keep these unified!) |

## 5. Architectural Non-Negotiables

1.  **No Physics in Game**: All spatial triggers MUST live in `InteractionManager`.
2.  **Zero hardcoded thresholds**: All pixel distances, speeds, and alphas must come from `Settings`.
3.  **Y-Sorting is Mandatory**: All rendered entities must support `rect.bottom` sorting.
4.  **Error-Safe Rendering**: All `draw()` methods must be wrapped in safety checks for `None` surfaces (to support headless tests).

## 6. How to build a new Interactive Object

1.  Add the `sub_type` to `INTERACTIVE_OBJECTS.md`.
2.  Define the animation frames in `src/entities/interactive.py`.
3.  Add any custom logic to `InteractionManager` if it requires new spatial rules.

## 7. How to trigger Player Emotes

1.  **Manual Trigger**: Call `player.playerEmote('name')`.
    - Supported names: `love`, `bored`, `interact`, `question`.
2.  **Logic Integration**: Emotes are typically triggered from `InteractionManager`.
    - Proximity-based triggers should be added to `_check_proximity_emotes()`.
    - Input-based triggers (feedback) should be added to `handle_interactions()`.
3.  **Rendering**: Emotes are drawn in `Game._draw_scene()` after the HUD pass to ensure they stay on top of all world and UI elements.
