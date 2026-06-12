# ADR-002 — CustomTkinter Replaces DearPyGui

## Status: ✅ Accepted

## Context

ADR-001 selected DearPyGui as the GUI framework for the asset converter tool. After implementation, DearPyGui proved difficult to package and distribute cross-platform and had a less Pythonic API than desired for rapid prototyping of the tool's UI.

## Decision

Migrate the asset converter GUI from DearPyGui to CustomTkinter.

## Rationale

- CustomTkinter is built on Tkinter (stdlib) — zero external binary dependency
- Simpler widget model matches the converter's single-window layout
- Native look-and-feel on macOS without additional setup
- Faster iteration on layout changes

## Consequences

- ADR-001 is superseded
- DearPyGui is removed from requirements
- All GUI code in `tools/src/asset_convertor/gui/` migrated to CustomTkinter widgets
- Existing functionality preserved (file picker, conversion controls, progress display)
