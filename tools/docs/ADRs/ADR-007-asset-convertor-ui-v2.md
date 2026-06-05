# ADR-007: Asset Convertor UI v2 — Architecture Decisions

> **Date:** 2026-06-05
> **Status:** ACCEPTED
> **Context:** Refactoring `asset_convertor` GUI to support A3/A4 converters + Recolor mode.

## Decisions

### ADR-007-1: Dual-Toolbar Layout
**Decision:** Primary toolbar (type selector) + contextual secondary toolbar (mode-specific options).
**Rejected:** Left sidebar (reduces preview width), extended single toolbar (unscalable).

### ADR-007-2: Mode-First Navigation
**Decision:** Resource type (A1/A2/A3/A4/Recolor) is the primary axis. Format (MV/MZ/XP) is secondary and contextual.
**Rationale:** User selects what they're converting before they select how to convert it.

### ADR-007-3: Autotile Tables from Official Corescript
**Decision:** Implement A3/A4 conversion using `WALL_AUTOTILE_TABLE` (16 shapes) and `FLOOR_AUTOTILE_TABLE` (47 shapes) exactly as defined in `rpgtkoolmv/corescript` blob `9ff2991`.
**A4 hybrid rule:** `ty % 2 === 1` → WALL table (wall sides); else → FLOOR table (wall tops).

### ADR-007-4: Recolor = Palette Remapping (not hue shift)
**Decision:** Recolor operates on extracted unique colors (palette) with exact color-to-color mapping.
**Rejected:** Global hue shift (loses per-color control), pixel-by-pixel painting (wrong scope).

### ADR-007-5: Export Checkboxes — TSX Auto-disabled for Recolor
**Decision:** TSX export checkbox is automatically disabled in Recolor mode. Recolored PNGs are not Tiled tilesets.
