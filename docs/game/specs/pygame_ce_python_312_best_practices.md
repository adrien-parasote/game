# Reference Guide — Python 3.12 & Pygame-CE Best Practices [Reference]

> **Document Type:** Development Reference / State of the Art
> **Target Technologies:** Python 3.12+, Pygame-CE (Community Edition) 2.4.0+
> **Objective:** Establish coding, architecture, and optimization standards to design professional and high-performance 2D game engines.

---

## 1. Why Pygame-CE (Community Edition)?

**Pygame-CE** is the official, actively community-maintained fork of the original developers. Unlike the legacy version (`pygame` upstream), Pygame-CE brings:
* **SIMD and AVX2 Performance**: Significantly accelerated surface rendering and mathematical manipulations.
* **API Modernization**: Introduction of modern structures such as `FRect`, `fblits`, and `pygame.system`.
* **Continuous Compatibility**: Optimal support for the latest Python versions (3.11, 3.12, and future releases).

*Installation Rule: Never install both in the same virtual environment (virtualenv).*
```bash
pip uninstall pygame
pip install pygame-ce
```

---

## 2. Graphical Rendering & Pygame-CE Optimizations

Rendering in Python is often limited by CPU overhead (the "boundary crossing" between Python and SDL's C code). To maintain a stable framerate at 60 FPS or higher, you must apply these state-of-the-art techniques.

### 2.1 Massive Use of `Surface.fblits`
The classic `Surface.blit` method called in a Python `for` loop creates a CPU bottleneck due to loop interpretation on every frame.
* **The Solution**: Group your rendering operations (e.g., rendering a map's tile grid or a particle system) and call `fblits` in a single operation.

```python
# ❌ ANTI-PATTERN: Slow, blit loop in Python
for texture, position in render_queue:
    screen.blit(texture, position)

#   BEST PRACTICE: Ultra-fast batch processing (internal C-loop)
# render_queue is a list of tuples (Surface, coordinates_or_rect)
screen.fblits(render_queue)
```
> **Observed Performance Impact**: Reduction in full map rendering time from 8ms to 2ms (a 300% gain on the frame budget).

### 2.2 `FRect` (Floating-point Rectangle)
Pygame's legacy `Rect` truncated all coordinates to integers (`int`), causing micro-stuttering ("jittering") during low-speed movements or smooth camera pans.
* **The Solution**: Use `pygame.FRect` for all physical entities and the camera. It handles decimals (`float`) for physical calculations and rounds cleanly only at rendering time.

```python
import pygame

# Create a floating-point rectangle
entity_frect = pygame.FRect(10.5, 20.75, 32.0, 64.0)

# Smooth movement with delta time
entity_frect.x += velocity_x * dt

# Retrieve an FRect from a Surface
sprite_frect = surface.get_frect(topleft=(x, y))
```

### 2.3 Systematic Conversion of Pixel Formats
Never forget to convert images immediately after loading them. Otherwise, Pygame must convert the pixel format at each frame during the `blit`, which destroys performance.
* `.convert()`: For opaque images (no transparency).
* `.convert_alpha()`: For images containing transparency (per-pixel alpha).

```python
#   Best Practice: Safe and optimized loader
def load_texture(path: str, use_alpha: bool = True) -> pygame.Surface:
    raw_surf = pygame.image.load(path)
    return raw_surf.convert_alpha() if use_alpha else raw_surf.convert()
```

### 2.4 Text Rendering Caching (Font Rendering)
Text rendering with `font.render()` is one of the slowest operations in Pygame because it generates a new surface pixel by pixel on the fly.
* **Rule**: Never call `font.render` in your main drawing loop (`draw()`) for static or semi-static text. Generate them once, store them in a cache (dictionary), and draw the pre-rendered surface.

```python
class TextCache:
    def __init__(self, font: pygame.font.Font):
        self.font = font
        self._cache: dict[str, pygame.Surface] = {}

    def get_text_surface(self, text: str, color: pygame.Color) -> pygame.Surface:
        key = f"{text}_{color.r}_{color.g}_{color.b}"
        if key not in self._cache:
            self._cache[key] = self.font.render(text, True, color).convert_alpha()
        return self._cache[key]
```

### 2.5 Frustum Culling (Selective Rendering)
No need to send hundreds of tiles or entities to the graphics card if they are located off-screen.
* **Best Practice**: Calculate the intersection between the camera rectangle (`camera_frect`) and the entity/tile rectangle before adding it to the render queue.

```python
# Render only if visible on screen
if camera_frect.colliderect(entity.frect):
    render_queue.append((entity.image, entity.frect.topleft - camera_offset))
```

---

## 3. Mathematical & Pygame-CE System API Improvements

### 3.1 Vector Manipulation with `Vector2`
Pygame-CE has optimized `pygame.math.Vector2` and `Vector3` in C, making their instantiation and calculations highly performant.
* **`Vector2.move_towards(target, distance)`**: Calculates movement toward a target without ever overshooting it (prevents oscillations and manual trigonometry coding).

```python
pos = pygame.Vector2(10, 10)
target = pygame.Vector2(100, 100)
speed = 4.5 * dt

# Direct and safe movement without overshoot (in-place)
pos.move_towards_ip(target, speed)
```

### 3.2 Accessing System Paths with `pygame.system`
Managing save paths manually based on the OS (Windows, macOS, Linux) is a source of errors and permission violations. Pygame-CE integrates a robust system module.

```python
import pygame.system

# Retrieve a guaranteed and safe directory to write save files
# Windows: C:\Users\Name\AppData\Roaming\MyCompany\MyGame
# macOS  : /Users/Name/Library/Application Support/MyCompany/MyGame
save_dir = pygame.system.get_pref_path(org="MyCompany", app="MyGame")

# Get user OS language preferences
user_locales = pygame.system.get_pref_locales()
# Returns for example: [{'language': 'en', 'country': 'US'}]
```

---

## 4. Integration of Modern Python 3.12 Features

Python 3.12 introduces major features that simplify game code and drastically improve static typing (validated by `pyright`).

### 4.1 Simplified Generic Syntax (PEP 695)
No need to import `TypeVar` or `Generic` to define generic classes or functions anymore. The syntax is now directly integrated into the signature.

```python
#   BEST PRACTICE: Generic entity manager in Python 3.12
class EntityManager[T]:
    def __init__(self):
        self._entities: list[T] = []

    def register(self, entity: T) -> None:
        self._entities.append(entity)

    def get_all(self) -> list[T]:
        return self._entities
```

### 4.2 Explicit Type Alias Declaration (`type`)
Makes complex type signatures much more readable by avoiding verbose type assignments.

```python
import pygame

# Declare clear and reusable type aliases
type Coordinate = tuple[float, float] | pygame.Vector2
type RenderItem = tuple[pygame.Surface, pygame.FRect | Coordinate]

def queue_render(item: RenderItem) -> None:
    ...
```

### 4.3 Explicit Override Decorator (`@override`)
Secures polymorphism (very common in game entity or UI architectures). The `@override` decorator from the `typing` library allows tools like `pyright` to raise an error immediately if the parent class method signature or name changes.

```python
from typing import override
import pygame

class BaseEntity(pygame.sprite.Sprite):
    def update(self, dt: float) -> None:
        pass

class Player(BaseEntity):
    @override
    def update(self, dt: float) -> None:
        # If the parent method "update" were renamed, Pyright would raise an error here.
        self.move_player(dt)
```

### 4.4 Precise Configuration Typing with `Unpack` and `TypedDict`
Ideal for passing complex entity creation configurations or parameters without losing autocompletion and static type safety.

```python
from typing import TypedDict, Unpack

class EntityConfig(TypedDict):
    speed: float
    health: int
    name: str
    can_teleport: bool

#   Usage: kwargs is now fully typed and statically validated!
def spawn_entity(x: float, y: float, **kwargs: Unpack[EntityConfig]) -> None:
    speed = kwargs.get("speed", 100.0)
    name = kwargs.get("name", "NPC")
```

### 4.5 Powerful F-Strings
F-strings in Python 3.12 no longer have quote limitations and allow nesting, newlines, and comments directly inside the expressions.
* **The `=` Specifier**: Indispensable for quick debugging logs.

```python
pos = pygame.Vector2(45.2, 89.1)
# Prints directly: pos=Vector2(45.2, 89.1)
print(f"{pos=}") 

# Complex F-string allowed in 3.12 (multi-line and nested expressions)
debug_info = f"Entity: {
    'Active' if entity.is_alive 
    else 'Dead' # Comments are allowed here!
}"
```

---

## 5. State-of-the-Art Game Architecture

To prevent video game code from becoming an unreadable "spaghetti bowl" after a few weeks, structure your codebase according to these rigorous principles.

```
src/
├── main.py                           # Single entry point
├── config.py                         # Global parameters (persistent Settings class)
├── engine/
│   ├── game.py                       # Main loop (Init, Events, Update, Draw)
│   ├── audio.py                      # Sound and music manager
│   └── state.py                      # State machine (Menu, Game, Inventory...)
├── entities/
│   ├── base.py                       # BaseEntity abstract class
│   ├── player.py                     # Player class (inherits from BaseEntity)
│   └── groups.py                     # Custom sprite groups (Y-Sorted)
├── map/
│   ├── manager.py                    # Map loading and transitions
│   └── tmj_parser.py                 # Tiled JSON parser (TMX optimized for JSON)
└── ui/
    ├── manager.py                    # UI and window manager
    └── components.py                 # Buttons, dialog boxes, inventory grids
```

### 5.1 Strict Separation of Physics and Rendering
* Physics calculations happen in `update(dt)`.
* Drawing happens in `draw(screen)`.
* **No physical calculations or movements should ever be coded inside the drawing method.**

### 5.2 Y-Sorted Rendering (2.5D Depth of Field)
For a 2.5D RPG, entities must be drawn according to their Y-coordinate (`centery` or `bottom`). Objects lower on the screen are drawn *on top of* objects higher on the screen.
* **Best Practice**: Inherit from `pygame.sprite.Group` and override the drawing method.

```python
class YSortedCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.offset = pygame.Vector2()

    def custom_draw(self, camera_frect: pygame.FRect):
        # 1. Calculate camera offset
        self.offset.x = camera_frect.x
        self.offset.y = camera_frect.y

        # 2. Sort entities by their bottom Y-coordinate (bottom)
        # 3. Build render_queue for fblits
        render_queue = []
        sorted_sprites = sorted(self.sprites(), key=lambda sprite: sprite.frect.bottom)
        
        for sprite in sorted_sprites:
            # Frustum Culling
            if camera_frect.colliderect(sprite.frect):
                render_pos = sprite.frect.topleft - self.offset
                render_queue.append((sprite.image, render_pos))

        # 4. Perform ultra-fast batch rendering
        self.display_surface.fblits(render_queue)
```

### 5.3 Delta Time Stabilization (FPS Independence)
Physical calculations must be multiplied by the time elapsed since the last frame (`dt` expressed in seconds).
* **Watch out for the trap**: If the game freezes for 2 seconds (e.g., during level loading or a breakpoint in the debugger), `dt` spikes, which can project the player through walls on the next frame.
* **Solution**: Rigidly clamp the maximum value of the time step (`dt_clamp`).

```python
class Game:
    def __init__(self):
        self.clock = pygame.Clock()
        self.target_fps = 60

    def run(self) -> None:
        while self.running:
            # dt in seconds (e.g. 1/60 = 0.016s)
            raw_dt = self.clock.tick(self.target_fps) / 1000.0
            
            # Anti-teleportation safety: limit dt to equivalent of 10 FPS min (0.1s max)
            dt = min(raw_dt, 0.1)
            
            self.handle_events()
            self.update(dt)
            self.draw()
```

---

## 6. Absolute Anti-Patterns to Ban (DO NOT)

| Forbidden Practice ❌ | Technical Consequence | Recommended Practice ✅ |
| :--- | :--- | :--- |
| Instantiating objects (`Vector2`, `FRect`, `Surface`) in the main loop | Garbage Collector explosion, causing regular framerate micro-stutters. | Instantiate once in the constructor (`__init__`) and modify existing properties (e.g., using `move_towards_ip`). |
| Rendering text or loading fonts at each frame | Dramatic FPS drop (< 15 FPS) because font texture generation is extremely heavy for the CPU. | Load fonts once and pre-calculate/cache text surfaces. |
| Using `pygame.display.flip()` if only a small part of the screen changes | Unnecessary data transfer to the screen. | Use `pygame.display.update(rect_list)` to limit the update to moving areas (Dirty Rects). |
| Using raw paths with hardcoded slashes (`/` or `\`) | Instant crash when porting the game from one OS to another (e.g., from macOS to Windows). | Always build paths using `os.path.join` or `pathlib.Path`. |
| Omitting `.convert()` or `.convert_alpha()` on a surface | Loss of 200% to 300% in image display speed (CPU forced to decode bits at each frame). | Apply conversion as soon as the graphic asset is loaded. |
| Omitting Delta Time (`dt`) clamping | Glitching through walls, major physical collision bugs during sudden framerate drops or debug pauses. | Rigidly clamp the maximum value of `dt`. |

---

## 7. Recommended Quality Configuration

To guarantee that these high standards are maintained, configure your static analysis tools with these settings:

### Pyright Configuration (`pyrightconfig.json`)
```json
{
  "include": ["src"],
  "exclude": ["**/__pycache__", "venv"],
  "pythonVersion": "3.12",
  "pythonPlatform": "All",
  "typeCheckingMode": "strict",
  "useLibraryCodeForTypes": true,
  "reportMissingTypeStubs": false
}
```

### Ruff Configuration (`pyproject.toml`)
```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # Pyflakes (bug detection)
    "B",   # Bugbear (anti-patterns)
    "I",   # Isort (import organization)
    "UP",  # Upgrade (modernization to Python 3.12)
    "T20"  # Ban rogue prints (favor logging)
]
```
