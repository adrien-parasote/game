# Spec — Recolor: Fix Palette Swatches + Import Palette from Image

> Document Type: Implementation
> **Covers:** Bug fix AP-RE-SWATCH-01 (swatches blancs macOS) + Feature F-PALETTE-IMG (import palette depuis une image)
> **Parent spec (GUI):** [asset_convertor_mv_gui.md](./asset_convertor_mv_gui.md#recolor-panel)
> **Parent spec (engine):** [asset_convertor_mv_recolor.md](./asset_convertor_mv_recolor.md#L1)

---

## Deep Links

- [GUI spec § Recolor Panel](./asset_convertor_mv_gui.md#recolor-panel)
- [GUI spec § Section A: Palette de l'asset](./asset_convertor_mv_gui.md#section-a-palette-de-lasset)
- [Recolor engine spec § extract_palette](./asset_convertor_mv_recolor.md#extract_palette)
- [Source: `gui/recolor_panel.py` L139–L158](../../src/asset_convertor/gui/recolor_panel.py#L139)
- [Source: `core/recolor.py` § extract_palette](../../src/asset_convertor/core/recolor.py#L1)

---

## Goal

### Fix 1 — Palette de l'asset : swatches blancs

La palette de l'asset s'affiche en blanc/vide sur macOS alors que le label dit "16 couleurs détectées".

**Root cause :** `_rebuild_swatches()` crée des `tk.Button` avec `bg=hex_color`. Sur macOS, le renderer natif de `tk.Button` **ignore la propriété `bg`** pour les boutons sans texte — il dessine un fond système gris/blanc par-dessus. La couleur de fond n'est jamais visible.

**Fix :** Remplacer chaque `tk.Button` par un `tk.Canvas` de taille fixe avec un rectangle coloré peint dessus (identique à ce qui est déjà fait dans les remap rows et les micro-swatches des presets chips). `tk.Canvas` n'est pas soumis au rendu natif macOS et respecte toujours `bg`.

### Feature 2 — Import palette depuis une image externe

Permettre à l'utilisateur de charger une autre image (ex : un autre tileset) et d'en extraire la palette pour harmoniser plusieurs assets. Un bouton "🖼 Importer depuis image…" ouvre un `filedialog`, charge l'image, extrait la palette avec `extract_palette()`, et **remplace la palette cible du remappage** (nearest ΔE CIE76 via `propose_remap()`). En cas d'erreur (fichier illisible, image transparente), le message est transmis à `app.py` via un callback `on_error` pour affichage dans le journal du bas.

---

## Constraints

| Tier | Exemples |
|------|----------|
| **Always do** | Utiliser `tk.Canvas` pour tout rendu de swatch coloré (source et remap). Appeler `extract_palette()` existant sans modification. Transmettre les erreurs via le callback `on_error` vers `app.py` (journal du bas). Rester dans `gui/recolor_panel.py` uniquement — ne pas toucher `core/`. |
| **Ask first** | Modifier la signature de `extract_palette()`. Ajouter de nouvelles dépendances Python. Changer le layout général du `RecolorPanel`. |
| **Never do** | Utiliser `tk.Button` avec `bg=` pour afficher une couleur (broken on macOS). Modifier `core/recolor.py` ou `core/palettes.py`. Bloquer le thread principal pendant `filedialog` (c'est déjà non-bloquant par design Tkinter). Ignorer silencieusement une erreur sans la propager via `on_error`. |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `gui/recolor_panel.py` | Python Module (MODIFY) | This spec § "Implémentation" | `gui/app.py` |
| `tests/asset_convertor/gui/test_recolor_panel.py` | Python Tests | This spec § "Test Cases" | Pytest runner |
| Callback `on_error(message: str)` | Callable[[str], None] | This spec § "Interface on_error" | `gui/app.py` (log du bas) |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `core/recolor.py` → `extract_palette()` | Function | `asset_convertor_mv_recolor.md § "extract_palette"` | Recolor spec |
| `core/recolor.py` → `propose_remap()` | Function | `asset_convertor_mv_recolor.md § "propose_remap"` | Recolor spec |
| `tkinter.filedialog.askopenfilename()` | stdlib | Python docs | stdlib |

### Public Interface

N/A — module interne, pas d'export public.

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Function | `extract_palette(img, max_colors=_MAX_SWATCHES)` | `core/recolor.py` |
| Function | `propose_remap(source_palette, imported_palette)` | `core/recolor.py` |
| Function | `tkinter.filedialog.askopenfilename(filetypes=[...])` | Python stdlib |
| Callback | `on_error(message: str)` | `gui/app.py` (injecté à l'init de `RecolorPanel`) |

### Tracked Concepts

| Concept | Status | Mentioned in |
|---|---|---|
| `tk.Canvas` pour swatches | Fix obligatoire dans ce spec | GUI spec § Section A |
| "Import palette depuis image" | Feature ajoutée (obligatoire) | Aucune mention antérieure |
| `on_error` callback | Nouveau paramètre de `RecolorPanel.__init__` | GUI spec § Recolor Panel |

---

## Assumptions

| # | Assumption | Risk | Source Type | Validation |
|---|---|---|---|---|
| A1 | `tk.Canvas` avec `bg=hex_color` respecte la couleur de fond sur macOS (pas de rendu natif override) | Low | SHOW | Verified via existing `_build_remap_row()` (L268-L280) and `_build_preset_chip()` micro-swatches (L203-L208) where it works correctly. |
| A2 | `tkinter.filedialog.askopenfilename()` est thread-safe à appeler depuis le main thread Tkinter | Low | TELL | Cited from Python standard library docs. |
| A3 | `PIL.Image.open()` + `extract_palette()` peut charger n'importe quel PNG/JPEG sans freeze visible (<100ms) | Low | SHOW | Verified via benchmark: extract_palette runs in ~12ms on `basement_floor.png`. |
| A4 | La Feature 2 n'affecte que `RecolorState.remap_table` — `source_palette` reste la palette de l'asset source | Low | TELL | Design decision: target palette is replaced, not source palette. |
| A5 | `app.py` peut fournir `on_error` à `RecolorPanel.__init__` without structural refactoring | Low | SHOW | Verified via grep of `gui/app.py` showing it uses callables for event wiring. |

---

## Interface on_error

`RecolorPanel` reçoit un nouveau paramètre optionnel à l'initialisation :

```python
def __init__(
    self,
    parent: ctk.CTkFrame,
    state: AppState,
    on_state_change: Callable[[AppState], None],
    on_preview_update: Callable[[Image.Image], None],
    on_error: Callable[[str], None] | None = None,   # ← NEW
) -> None:
    ...
    self._on_error = on_error
```

**Usage interne :**
```python
if self._on_error:
    self._on_error(f"❌ Import palette : {message}")
```

**Côté `app.py` :** Le constructeur de `RecolorPanel` dans `_swap_recolor_panel()` passe `on_error=self._log` (la méthode de log existante qui écrit dans le journal du bas).

> **Ce changement implique une mise à jour de `gui/app.py`** uniquement à l'instanciation de `RecolorPanel` — une seule ligne. Aucune autre modification d'`app.py` requise.

---

## Implémentation

### Bug Fix 1 — `_rebuild_swatches()` : tk.Button → tk.Canvas

**Fichier :** `gui/recolor_panel.py`

**Avant (ligne 144–153) :**
```python
for i, color in enumerate(palette):
    hex_color = _rgb_hex(color)
    btn = tk.Button(
        self._swatch_inner,
        bg=hex_color, activebackground=hex_color,
        width=_SWATCH_SIZE // 8, height=1,
        relief="flat", bd=2,
        command=lambda c=color: self._on_source_swatch_click(c),
    )
    btn.grid(row=0, column=i, padx=1, pady=2)
```

**Après :**
```python
for i, color in enumerate(palette):
    hex_color = _rgb_hex(color)
    canvas = tk.Canvas(
        self._swatch_inner,
        width=_SWATCH_SIZE,
        height=_SWATCH_SIZE,
        bg=hex_color,
        highlightthickness=1,
        highlightbackground="#555",
        cursor="hand2",
    )
    canvas.grid(row=0, column=i, padx=1, pady=2)
    canvas.bind("<Button-1>", lambda e, c=color: self._on_source_swatch_click(c))
```

**Pourquoi `tk.Canvas` fonctionne et `tk.Button` ne fonctionne pas sur macOS :**
- `tk.Button` sur macOS utilise le rendu natif Aqua qui ignore `bg` pour les boutons sans texte/image.
- `tk.Canvas` est un widget de dessin brut — `bg` est always respected, pas de surcharge du thème natif.
- **Preuve dans le code existant :** `_build_remap_row()` L268 et les micro-swatches des preset chips L203 utilisent déjà `tk.Canvas` et s'affichent correctement.

**Suppression des imports inutilisés :** Si `tk.Button` n'est plus utilisé nulle part dans le fichier après ce fix, vérifier et retirer l'import si applicable.

---

### Feature 2 (Optionnelle) — Bouton "Importer depuis image…"

**Fichier :** `gui/recolor_panel.py`

#### 2a. Ajout du bouton dans `_build_palette_section()`

Ajouter un bouton CTk sous le label `self._lbl_palette_info` (row 4) :

```python
self._btn_import_palette = ctk.CTkButton(
    frame,
    text="🖼 Importer depuis image…",
    height=24,
    font=ctk.CTkFont(size=11),
    command=self._import_palette_from_image,
)
self._btn_import_palette.grid(row=4, column=0, pady=(2, 6))
```

#### 2b. Méthode `_import_palette_from_image()`

```python
def _import_palette_from_image(self) -> None:
    """Open a file dialog, extract palette from chosen image, use it as remap target."""
    path = askopenfilename(
        title="Choisir une image source de palette",
        filetypes=[
            ("Images PNG/JPEG", "*.png *.jpg *.jpeg"),
            ("Tous les fichiers", "*.*"),
        ],
    )
    if not path:
        return  # User cancelled — no-op

    try:
        img = Image.open(path).convert("RGBA")
        imported_palette = extract_palette(img, max_colors=_MAX_SWATCHES)
    except OSError as exc:
        if self._on_error:
            self._on_error(f"❌ Import palette : fichier illisible — {exc}")
        return
    except ValueError as exc:
        # extract_palette raises ValueError when image is fully transparent
        if self._on_error:
            self._on_error(f"❌ Import palette : image vide (aucun pixel non-transparent) — {exc}")
        return

    rs = self._state.recolor
    if rs is None or not rs.source_palette:
        # No source palette yet — nothing to remap against
        if self._on_error:
            self._on_error("⚠️ Import palette : chargez d'abord un asset source.")
        return

    remap = propose_remap(rs.source_palette, imported_palette)
    rs_updated = dataclasses.replace(
        rs,
        remap_table=remap,
        active_preset=None,  # Clear preset selection — custom palette now active
    )
    self._state = dataclasses.replace(self._state, recolor=rs_updated)
    self._on_state_change(self._state)

    self._rebuild_remap_rows(rs_updated.source_palette, remap)
    self._schedule_preview_refresh()
```

**Imports à ajouter** en haut du fichier (si pas déjà présents) :
```python
from tkinter.filedialog import askopenfilename
```

> **Note (divergence résolue) :** Le pattern initial `from tkinter import filedialog` + `filedialog.askopenfilename(...)` a été remplacé par l'import direct `from tkinter.filedialog import askopenfilename` pour permettre un `mock.patch("...askopenfilename")` fiable dans les tests (le sous-attribut `filedialog.askopenfilename` n'est pas patchable de façon isolée dans un contexte pytest multi-module).

#### 2c. Comportement attendu

1. L'utilisateur ouvre l'asset à recolorer (source).
2. L'utilisateur clique "🖼 Importer depuis image…".
3. Un `filedialog` s'ouvre → l'utilisateur choisit un autre tileset.
4. `extract_palette()` extrait les couleurs les plus fréquentes de l'image importée.
5. `propose_remap()` mappe la palette source → palette importée (nearest ΔE CIE76).
6. La section Remappage se reconstruit avec les nouvelles couleurs cibles.
7. Le prévisualisation se met à jour (debounce 300ms).

**Limite :** Si l'image importée a moins de couleurs que la source, plusieurs couleurs source mapperont vers la même couleur cible (many-to-one — comportement déjà documenté dans la spec recolor § AP-RE-01).

---

## Project File Tree

```
tools/src/asset_convertor/
  gui/
    recolor_panel.py    # [MODIFY] __init__: ajout param on_error
                        #          _rebuild_swatches: tk.Button → tk.Canvas
                        #          _build_palette_section: ajout bouton import
                        #          _import_palette_from_image: nouvelle méthode
    app.py              # [MODIFY] instanciation de RecolorPanel: ajout on_error=self._log
tests/asset_convertor/gui/
  test_recolor_panel.py # [NEW] 11 unit tests + 4 integration tests
```

---

## Bundling & Native-Module Audit

- BM1: N/A — Python desktop app, no bundled framework.
- BM2: N/A
- BM3: N/A — `tkinter.filedialog` est stdlib.
- BM4: N/A — aucun renommage de constante.

---

## Error Handling Matrix

| Error / Exception | Trigger / Detection | Response / Action | Recovery / Fallback |
|---|---|---|---|
| `_rebuild_swatches` appelé avec palette vide | Aucune couleur détectée dans source | (aucun message) | Canvas inner vide, label : "0 couleur détectée". No-op. |
| `filedialog` annulé par l'utilisateur | Bouton Import → Cancel | (aucun message) | `path` est `""` → early return. |
| Image importée illisible (`OSError`) | Fichier corrompu ou format non supporté | `on_error("❌ Import palette : fichier illisible — {exc}")` → journal du bas | Early return, state inchangé. |
| Image importée entièrement transparente (`ValueError` de `extract_palette`) | Image PNG 100% transparente | `on_error("❌ Import palette : image vide (aucun pixel non-transparent) — {exc}")` → journal du bas | Early return, state inchangé. |
| `_import_palette_from_image` appelé sans asset source chargé | `rs.source_palette == []` | `on_error("⚠️ Import palette : chargez d'abord un asset source.")` → journal du bas | Early return. |
| `on_error` est `None` (not wired) | `RecolorPanel` instancié sans `on_error=` | Errors silencieux — dégradation gracieuse. | `if self._on_error: self._on_error(...)` guard partout. |

---

## Anti-Patterns

| # | Anti-Pattern | Why Wrong | Do Instead |
|---|---|---|---|
| AP-SW-01 | Utiliser `tk.Button` avec `bg=hex_color` pour afficher une couleur sur macOS | Le rendu natif Aqua ignore `bg` sur les boutons sans texte. Les swatches apparaissent blancs. | Utiliser `tk.Canvas` avec `bg=hex_color` + `canvas.bind("<Button-1>", ...)` pour le clic. |
| AP-SW-02 | Charger l'image importée dans un thread en arrière-plan | `tkinter.filedialog` doit être appelé depuis le main thread. Si on lance un thread pour toute l'opération, le filedialog sera appelé depuis ce thread → crash ou comportement indéfini. | Appeler `filedialog.askopenfilename()` dans le main thread (dans `_import_palette_from_image` directement). `Image.open()` + `extract_palette()` sont assez rapides (< 100ms pour un tileset MV) pour rester en main thread. |
| AP-SW-03 | Remplacer `RecolorState.source_palette` par la palette importée | L'utilisateur perd la palette de l'asset source — il ne peut plus voir quelles couleurs sont remappées. | La palette importée est la **cible** du remappage. `source_palette` reste celle de l'asset ouvert. |
| AP-SW-04 | Appeler `Image.open(path)` sans `.convert("RGBA")` | `extract_palette` appelle `.load()` et itère sur les tuples — une image en mode "P" (indexed) retourne des entiers, pas des tuples (R,G,B,A). | Toujours `.convert("RGBA")` après `Image.open()`. |
| AP-SW-05 | Ne pas passer `max_colors=_MAX_SWATCHES` à `extract_palette()` dans l'import | Une photo importée peut avoir 10 000+ couleurs uniques → `extract_palette` retourne 256 couleurs → la section remappage a 256 lignes → UI inutilisable. | Toujours passer `max_colors=_MAX_SWATCHES` (32) dans le contexte GUI. |
| AP-SW-06 | Ignorer silencieusement les erreurs d'import (`except: pass`) | L'utilisateur clique "Importer", rien ne se passe — feedback zéro. Impossible de diagnostiquer. | Toujours appeler `self._on_error(message)` dans chaque branche d'erreur. Protéger avec `if self._on_error:` pour la dégradation gracieuse si le callback n'est pas câblé. |

---

## Test Case Specifications

### Unit Tests — `test_recolor_panel.py`

> Ces tests vérifient les comportements sans lancer la fenêtre CTk complète (mock `ctk.CTk`).

| ID | Test | Input | Expected |
|---|---|---|---|
| TC-001 | `_rebuild_swatches` crée des `tk.Canvas`, pas des `tk.Button` | Palette de 3 couleurs | `len(swatch_inner.winfo_children()) == 3` + tous les enfants sont `tk.Canvas` |
| TC-002 | Le `bg` du Canvas correspond à la couleur hex | Couleur `(255, 0, 0, 255)` | `canvas.cget("bg") == "#ff0000"` |
| TC-003 | Label `_lbl_palette_info` affiche le bon nombre | Palette de 5 couleurs | `"5 couleurs détectées"` |
| TC-004 | Palette vide → aucun enfant, label "0 couleur détectée" | `palette = []` | `len(children) == 0` + label `"0 couleur détectée"` |
| TC-005 | `_import_palette_from_image` : cancel filedialog → no-op, no error | `askopenfilename` retourne `""` | `_state.recolor.remap_table` inchangé, `on_error` non appelé |
| TC-006 | `_import_palette_from_image` : image illisible → on_error appelé, state inchangé | `Image.open` lève `OSError` | `on_error` appelé avec message `"❌ Import palette : fichier illisible"`, state inchangé |
| TC-007 | `_import_palette_from_image` : image transparente → on_error appelé, state inchangé | `extract_palette` lève `ValueError` | `on_error` appelé avec message `"❌ Import palette : image vide"`, state inchangé |
| TC-008 | `_import_palette_from_image` sans source_palette chargée → on_error appelé, early return | `rs.source_palette == []` | `on_error` appelé avec message `"⚠️ Import palette : chargez d'abord un asset source."`, `propose_remap` non appelé |
| TC-009 | Import valide → `remap_table` mis à jour | Image 4 couleurs importée, source 3 couleurs | `len(remap_table) == 3` (len de source_palette) |
| TC-010 | Import valide → `active_preset` mis à None | `rs.active_preset == "Autumn"` avant import | `rs.active_preset is None` après import |
| TC-011 | `on_error=None` (pas câblé) → dégradation gracieuse | Instancier `RecolorPanel` sans `on_error`, déclencher OSError | Aucune exception levée depuis `RecolorPanel` |

### Integration Tests

| ID | Test | Scenario | Expected |
|---|---|---|---|
| IT-001 | Palette visible après chargement d'un asset | Charger `basement_floor.png` → mode Recolor | Section palette non vide, couleurs correctes (non blanches) |
| IT-002 | Import image externe valide → remappage mis à jour + preview refresh schedulé | Charger asset source + importer palette d'un autre tileset PNG valide | `remap_table` non vide, `_debounce_id` non None, `on_error` non appelé |
| IT-003 | Swatches et remap rows utilisent le même composant `tk.Canvas` | Inspecter les widgets après palette extract + preset select | Tous les swatches couleur sont `tk.Canvas` (pas `tk.Button`) |
| IT-004 | Import depuis app.py — `on_error` câblé sur `self._log` | Importer un fichier non-image (ex: `.txt`) | Message d'erreur apparaît dans le journal du bas |

---

## Correction Log

| Date | Issue | Fix | Author |
|------|-------|-----|--------|
| 2026-06-09 | Swatches palette de l'asset blancs sur macOS — `tk.Button.bg` ignoré par le rendu Aqua natif | Ce spec — fix `_rebuild_swatches` : `tk.Button` → `tk.Canvas` | SPEC |
| 2026-06-09 | Feature import palette depuis image initialement marquée optionnelle — rendue obligatoire. Gestion erreur initiale silencieuse — changée vers callback `on_error` → journal du bas (option C). | Spec mise à jour | SPEC |
| 2026-06-09 | HARDEN /doc-update — Drift : import `filedialog` remplacé par import direct `askopenfilename`. Spec et exemples de code mis à jour pour refléter le pattern réel (`from tkinter.filedialog import askopenfilename`). Raison : patchabilité fiable dans pytest multi-module. | Spec corrigée (lignes imports + code example 2b) | HARDEN |
