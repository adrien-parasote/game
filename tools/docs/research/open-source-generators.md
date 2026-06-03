# Open Source Pixel Art & Tile Generators

## Key GitHub Repositories & Tools

### 1. Dedicated AI Pixel Art Generators
- **Pixel-Forge**: A node-based AI game asset generator. It includes specific pipelines for tileable textures using Flux/LoRA models, aiming to generate seamless pixel-art tiles and 2D sprites. This is very close to our target workflow.
- **Retro Diffusion Plugin (Unity)**: A Unity plugin that generates pixel art and tileable textures directly in the engine using a custom API. It proves the viability of generating assets directly where they are used.

### 2. Stable Diffusion Extensions & Workflows
- **[sd-pixel](https://github.com/Leodotpy/sd-pixel)**: An extension for AUTOMATIC1111 (Stable Diffusion WebUI). It focuses on post-processing: taking high-res or messy AI output and downscaling it, fixing asymmetrical pixels, and applying strict color palettes. 
- **[ComfyUI-PixelArt-Detector](https://github.com/dimtoneff/ComfyUI-PixelArt-Detector)**: Custom nodes for ComfyUI designed for downscaling, color palette swapping, and restoring pixel art using SDXL.
- **Stable Diffusion Tiling**: Both AUTOMATIC1111 and Forge UI have a native "Tiling" checkbox that forces the AI to match the edges of the generated image, making it naturally seamless.

### 3. Procedural & Autotiling Tools
- **[2dtiler](https://github.com/2dtiler/app)**: An alternative to tools like Tiled, incorporating AI for level design and tileset management.
- **[CelesteWFC](https://github.com/aczw/CelesteWFC)**: Implements the Wave Function Collapse algorithm. While not a generator of the art itself, it shows how to procedurally assemble tiles once they are generated.
- **[PixelRefiner](https://github.com/HappyOnigiri/PixelRefiner)**: A utility to clean up AI-generated pixel art (removes anti-aliasing, detects grids, optimizes transparency).

## Lessons for Our Objective
Most open-source solutions rely on a two-step process:
1. **Generation (Base)**: Using Stable Diffusion with a "Tiling" feature or a specific LoRA fine-tuned for pixel art.
2. **Post-Processing (Quantization)**: A crucial step that takes the "soft" AI image, snaps it to a strict grid, and forces the colors into a limited palette (like PICO-8 or Endesga 32).

For autotiles (like RPG Maker style 47-tile sets), no single open-source AI tool does this perfectly out of the box yet. It usually requires generating a base seamless texture and then using a script or algorithm to carve it into edge tiles, corner tiles, etc.
