# Sprite-AI Platform Capabilities Research

## Overview
Sprite-AI (https://www.sprite-ai.art) is an AI-powered SaaS platform for game developers to generate, edit, and organize pixel art assets. The system uses a "hybrid" workflow where AI generation creates base assets, followed by manual refinement using in-browser tools.

## Key Features & Tools

### 1. Studio (AI Generator)
- Uses prompt-based generation specifically tuned for pixel art.
- Allows constraining generations to specific color palettes (by name, mood, count, or specific colors).
- Can apply styles (e.g., retro, horror, cozy, RPG).
- Supports seamless tile generation workflows.

### 2. Built-in Editor Tools
- **Pixel Editor**: Browser-based tool to manually clean up AI-generated sprites.
- **Palette Generator / Transfer Tool**: Automatically applies chosen palettes (like PICO-8, Endesga 32, Sweetie 16) across existing sprites, providing a cleaner alternative to manual recoloring.
- **Tile Editor**: A tool specifically for refining and testing seamless tiles.
- **Background Removal**: Specialized for cleaning up sprite sheets and isolated elements.

### 3. Palettes & Aesthetic Systems
The platform highly emphasizes color constraint as the defining characteristic of good pixel art. Key palettes promoted include:
- **PICO-8 (16 colors)**: Best for retro platformers and jams. Highly vibrant.
- **Endesga 32 (32 colors)**: Best for fantasy RPGs, excellent warm tones.
- **GameBoy (4 colors)**: Authentic nostalgic limitations.
- **Sweetie 16 (16 colors)**: Softer and friendlier alternative to PICO-8.
- **Zughy 32 (32 colors)**: Dark, moody, perfect for horror games.
- **Apollo (16 colors)**: Ideal for sci-fi, with strong blue/cyan ranges.

### 4. Seamless Tiles
Guides explain how to use the generator to create tiling textures (like grass, dirt, factory floors) that seamlessly wrap. Examples include "topdown view grass tile with flowers" and "grass texture in factory style".

## Decision: Adopt, Adapt, or Build-New?
The user wants to build an asset convertor that achieves similar results. Since the user explicitly stated "le tool asset_convertor ne me va pas" and found Sprite-AI as an inspiration for the *final render*, we need to **Adapt** our approach to incorporate:
1. **Strict Palette Constraints**: Pre-defined limited palettes during or immediately after generation.
2. **Hybrid Workflow Integration**: Ensure the user can easily prompt for a base and then edit/tile it.
3. **Seamless Tiling Support**: Prompting strategies or post-processing for tiling textures.
