# STRATEGY: Autotile Conversion Pipeline

## 1. What exact problem are you solving?
Help level designers convert legacy RPG Maker XP autotiles (96x128px) into Tiled Wang Edge tilesets (16 tiles, 512x32px strip) seamlessly so they can paint terrains automatically in Tiled without manual asset slicing.

## 2. What are your success metrics?
- 100% conversion success rate of standard 96x128px autotiles.
- 0 manual configuration steps required in Tiled after TSX generation.
- Correct Wang ID Edge masking, enabling seamless Tiled Terrain brush painting.

## 3. Why will you win?
By writing a direct asset pipeline script, we preserve the large library of existing RPG Maker assets, enabling the use of modern Tiled tools without requiring artists to redraw or manually slice thousands of tiles.

## 4. What's the core architecture decision?
A standalone Python script using Pillow for image manipulation and standard `xml.etree.ElementTree` for TSX generation. 

## 5. What's the tech stack rationale?
Python + Pillow: Excellent, ubiquitous image processing stack that runs cross-platform and integrates easily into standard CI/CD asset pipelines.

## 6. What are the features?
- **F1:** PNG tile strip generation (parsing 96x128px autotiles into 16 variants of 32x32px).
- **F2:** TSX file generation with accurate `type="edge"` Wang IDs pointing to the PNG strip.
- **F3:** CLI interface for single-file and potential batch processing.

## 7. What are you NOT building?
- Support for the 47-tile Mixed Wang set (Blob pattern).
- Support for animated autotiles (384x128px).
- A graphical user interface (GUI).
