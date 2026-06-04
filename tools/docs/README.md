# Tooling Documentation Hub

Welcome to the **Tooling Documentation Hub**. This directory centralizes all strategic blueprints, technical specifications, architecture decisions (ADRs), and research references for the standalone developer tools and asset pipelines.

---

## 🗺️ Documentation Map

### 1. Asset Convertor (Interactive GUI & CLI)
The central procedural tileset editor allowing real-time parameter configuration, interactive tile painting, and Tiled-ready export.
* **Active Spec**: [Asset Convertor Spec](./specs/asset_convertor_spec.md)
* **Strategic Blueprint**: [Asset Convertor Blueprint](./strategic/asset_convertor_blueprint.md)
* **ADR**: [ADR-001 Dear PyGui replaces Pygame](./ADRs/adr-001-dearpygui-replaces-pygame.md)
* **Research**:
  * [Python GUI Frameworks](./research/python_gui_frameworks.md)
  * [Asset Creation Concept](./research/asset_creation_tool.md)

### 2. Autotile Converter (RPG Maker ➔ Tiled)
A compilation utility translating RPG Maker XP, MV, and MZ autotile blocks into 47-tile Wang blob tilesets.
* **Active Spec**: [Autotile Converter Spec](./specs/autotile_converter_spec.md)
* **Strategic Blueprint**: [Autotile Converter Blueprint](./strategic/autotile_converter_blueprint.md)
* **Research**:
  * [RPG Maker Autotile Formats & Tiled Blob Mapping](./research/autotile-converter.md)

### 3. Diagonal Wall Transformation
A lossless vertical shear utility automating the conversion of flat wall textures into 45-degree diagonal slopes.
* **Active Spec**: [Diagonal Wall Spec](./specs/diagonal_wall_spec.md)
* **Strategic Blueprint**: [Diagonal Wall Blueprint](./strategic/diagonal_wall_blueprint.md)
* **Research**:
  * [Geometric Shear & Slope Tiling Research](./research/diagonal_wall_transformation.md)

### 4. Simple Tiles Generator (Phase 1)
Initial procedural generator leveraging Slynyrd's matrix stamp kitbashing patterns.
* **Active Spec**: [Phase 1 Spec](./specs/phase-1-simple-tiles.md)
* **Strategic Blueprint**: [Simple Tiles Blueprint](./strategic/simple_tiles_blueprint.md)
* **Research**:
  * [Open Source Generators Study](./research/open-source-generators.md)
  * [Pixel Art Stamp Layouts](./research/pixellab-capabilities.md)

### 5. Grass Rendering Improvements
Visual upgrades to the grass procedural generator to incorporate stylized crescent shapes, wind blades, and organic clusters.
* **Active Spec**: [Grass Rendering Spec](./specs/grass_rendering_spec.md)
* **Strategic Blueprint**: [Grass Rendering Blueprint](./strategic/grass_rendering_blueprint.md)
* **Adversarial Review**: [Grass Spec Stress-Test Review](./reviews/adversarial-review-grass.md)
* **Research**:
  * [Stylized Grass Kitbashing Techniques](./research/grass_rendering_improvements.md)
  * [L-system & Sprite-AI Reference](./research/sprite-ai-capabilities.md)

### 6. Terrain Generation Core (Domain Warping)
Mathematical space distorter producing organic curves ("S-curves") on noise patterns to simulate realistic terrains.
* **Active Spec**: [Terrain Generation Core Spec](./specs/terrain_generation_core_spec.md)
* **Strategic Blueprint**: [Terrain Generation Core Blueprint](./strategic/terrain_generation_core_blueprint.md)
* **Research**:
  * [Domain Warping & Organic Noise Scattering](./research/terrain_generation_improvements.md)

### 7. Code Quality & Constants
Refactoring specifications focusing on constant centralization and French-to-English comment translations.
* **Active Spec**: [Code Quality Spec](./specs/code_quality_constants_and_translation.md)
* **Strategic Blueprint**: [Constants Extraction Blueprint](./strategic/constants_extraction_blueprint.md)
* **Research**:
  * [Code Optimization & Constants Registry](./research/code_optimization_and_constants.md)
