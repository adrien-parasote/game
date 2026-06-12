# ADR-001: Dear PyGui replaces Pygame preview, CLI preserved

> **Date:** 2026-05-31
> **Status:** ❌ Superseded by ADR-002
> **Context:** Asset Convertor V3

## Context

The Asset Convertor has two user-facing interfaces:
1. **CLI** (`cli.py`) — scripted generation with `--terrain`, `--quality`, `--seed` flags
2. **Pygame preview** (`preview/pygame_preview.py`) — read-only display after generation, SPACE to regenerate minimap

The current workflow is edit YAML → run CLI → view preview → close → repeat. This is slow for iterative design.

## Decision

- **Replace** `preview/pygame_preview.py` with a Dear PyGui interactive GUI
- **Preserve** `cli.py` for scripted/automated workflows
- **Extract** minimap logic into `core/minimap.py` (shared by both)
- **Demote** `pygame-ce` from hard dependency to optional (CLI `--preview` only)

## Consequences

### Positive
- Real-time parameter iteration (< 1s feedback loop)
- All texture parameters exposed as interactive widgets
- 1-click export from GUI
- Core pipeline unchanged — GUI is a thin wrapper

### Negative
- Two entry points to maintain (CLI + GUI)
- Dear PyGui in maintenance mode (acceptable risk for internal tool)
- Pygame-CE still needed if CLI `--preview` flag is used

### Neutral
- numpy becomes a required dependency (already used by subtile.py)
- New module: `tools/asset_convertor/gui/` (~300-400 lines estimated)

## Alternatives Considered

| Option | Rejected Because |
|--------|-----------------|
| PySide6 | 500MB+ install, signal/slot complexity, overkill for parameter tool |
| CustomTkinter | No color picker, slow image updates, maintenance declining |
| Flet | Base64 encoding bottleneck for real-time preview |
| Replace CLI too | Breaks scripted/automated workflows |
