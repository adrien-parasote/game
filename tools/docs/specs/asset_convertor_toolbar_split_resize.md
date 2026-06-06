# Spec — Toolbar Split (Import Tiled / Modifications) + Outil Resize 48px→32px

> Document Type: Implementation
> **Covers:** F-TOOLBAR-SPLIT (séparation visuelle en deux groupes), F-RESIZE-TOOL (outil de redimensionnement 48px→32px)
> **Parent spec:** [asset_convertor_mv_gui.md](./asset_convertor_mv_gui.md)

---

## Deep Links

- [app.py — `_build_primary_toolbar()`](../../src/asset_convertor/gui/app.py#L254)
- [app.py — `_TILED_TYPE_MAP` + `_MOD_TYPE_MAP`](../../src/asset_convertor/gui/app.py#L99)
- [app.py — `_on_tiled_type_change()` / `_on_mod_type_change()`](../../src/asset_convertor/gui/app.py#L697)
- [app.py — `_on_type_change_internal()`](../../src/asset_convertor/gui/app.py#L714)
- [app.py — `_validate_resize_dimensions()`](../../src/asset_convertor/gui/app.py#L1418)
- [app.py — `_convert_resize()` + `_on_convert_success_resize()`](../../src/asset_convertor/gui/app.py#L907)
- [app.py — `_export_resize()`](../../src/asset_convertor/gui/app.py#L1380)
- [app.py — `_swap_secondary()`](../../src/asset_convertor/gui/app.py#L304)
- [state.py — `ResourceType` Literal](../../src/asset_convertor/gui/state.py#L25)
- [test_gui_state_v2.py — tests existants](../../../tools/tests/asset_convertor/gui/test_gui_state_v2.py)
- [test_resize_logic.py — tests resize](../../../tools/tests/asset_convertor/gui/test_resize_logic.py)
- [Spec GUI parent § "Primary Toolbar"](./asset_convertor_mv_gui.md#primary-toolbar-_build_primary_toolbar)
- [Spec GUI parent § "Anti-Patterns"](./asset_convertor_mv_gui.md#anti-patterns)

---

## Goal

Diviser la primary toolbar en **deux groupes visuellement distincts** :

- **Groupe Import Tiled** : `🎮 Animé | 🏠 Bâtiment | 🧱 Mur | 🌱 Sol` (types A1/A3/A4/A2 — produisent des assets pour Tiled)
- **Groupe Modifications** : `🎨 Recolor | 🔄 Resize` (outils de transformation post-import)

Et ajouter un **outil Resize** dans le groupe Modifications : charge un PNG 48px, produit un PNG 32px via `Image.NEAREST`.

---

## Constraints

| Tier | Exemples |
|------|----------|
| **Always do** | Labels en français. `dataclasses.replace()` pour toutes les mises à jour d'AppState. UI updates via `self.after(0, callback)` depuis les threads. Désélectionner le groupe opposé quand l'utilisateur clique dans un groupe. |
| **Ask first** | Ajouter des dépendances Python autres que Pillow et CustomTkinter. Modifier les signatures des convertisseurs existants (`convert_mv`, `convert_xp`, etc.). |
| **Never do** | Modifier la logique de conversion A1/A2/A3/A4/Recolor existante. Mettre la logique de conversion dans `core/` pour Resize (trop simple, < 10 lignes). Utiliser un filtre autre que `Image.NEAREST` pour le resize pixel art. Casser les comportements exportés (TSX/PNG) existants. |

---

## Cross-Spec Contracts

### Produces

| Path / Identifier | Format | Schema location | Consumers |
|---|---|---|---|
| `gui/app.py` — `_build_primary_toolbar()` modifié | Python function | This spec § "Primary Toolbar — Nouveau layout" | `_build_ui()` (même fichier) |
| `gui/state.py` — `ResourceType` étendu | Python Literal | This spec § "AppState — extension ResourceType" | `app.py`, `test_gui_state_v2.py` |

### Consumes

| Path / Identifier | Format | Schema location | Producer |
|---|---|---|---|
| `core/converter_mv.py` | Python module | `autotile_converter_spec.md` | A2/A1 |
| `core/converter_mv_a3.py` | Python module | `asset_convertor_mv_core_converters.md` | A3 |
| `core/converter_mv_a4.py` | Python module | `asset_convertor_mv_core_converters.md` | A4 |
| `core/recolor.py` → `apply_remap()` | Function | `asset_convertor_mv_recolor.md` | Recolor |

### Public Interface

| Type | Identifier | Documenté ici |
|---|---|---|
| Python Literal | `ResourceType = Literal["A1","A2","A3","A4","Recolor","Resize"]` | This spec § "AppState — extension ResourceType" |

### External Invocations

| Type | Invoked | Defined in |
|---|---|---|
| Pillow | `Image.open(path).resize((32, 32), resample=Image.NEAREST)` | Pillow stdlib |

### Tracked Concepts

| Concept | Statut | Mentionné dans |
|---|---|---|
| `resource_type` | Étendu avec `"Resize"` | `asset_convertor_mv_gui.md` |
| `_TYPE_LABEL_MAP` | Remplacé par `_TILED_TYPE_MAP` + `_MOD_TYPE_MAP` | `asset_convertor_mv_gui.md` |

---

## Primary Toolbar — Nouveau layout

**Fichier :** `gui/app.py` → `_build_primary_toolbar()`

### Disposition visuelle

```
Row 0 de la primary toolbar (CTkFrame height=56):

col 0    col 1                                   col 2         col 3     col 5(weight spacer)  col 6
[Ouvrir] [🎮 Animé | 🏠 Bâtiment | 🧱 Mur | 🌱 Sol]  [séparateur]  [🎨 Recolor | 🔄 Resize]  ←spacer→      [⚙ Convertir]
          seg_tiled (CTkSegmentedButton)          CTkFrame 2px   seg_mod (CTkSegmentedButton)
```

> **Note colonnes :** Les colonnes 0, 1, 2, 3 sont les widgets. La colonne 5 reçoit `weight=1` (spacer extensible via `grid_columnconfigure`). La colonne 6 contient `btn_convert`. Il n'y a pas de widget en colonne 4.

### Implémentation

```python
# ── Variables de groupe ─────────────────────────────────────────────────────

# Dictionnaire Import Tiled : label → ResourceType
_TILED_TYPE_MAP: dict[str, str] = {
    "🎮 Animé":    "A1",
    "🏠 Bâtiment": "A3",
    "🧱 Mur":      "A4",
    "🌱 Sol":      "A2",
}

# Dictionnaire Modifications : label → ResourceType
_MOD_TYPE_MAP: dict[str, str] = {
    "🎨 Recolor": "Recolor",
    "🔄 Resize":  "Resize",
}

# [REMOVED] _LABEL_BY_TYPE inverse lookup — aucun consommateur documenté (YAGNI).
# Si nécessaire, calculer à la demande : {v: k for k, v in {**_TILED_TYPE_MAP, **_MOD_TYPE_MAP}.items()}
```

```python
def _build_primary_toolbar(self) -> None:
    bar = ctk.CTkFrame(self, height=56, corner_radius=0)
    bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
    bar.grid_columnconfigure(5, weight=1)  # spacer avant Convertir

    # col 0 — Ouvrir
    self.btn_open = ctk.CTkButton(bar, text="📂 Ouvrir", width=130, command=self._open_file)
    self.btn_open.grid(row=0, column=0, padx=(12, 8), pady=10)

    # col 1 — Groupe Import Tiled
    self._tiled_type_var = ctk.StringVar(value="🌱 Sol")
    self.seg_tiled = ctk.CTkSegmentedButton(
        bar,
        values=list(_TILED_TYPE_MAP.keys()),
        variable=self._tiled_type_var,
        command=self._on_tiled_type_change,
    )
    self.seg_tiled.grid(row=0, column=1, padx=(4, 4), pady=10)

    # col 2 — Séparateur visuel (CTkFrame vertical 2px)
    ctk.CTkFrame(bar, width=2, height=28, fg_color="gray40").grid(
        row=0, column=2, padx=6, pady=14,
    )

    # col 3 — Groupe Modifications
    self._mod_type_var = ctk.StringVar(value="")
    self.seg_mod = ctk.CTkSegmentedButton(
        bar,
        values=list(_MOD_TYPE_MAP.keys()),
        variable=self._mod_type_var,
        command=self._on_mod_type_change,
    )
    self.seg_mod.grid(row=0, column=3, padx=(4, 4), pady=10)

    # col 5 (spacer — weight configuré par grid_columnconfigure(5, weight=1))
    ctk.CTkLabel(bar, text="").grid(row=0, column=5, sticky="ew")

    # col 6 — Convertir / Appliquer
    self.btn_convert = ctk.CTkButton(
        bar, text="⚙ Convertir", width=140,
        state="disabled", command=self._run_conversion,
    )
    self.btn_convert.grid(row=0, column=6, padx=(8, 12), pady=10)
```

### Callbacks de groupe — sélection exclusive croisée

```python
def _on_tiled_type_change(self, label: str) -> None:
    """Sélection dans le groupe Import Tiled → déselectionne le groupe Modifications."""
    if label == "":  # guard défensif — set("") peut déclencher le callback selon la version CTk
        return
    self._mod_type_var.set("")
    resource_type = _TILED_TYPE_MAP.get(label, "A2")
    self._on_type_change_internal(resource_type)

def _on_mod_type_change(self, label: str) -> None:
    """Sélection dans le groupe Modifications → déselectionne le groupe Import Tiled."""
    if label == "":  # guard défensif — set("") peut déclencher le callback selon la version CTk
        return
    self._tiled_type_var.set("")
    resource_type = _MOD_TYPE_MAP.get(label, "Recolor")
    self._on_type_change_internal(resource_type)
```

> **Note :** `_on_type_change()` existant est renommé `_on_type_change_internal()`. Les deux nouveaux callbacks appellent `_on_type_change_internal()`. Pas de changement de logique interne.

### Désélection par `set("")`

Quand `CTkSegmentedButton.variable.set("")`, aucun segment n'est visuellement actif (comportement CustomTkinter natif). C'est le mécanisme de désélection croisée entre les deux groupes.

**Comportement du callback :** `set("")` appelé programmatiquement ne déclenche PAS le callback `command` dans CustomTkinter — seule une interaction utilisateur le déclenche. [ASSUMED Medium — valider visuellement au BUILD.] Le guard `if label == "": return` est présent dans les deux callbacks à titre défensif pour toutes les versions de CustomTkinter.

**Règle :** L'un des deux groupes a TOUJOURS un segment sélectionné, sauf pendant la transition entre groupes (fenêtre ~1 frame).

---

## AppState — Extension ResourceType

**Fichier :** `gui/state.py`

```python
# Avant
ResourceType = Literal["A1", "A2", "A3", "A4", "Recolor"]

# Après
ResourceType = Literal["A1", "A2", "A3", "A4", "Recolor", "Resize"]
```

Aucun autre champ de `AppState` ne change. Le type `Resize` se comporte comme `Recolor` pour les règles TSX :
- `export_tsx` = **False** quand `resource_type == "Resize"` (pas de tileset Tiled produit)
- `export_tsx` = True pour tous les autres types

---

## Secondary Toolbar — Resize

**Fichier :** `gui/app.py` → nouveau `_build_secondary_resize()`

```python
def _build_secondary_resize(self, parent: ctk.CTkFrame) -> None:
    """Resize: hint label — source attendue 48px."""
    ctk.CTkLabel(
        parent,
        text="📐 Source attendue : PNG 48px (multiples de 48) — Produit une image 32px (ratio 1.5×, pixel-perfect)",
        text_color="gray",
        font=ctk.CTkFont(size=11),
    ).grid(row=0, column=0, padx=(16, 4), pady=10)
```

Ajout dans `_swap_secondary()` :

```python
builders = {
    "A2":     self._build_secondary_a2,
    "A3":     self._build_secondary_a3,
    "A4":     self._build_secondary_a4,
    "A1":     self._build_secondary_a1,
    "Recolor": self._build_secondary_recolor,
    "Resize": self._build_secondary_resize,  # ← nouveau
}
```

---

## Conversion Resize — `_convert_resize()`

**Fichier :** `gui/app.py`

> **Threading :** `_convert_resize()` est appelée via `threading.Thread(target=self._convert_resize, daemon=True)` dans `_run_conversion()` — même pattern que `_convert_a2`, `_convert_a3`, etc. Ne jamais appeler directement depuis le thread UI.

```python
def _convert_resize(self) -> None:
    """Resize PNG 48px → 32px via NEAREST (pixel art, ratio 1.5× exact).

    Appelée dans un thread daemon par _run_conversion() — ne pas appeler depuis le thread UI.
    """
    try:
        img = self._state.source_img
        if img is None:
            msg = "⚠️ Aucun fichier source chargé."
            self.after(0, lambda m=msg: self._on_convert_error(m))
            return

        src_w, src_h = img.size
        # Calcul proportionnel : 48→32 = ratio 2/3 exact
        target_w = round(src_w * 32 / 48)
        target_h = round(src_h * 32 / 48)

        result = img.resize((target_w, target_h), resample=Image.NEAREST)

        self._state = dataclasses.replace(self._state, result_img=result)
        self.after(0, lambda: self._on_convert_success_resize(result))
    except Exception as err:
        msg = str(err)
        self.after(0, lambda m=msg: self._on_convert_error(m))

def _on_convert_success_resize(self, result: Image.Image) -> None:
    """Affiche le résultat resize dans le panneau SORTIE."""
    self.btn_convert.configure(state="normal")
    self.btn_export.configure(state="normal")
    self._display_result_image(result)
    w, h = result.size
    self.lbl_output_info.configure(text=f"Resize : {w}×{h} px (32px)")
    self._set_status(f"Resize terminé — {w}×{h} px.")
```

Ajout dans `_run_conversion()` dispatch — chaque entrée est passée comme `target` à `threading.Thread` :

```python
dispatch = {
    "A2":     self._convert_a2,
    "A3":     self._convert_a3,
    "A4":     self._convert_a4,
    "A1":     self._convert_a1,
    "Recolor": self._apply_recolor,
    "Resize": self._convert_resize,  # ← nouveau
}
# Appel effectif : threading.Thread(target=dispatch[resource_type], daemon=True).start()
```

### Comportement du canvas pour Resize

Le panneau APERÇU CANVAS est **masqué** pour le type Resize (aucun autotile à prévisualiser). Comportement identique au mode Recolor : pas de canvas, pas de toggle.

> **Implémentation :** Dans `_on_type_change_internal()`, ajouter `resource_type in ("Recolor", "Resize")` pour les branches qui cachent/restaurent le canvas panel.

---

## Validation des dimensions — extension

**Fichier :** `gui/app.py` → `_validate_dimensions()` + `_open_file()` + `_on_type_change_internal()`

Pour le type Resize, la validation accepte **toute image dont width et height sont multiples de 48** :

```python
if resource_type == "Resize":
    if img.width % 48 != 0 or img.height % 48 != 0:
        return (
            f"⚠️ Resize : dimensions {img.width}×{img.height} px non multiples de 48. "
            "Attendu : multiples de 48 px (ex: 48×48, 96×96, 192×192)."
        )
    return None  # OK
```

### Re-validation lors d'un changement de type (F-VALIDATION-TIMING-01)

La validation ci-dessus est appelée dans `_open_file()`. **Elle doit aussi être appelée dans `_on_type_change_internal()`** quand le type passe à `"Resize"` et qu'un fichier est déjà chargé — sinon l'utilisateur peut convertir un fichier non-multiple de 48 sans erreur.

```python
# Dans _on_type_change_internal(), après le bloc canvas/export_tsx :
if resource_type == "Resize" and self._state.source_img is not None:
    err_msg = self._validate_resize_dimensions(self._state.source_img)
    if err_msg:
        self._set_status(err_msg)
        self.btn_convert.configure(state="disabled")
    elif self._state.source_img is not None:
        self.btn_convert.configure(state="normal")
```

> **Séquence couverte :** (1) Utilisateur ouvre fichier 64×64 en mode Recolor → valide. (2) Bascule sur Resize → re-validation → dimensions non multiples de 48 → `btn_convert` désactivé + message status. Convertir reste inatteignable.

---

## Comportement export pour Resize

- `export_tsx` = False (auto-set dans `_on_type_change_internal()` quand `resource_type == "Resize"`)
- `export_png` = True (comportement standard)
- Nom du fichier exporté : `{source_stem}_32px.png`

Ajout dans `_export()` (section Resize) :

```python
if self._state.resource_type == "Resize":
    stem = Path(self._state.source_path).stem
    out_path = Path(self._state.output_dir) / f"{stem}_32px.png"
    self._state.result_img.save(str(out_path))
    self._log(f"✅ Export Resize : {out_path.name}")
    return
```

---

## Error Handling Matrix

| Erreur | Déclencheur | Message utilisateur | Récupération |
|--------|-------------|---------------------|--------------|
| Source non chargée (Resize) | Clic Convertir sans fichier ouvert | `"⚠️ Aucun fichier source chargé."` (log) | No-op |
| Dimensions non multiples de 48 | Ouverture PNG dont w ou h % 48 ≠ 0 | `"⚠️ Resize : dimensions NxM px non multiples de 48."` (status) | Disable btn_convert |
| Dimensions non valides après changement de type | Bascule vers Resize avec image déjà chargée non-multiple de 48 | `"⚠️ Resize : dimensions NxM px non multiples de 48."` (status) | Disable btn_convert |
| Erreur Pillow inattendue | `img.resize()` lève une exception | `"❌ Erreur resize : {error}"` (log) | Préserver état précédent |
| Export sans result_img | Clic Exporter sans conversion | `"⚠️ Aucun résultat à exporter."` (log) | No-op |
| Chemin export déjà existant | `{stem}_32px.png` existe dans output_dir | Écrasement silencieux | Convention app — comportement identique aux autres exporteurs |

**Statuts des claims :**
- Pillow `Image.NEAREST` ratio 1.5× → **VERIFIED** (research + documentation officielle Pillow)
- `CTkSegmentedButton.variable.set("")` déselectionne tous les segments → **ASSUMED** (Medium — à valider visuellement lors du BUILD)
- `set("")` ne déclenche pas le callback `command` programmatiquement → **ASSUMED** (Medium — guard défensif `if label == "": return` présent dans les deux callbacks)

---

## Anti-Patterns

| # | Anti-Pattern | Pourquoi incorrect | À faire à la place |
|---|---|---|---|
| AP-SPLIT-01 | Garder un seul `CTkSegmentedButton` et ajouter "Resize" dedans | Mélange les deux groupes logiques dans un seul widget non séparable visuellement | Deux `CTkSegmentedButton` distincts + `CTkFrame` séparateur 2px |
| AP-SPLIT-02 | Gérer la désélection croisée dans `_on_type_change_internal()` plutôt que dans les callbacks de groupe | `_on_type_change_internal()` ne connaît pas quel groupe vient d'être activé | Désélection dans `_on_tiled_type_change()` et `_on_mod_type_change()` AVANT d'appeler la logique commune |
| AP-SPLIT-03 | Utiliser `Image.LANCZOS` ou `Image.BILINEAR` pour le resize | Introduit du flou/anti-aliasing sur les bords des pixels — destroy la netteté pixel art | `Image.NEAREST` uniquement |
| AP-SPLIT-04 | Calculer `target_w = src_w // 48 * 32` (division entière) | `//` introduit des erreurs d'arrondi si `src_w` n'est pas multiple de 48. `round(src_w * 32 / 48)` est plus précis. | `round(src_w * 32 / 48)` |
| AP-SPLIT-05 | Afficher le canvas APERÇU pour le mode Resize | Le Resize ne produit pas d'autotile — le canvas 5×5 n'a pas de signification pour une image redimensionnée | Cacher le canvas panel (`grid_remove()`) comme pour Recolor |
| AP-SPLIT-06 | Modifier `_on_type_change()` directement sans le renommer `_on_type_change_internal()` | Le nom `_on_type_change(label: str)` prend un label de `CTkSegmentedButton` — avec deux groupes, ce contrat est ambigu | Renommer en `_on_type_change_internal(resource_type: str)` qui prend le type interne, non le label |
| AP-SPLIT-07 | Exporter un TSX pour le type Resize | Resize produit une image PNG simple, pas un autotile Tiled. Un TSX serait invalide. | Forcer `export_tsx=False` dans `_on_type_change_internal()` pour `resource_type == "Resize"` |

---

## Test Case Specifications

### Unit Tests — à ajouter dans `test_gui_state_v2.py`

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-RSZ-U-001 | `ResourceType` accepte `"Resize"` | `AppState(resource_type="Resize")` | Pas d'erreur, `state.resource_type == "Resize"` |
| TC-RSZ-U-002 | AppState Resize force `export_tsx=False` (règle métier) | `AppState(resource_type="Resize", export_tsx=False)` | `state.export_tsx is False` |
| TC-RSZ-U-003 | `dataclasses.replace()` préserve `resource_type="Resize"` | `replace(AppState(), resource_type="Resize")` | `state.resource_type == "Resize"` |
| TC-RSZ-U-004 | AppState frozen avec `resource_type="Resize"` | `state = AppState(resource_type="Resize"); state.resource_type = "A2"` | `FrozenInstanceError` |
| TC-RSZ-U-005 | `result_img` None par défaut pour Resize | `AppState(resource_type="Resize")` | `state.result_img is None` |

### Unit Tests — logique resize (à ajouter dans `test_resize_logic.py` nouveau fichier)

| ID | Test | Input | Expected |
|----|------|-------|----------|
| TC-RSZ-U-010 | Resize 48×48 → 32×32 | `Image.new("RGBA", (48, 48)).resize((32, 32), Image.NEAREST)` | `result.size == (32, 32)` |
| TC-RSZ-U-011 | Resize 96×96 → 64×64 | `Image.new("RGBA", (96, 96)).resize((64, 64), Image.NEAREST)` | `result.size == (64, 64)` |
| TC-RSZ-U-012 | Resize 192×48 (wide) → 128×32 | `Image.new("RGBA", (192, 48)).resize((128, 32), Image.NEAREST)` | `result.size == (128, 32)` |
| TC-RSZ-U-013 | Validation : 48×48 → None (pas d'erreur) | `_validate_resize_dimensions(48, 48)` | `None` |
| TC-RSZ-U-014 | Validation : 46×48 → message d'erreur | `_validate_resize_dimensions(46, 48)` | chaîne non-None contenant `"non multiples de 48"` |
| TC-RSZ-U-015 | Validation : 48×46 → message d'erreur | `_validate_resize_dimensions(48, 46)` | chaîne non-None contenant `"non multiples de 48"` |
| TC-RSZ-U-016 | Calcul target_w = round(192 * 32 / 48) == 128 | Calcul arithmétique | `128` |
| TC-RSZ-U-017 | `Image.NEAREST` préserve les couleurs exactes | Pixel rouge pur `(255, 0, 0, 255)` dans image 48×48 → resize 32×32 | Pixel correspondant == `(255, 0, 0, 255)` |

### Integration Tests

| ID | Test | Scénario | Expected |
|----|------|----------|----------|
| IT-RSZ-001 | Sélection Resize force `export_tsx=False` | Simuler `_on_type_change_internal("Resize")` | `self._state.export_tsx == False` |
| IT-RSZ-002 | Sélection A2 après Resize restaure `export_tsx=True` | `_on_type_change_internal("A2")` après Resize | `self._state.export_tsx == True` |
| IT-RSZ-003 | `_run_conversion()` dispatch → `_convert_resize` pour Resize | `self._state.resource_type = "Resize"` | `threading.Thread` lancé avec `target=self._convert_resize` |

---

## Project File Tree

```
tools/src/asset_convertor/gui/
  app.py              # [MODIFY] toolbar split + _convert_resize + _build_secondary_resize
  state.py            # [MODIFY] ResourceType Literal + "Resize"
tools/tests/asset_convertor/gui/
  test_gui_state_v2.py  # [MODIFY] ajout TC-RSZ-U-001 à TC-RSZ-U-005
  test_resize_logic.py  # [NEW] TC-RSZ-U-010 à TC-RSZ-U-017
```

---

## Correction Log

| Date | Issue | Fix | Author |
|------|-------|-----|--------|
| 2026-06-06 | F-COLNUM-01 — Mismatch diagramme/code (col 4 vs col 5 spacer) | Diagramme mis à jour : col 5 = spacer weight, col 6 = Convertir. Commentaire code corrigé. | Adversarial review |
| 2026-06-06 | F-LABEL-BY-TYPE-01 — `_LABEL_BY_TYPE` sans consommateur | Supprimé du snippet. Remplacé par un commentaire YAGNI avec formule on-demand. | Adversarial review |
| 2026-06-06 | F-CROSS-DESEL-01 — `set("")` peut déclencher le callback | Guard `if label == "": return` ajouté dans `_on_tiled_type_change()` et `_on_mod_type_change()`. Comportement documenté dans § Désélection. | Adversarial review |
| 2026-06-06 | F-ASSERT-01 — `assert img is not None` supprimé par `-O` | Remplacé par `if img is None: ... return`. Message d'erreur explicite. | Adversarial review |
| 2026-06-06 | F-THREADING-01 — Threading non déclaré dans `_convert_resize()` | Note threading ajoutée en tête de section. Docstring et commentaire dispatch mis à jour. | Adversarial review |
| 2026-06-06 | F-VALIDATION-TIMING-01 — Pas de re-validation lors du changement de type | Section "Re-validation lors d'un changement de type" ajoutée dans § Validation. Snippet `_on_type_change_internal()`. Nouvelle ligne Error Handling Matrix. | Adversarial review |
| 2026-06-06 | F-EXPORT-OVERWRITE-01 — Écrasement silencieux non documenté | Ligne ajoutée dans Error Handling Matrix : convention app documentée. | Adversarial review |
| 2026-06-06 | /doc-update — Deep links stales | `_TYPE_LABEL_MAP` → `_TILED_TYPE_MAP`+`_MOD_TYPE_MAP`, `_on_type_change` → `_on_type_change_internal`. Ajout des liens `_validate_resize_dimensions`, `_convert_resize`, `_export_resize`, `test_resize_logic.py`. Snippet re-validation corrigé (`_validate_resize_dimensions` vs `_validate_dimensions`). | HARDEN /doc-update |
