# Strategy: Kitbashing / Stamp Scattering

This document defines the new texture generation architecture, moving from a purely mathematical model (abstract noise) to an assembly model of semantic elements (Kitbashing), while strictly preserving color palette constraints and seamless tiling.

## The Core Concept

The algorithm programmatically draws small "stamps" in memory (using `PIL.ImageDraw` to simulate brushstrokes) with 3 gray levels (Shadow, Midtone, Highlight). Then, it intelligently scatters these stamps on a 32x32 canvas to create a continuous and semantically rich texture, without ever requiring external PNG files or AI.

## Architecture Consequences (Impact Scan)

1. **Replacing "Noise" with "Procedural Stamps"**
   - The algorithm generates vector shapes (grass blades, small rocks) in grayscale directly in memory.
   - The `Density` slider controls how many stamps are applied to the image.
   - No more need to provide external PNG files!

2. **Guaranteed *Seamless* Tiling**
   - When the algorithm "places" a grass blade at coordinates (30, 15), knowing the image is 32x32, the blade will overflow on the right.
   - The algorithm will mathematically wrap the overflow and redraw it at coordinates (0, 15) on the left edge (and also handles top/bottom). Perfect tiling is thus 100% guaranteed.

3. **Strict Color Management (Quantization / Palette) Inspired by TofuPixel**
   - To retain the tool's utility and respect a 4-color palette (e.g. GameBoy), the provided *stamps* will be drawn in 3 specific gray levels (+ transparent background).
   - The background of the 32x32 canvas will be filled with Color 0 (the darkest: the ground / deep shadows).
   - The Dark Gray of the stamp (e.g., RGB 85,85,85) will be mapped to Color 1 (the grass blade shadow).
   - The Mid Gray of the stamp (e.g., RGB 170,170,170) will be mapped to Color 2 (the base tone of the grass blade).
   - The White of the stamp (RGB 255,255,255) will be mapped to Color 3 (the highlight on the grass blade).
   - Thus, the grass will look like professional grass (shadow, base, highlight), but adapt instantly to any retro palette selected in the UI.

## 7 Strategic Questions

| Question | Answer for this feature |
|---|---|
| **1. Who is the user?** | The solo developer who wants a semantic texture (grass, stone) with a beautiful artistic structure (inspired by TofuPixel tutorials) without drawing every pixel or depending on AI. |
| **2. What problem does it solve?** | Abstract mathematical noise lacks semantics. AI is unstable and expensive. External stamps require manual work. Procedural stamps solve everything. |
| **3. What are the constraints?** | Must remain 100% offline, AI-free, fast, generate shapes in memory (PIL.ImageDraw), respect the palette, and be seamless. |
| **4. What does success look like?** | The grass visually looks like stylized grass while being mathematically "seamless" without manual intervention or external images. |
| **5. What exists already?** | The Live Preview engine, the .tsx export system, the palette management. The generator.py will be rewritten to draw and distribute shapes in memory. |
| **6. What is the smallest slice?** | 1. Stamp generator (grass) in PIL. 2. Placement algorithm with 2D wrapping. 3. Quantization by direct replacement of the 3 gray levels. |
| **7. What are the metrics?** | Generation time < 0.2s for Live Preview. 100% palette compliance. |
