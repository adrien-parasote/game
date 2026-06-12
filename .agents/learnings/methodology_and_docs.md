## 🔧 Spec, Agent & Workflow Documentation

### L-SPEC-001 · 2026-04-28 · U · Minor Rework
**Define procedural assets by boundary values**

In implementation specs, describe generated geometry/textures by **Start, End, Step/Falloff** values — not prose. Eliminates ambiguity in generation loops (e.g., center-to-edge alpha gradients).

---

### A-AGENT-001 · 2026-04-28 · U · Major Rework
**Blind file overwrites with stale context**

Replacing large file chunks from outdated memory destroys working code (I18n, UI scaling, etc.) and starts endless `AttributeError` loops.

✅ Always `view_file` before editing. Use targeted `multi_replace_file_content`. On accidental corruption: `git checkout -- <file>` immediately.

---

### A-AGENT-002 · 2026-04-28 · U · Major Rework
**Skipping Stream Coding pipeline stages**

Jumping to BUILD without SPEC, or skipping VERIFY/HARDEN, generates vibe-coded output that diverges from spec and requires expensive rework.

✅ Never write implementation code without RED tests (TDD Gate). Never commit without `/learn-eval` + `/doc-update`.

---

### A-SPEC-001 · 2026-04-28 · U · Minor Rework
**Ambiguous spritesheet definitions**

Describing an asset as "animated" without stating grid layout (rows × columns) and frame mapping causes incorrect slicing (4×1 instead of 4×8).

✅ Always specify: `rows=4, cols=8, frame_duration=0.1s, animation_row={state: row_index}`.

---

### A-SPEC-002 · 2026-04-30 · P · Spec Wrong
**POSITION_TO_DIR inversé dans la spec vs code**

`interactive-objects.md` documentait `0=Up, 1=Right, 2=Left, 3=Down`. Le code (`InteractiveEntity.POSITION_TO_DIR`) implémentait `0=Down, 1=Left, 2=Right, 3=Up`. La spec et le code divergeaient depuis la création du module.

**Cause :** Le mapping a été défini dans le code avant d'être documenté. La spec a été écrite de mémoire, inversée.

**Règle :** Pour tout mapping constant (enum-like), toujours extraire la valeur depuis le code source avec `grep` avant de documenter. Ne jamais documenter de mémoire.

```bash
# ✅ vérifier avant de documenter
grep -n "POSITION_TO_DIR" src/entities/interactive.py
```

**Scope :** Project-specific mais le pattern est universel — voir L-SPEC-001.

**Evidence :** `interactive-objects.md` ligne 24 corrigée. Confirmé avec `InteractiveEntity.POSITION_TO_DIR` dans `interactive.py`.

---

### A-AGENT-003 · 2026-05-01 · U · Spec Wrong
**Verify @property vs method before calling**

Generated `self.time_system.world_time()` with parentheses, but `world_time` is a `@property`. Runtime crash: `'WorldTime' object is not callable`.

```python
# ❌ Assumes world_time is a method
wt = self.time_system.world_time()

# ✅ Verify first — it's a property
wt = self.time_system.world_time
```

**Rule:** Before calling any attribute from an external module, verify whether it's a property or method:
```bash
grep -n "def world_time\|world_time = " src/engine/time_system.py
```

**Scope:** Universal — Python @property vs method mixups cause `TypeError: 'X' object is not callable`.
**Evidence:** Runtime crash on `_compute_slant()` first call. Fixed by removing parentheses.

---

### L-DOC-001 · 2026-05-03 · U · Perfect
**Relative paths in spec deep links for portability**

Absolute `file:///Users/username/...` paths in spec deep links break on every machine change or team handoff. Relative paths from the spec's directory work universally.

```markdown
# ❌ Machine-specific — breaks on any other system
[inventory.py L21](../../src/engine/inventory_system.py#L21)

# ✅ Relative from docs/game/specs/ — portable
[inventory.py L21](../../src/engine/inventory_system.py#L21)
```

**Convention from docs/game/specs/:**
- `../../src/` → source files
- `../../tests/` → test files
- `./` → other spec files in docs/game/specs/
- `../` → other docs/ files

**Evidence:** 87 links converted in 13 spec files. Script: `re.sub(r'file:///Users/[^/]+/Documents/perso/game/', '../../', content)`. commit `a7be023`.

---

### L-DOC-002 · 2026-05-03 · U · Minor Rework
**Two-pass cleaning required for specs: placeholder removal then deep link fix**

Spec generation often creates a full "Linked Test Functions" table stub AND retains the generic placeholder at the bottom. A single-pass cleanup missed the bare `tests/` paths inside backticks (which are not Markdown links and thus not caught by link-specific regex).

**Two-pass strategy:**
1. Remove generic placeholder blocks (`| TC-001 | [Component] |...`)
2. Separately fix bare paths in backticks inside tables: `` `tests/foo` `` → `` `../../tests/foo` ``

```python
# Pass 1 — structural placeholders
content = content.replace(PLACEHOLDER_BLOCK, '')

# Pass 2 — bare paths in backticks (Linked Test Functions tables)
content = re.sub(r'`(tests/)', r'`../../\1', content)
```

**Evidence:** 54 additional paths corrected across 11 files after pass 1 was believed complete. commit `fb4b039`.

---

### L-DOC-003 · 2026-05-03 · U · Perfect
**Automated spec audit script catches 100% of formatting violations**

A Python audit script checking (1) absolute paths, (2) bare `tests/` in backticks, (3) missing linked-file existence, (4) function name existence, (5) line number accuracy — caught every issue in one run. Zero false negatives when function names verified via `grep -n def func tests/file.py`.

**Pattern to reproduce:**
```python
# For each spec, in the Linked Test Functions table:
for tc_id, func_name, file_ref in re.findall(
    r'\|\s*([\w-]+)\s*\|\s*`(test_[^`]+)`\s*\|\s*`(\.\./\.\./[^`]+)`',
    content
):
    # verify file exists, verify function exists, verify line number
```

**Evidence:** 0 errors, 0 warnings final audit run. All 492 test functions validated. commit `fb4b039`.

---

### A-DOC-001 · 2026-05-03 · U · Minor Rework
**"Linked Test Functions" added in multiple passes creates inconsistent path formats**

When "Linked Test Functions" sections are added iteratively (some in session N, some in session N+1), the first batch uses one path convention (`tests/`) and the second uses another (`../../tests/`). The audit script cannot catch this until both conventions co-exist in the same file.

**Rule:** When adding "Linked Test Functions" to any spec, immediately run the audit script:
```bash
python3 audit_spec_links.py  # verifies all paths are ../../ relative
```
Never add linked test tables without running the audit immediately after.

**Evidence:** 5 spec files had inconsistent path formats discovered only in a second pass. 54 paths corrected.

---

*Last updated: 2026-05-07 — documentation urbanization session: L-DOC-001..L-DOC-003, A-DOC-001. L-ARCH-008 migré vers `game_engine.md` (audit 2026-05-15).*

---

> **Note :** `L-ARCH-008` a été migré vers `.agents/learnings/game_engine.md` le 2026-05-15 (audit documentation).
> Cause : ce learning concerne le pattern d'architecture `SomeManager(game: Any)`, domaine `game_engine` et non `methodology_and_docs`.
> Voir directement `game_engine.md#L-ARCH-008` pour le contenu.

---

### L-DOC-004 · 2026-05-07 · P · Minor Rework
**Suppression en cascade de variables interdépendantes**

Supprimer une variable non utilisée peut rendre sa dépendante elle-même orpheline. Dans `entity_factory.py`, supprimer `e_pos` a rendu `half_tile` orphelin à son tour.

**Règle :** Avant de supprimer une variable locale, scanner toutes les variables calculées en amont. Utiliser `ruff check --fix --unsafe-fixes` pour les suppressions en cascade — ruff résout la chaîne complète en une passe.

**Evidence :** `entity_factory.py::spawn_entities()` — 2 passes de lint nécessaires. Résolu en une fois avec `ruff --fix --unsafe-fixes`.

**Scope :** Universal (Python)

---

### L-DOC-005 · 2026-05-07 · U · Major Rework
**Learnings écrits dans le mauvais fichier domaine = duplicatas cachés**

`map_rendering.md` contenait `L-UI-007`, `L-UI-008` (→ `ui.md`) et `A-AUDIO-001` (→ `audio_engine.md`) — copiés par un agent sans vérifier le domaine cible.

**Détection :** En HARDEN, toujours `grep -rn "L-ID" .agents/learnings/` avant d'ajouter — si présent dans 2 fichiers → supprimer le duplicata.

**Règle :** Un learning = un seul fichier domaine. `map_rendering.md` = uniquement les patterns map/rendering pipeline.

**Evidence :** `map_rendering.md` nettoyé de 3 learnings hors-domaine en session 2026-05-07.

**Scope :** Project-specific

---

*Last updated: 2026-05-13 — HARDEN session: L-SPEC-002 added.*

---

### L-SPEC-002 · 2026-05-13 · U · Perfect
**Adversarial Review with Epistemic Pre-scan hardens specifications**

Conducting an epistemic pre-scan (checking cross-doc consistency, externally verifiable claims, hidden assumptions) followed by an adversarial review (hostile critic stress-test) identifies and resolves logical gaps that would otherwise cause implementation failure.

**Pattern:**
1. Run epistemic pre-scan to find unsupported claims.
2. Insert mandatory assumption markers (`> [assumption: ...]`) to track unverified claims for the BUILD phase.
3. Run adversarial review to find missing failure states.

**Evidence:** 31 engine specifications reached 10/10 AI-readiness score by systematically resolving logical contradictions and missing failure states before writing any code.

---

### A-DOC-002 · 2026-05-14 · U · Minor Rework
**Overly Strict Verification Tooling Produces False Positives**

Heuristic static analysis scripts (like `verify.py`) can throw false positives. For example:
- `P8_SpecConformance` checking for undocumented symbols might flag standard library exceptions (e.g., `AttributeError`, `FileNotFoundError`).
- `P9_TestQuality` might flag tests as lacking behavioral delegations if the test relies entirely on dependency injection or `unittest.mock.patch` for Pygame objects.
- `P0_Security` checking for SQL injection might flag simple format logs containing words like `"updated"` (which contains `"update"` case-insensitively) in an f-string context.

**Anti-pattern:** The agent plowing ahead to modify correct code or specs in a futile attempt to "fix" false positives reported by automated checks.
**Fix:** Use the "Radical Honesty" and "Push Back" behaviors. If a verification step fails due to a verifiable false positive, do not modify the codebase. Alternatively, if a simple rephrasing bypasses the checker without logic shift (e.g., renaming `"updated"` to `"refreshed"` in non-user logs), perform it to keep verification fully clean.
**Evidence:** `verify.py` flagged `test_save_menu.py` for "no delegation", and flagged `AttributeError` as an undocumented export. In 2026-05-31 refactoring, `P0_Security` flagged an f-string log containing `"Preview updated..."` as a SQL f-string. Fixed by renaming log to `"Preview refreshed..."` and sorted imports via Ruff, achieving 100% green verification.

---

### L-DOC-008 · 2026-05-15 · U · Perfect
**Audit documentaire : grep avant de supposer l'étendue d'une référence**

Lors d'un audit doc, on suppose souvent que les références problématiques sont localisées aux fichiers identifiés manuellement. En réalité, un header auto-généré (`> **Design tokens** – see [design-tokens.md]`) peut exister dans **N >> 3 fichiers** à cause d'un template partagé.

```bash
# ❌ Corriger manuellement 3 fichiers identifiés → 28 autres restent cassés
# ✅ Toujours grep d'abord pour connaître l'étendue réelle
grep -rl "design-tokens.md" docs/ .agents/
# → 31 fichiers identifiés d'un coup
# Puis supprimer en masse :
for f in docs/game/specs/*.md; do sed -i '' '1{/design-tokens/d;}' "$f"; done
```

**Règle :** Avant de corriger manuellement N occurrences d'un pattern problématique, lancer `grep -rl "pattern" .` pour connaître l'étendue réelle. Si N > 5 → script sed one-liner au lieu de corrections manuelles.

**Evidence :** `design-tokens.md` référencé dans 31 fichiers (vs 3 identifiés manuellement). Nettoyage en 1 commande. commit `b312f8e`.

---

### L-DOC-006 · 2026-05-15 · P · Minor Rework
**Placeholder CSS dans un projet Python : suppression > transformation**

Un fichier `design-tokens.md` contenant des tokens CSS (`--primary: #3A7BD5`, `Inter, sans-serif`) dans un projet pygame-CE est **activement trompeur** pour les agents IA — ils peuvent inférer que le projet est un projet web.

**Anti-pattern :** Garder un fichier "placeholder" avec contenu générique en se disant "on le remplira plus tard". Un placeholder vide ou générique pollue le corpus documentaire sans valeur.

**Règle :** Supprimer immédiatement tout fichier dont le contenu est générique ou hors-domaine. Documenter la suppression dans `learnings.md` (Note historique). Si le besoin réel existe → créer un fichier avec du vrai contenu projet, pas un template.

**Evidence :** `design-tokens.md` référencé dans 31 spec headers générait une ambiguïté CSS/pygame. Suppression + nettoyage = zéro impact fonctionnel, clarté maximale. commit `b312f8e`.

---

### L-DOC-007 · 2026-05-15 · U · Perfect
**Script relocation: grep for all hardcoded call sites across docs and config**

When moving scripts to subdirectories (e.g. `scripts/` -> `scripts/calibration/`), assuming only `ARCHITECTURE.md` needs updates is an anti-pattern. Hardcoded paths often exist in `docs/game/specs/`, `README.md`, and metadata-generating scripts (e.g. `tc_report.py`).

**Pattern:**
1. Move files.
2. `grep -rn "old_script_name.py" .` across the entire project (not just `docs/`).
3. Update `ARCHITECTURE.md` and any identified specs.
4. Verify by running the script from its new location if applicable.

**Evidence:** Relocation of `calibrate_halos.py` and `process_banners.py` identified 4 hidden references in `docs/game/specs/game-flow-spec.md` and 1 in `tc_report.py` that would have otherwise broken traceability reporting.

---

### L-STATIC-003 · 2026-05-15 · U · Perfect
**Automated dead code cleanup: `ruff --fix --select F401,F811`**

Using `ruff check . --select F401,F811 --fix` safely removes unused imports and redefinitions across the entire project in seconds. This is significantly faster and more reliable than manual cleanup, especially in large test suites with duplicate mocks or UI components with complex dependency chains.

**Pattern:**
1. Identify linting issues via `verify.py` or `ruff check .`.
2. Run `ruff check . --select F401,F811 --fix`.
3. Verify remaining issues.

**Evidence:** 34 dead code/import violations in `src/ui/save_menu.py` and `tests/` resolved in 3s with zero regressions in the 777-test suite.

---

### L-DOC-009 · 2026-05-15 · U · Perfect
**Documentation Urbanization: The Discovery-Audit-Fix cycle**

Regularly running link checkers and TC ID prefix validation prevents documentation drift from the source of truth. Moving archived strategy blueprints to `docs/archive/` while keeping their decision logic in ADRs preserves history without cluttering implementation specs.

**Pattern:**
1. **Discovery**: Use scripts (`check_links.py`) to find broken references.
2. **Consolidation**: Move completed strategic blueprints to `docs/archive/` if they are fully captured in ADRs.
3. **Hardening**: Fix relative path depth (`../../`) and prefix generic IDs (`TC-` -> `DOM-U-`) to ensure total AI-readiness.

**Evidence:** 8 broken links fixed, 24 TC IDs urbanized, and 1 archived strategy moved to `docs/archive/` in the 2026-05-15 urbanization session.

---

### L-DOC-010 · 2026-05-15 · U · Perfect
**Spec Conformance for Python: Class member detection**

Automated spec conformance tools often only scan top-level `def` and `class` exports in Python, missing class members like `Settings.MAP_SIZE` or `GameState.TITLE`. This causes false "missing in code" findings when these symbols are documented in backticks.

**Fix:** Enhance the conformance scanner to:
1.  Detect indented `def`, `class`, and SCREAMING_CASE assignments (`UPPER_CASE = ...`) as internal exports.
2.  Support optional `cls.` or `self.` prefixes in assignments.
3.  Allow SCREAMING_CASE symbols in specs if they are part of a dotted identifier (preventing env var noise while allowing member refs).

**Evidence:** `spec_conformance.py` logic updated to detect indented constants and dotted identifiers. 5 false positive divergences in `game-flow-spec.md` resolved.

---

*Last updated: 2026-05-15 — L-DOC-008 (ID fix), L-DOC-009 urbanization workflow, L-DOC-010 conformance fix.*

---

### A-AGENT-004 · 2026-05-17 · U · Minor Rework
**Proposer `sheet_cols`/`sheet_rows` sans vérifier les dimensions réelles de la sheet**

Premier fix du bug `05-guards.png` : proposé `sheet_cols=2, sheet_rows=12` (12 lignes) sans avoir vérifié que l'image fait 64×384px avec 4 lignes de 96px. L'utilisateur a dû intervenir pour corriger `sheet_rows=4`.

**Diagnostic manqué :**
```bash
# ✅ TOUJOURS exécuter avant de proposer des cols/rows
python3 -c "
import pygame; pygame.init(); pygame.display.set_mode((1,1))
s = pygame.image.load('assets/images/characters/05-guards.png')
w, h = s.get_size()
print(f'Size: {w}x{h}')
print(f'-> cols=2: {w//2}x{h//4} per frame (4 rows)')
print(f'-> cols=4: {w//4}x{h//4} per frame (4 rows)')
"
# Output: Size: 64x384 -> cols=2: 32x96 ✅  cols=4: 16x96 ❌
```

**Règle :** Avant de proposer un fix sur les paramètres `load_grid(cols, rows)` d'un NPC, TOUJOURS :
1. Charger l'image avec `pygame.image.load` et afficher ses dimensions réelles
2. Calculer `frame_w = sheet_w // cols` et `frame_h = sheet_h // rows` pour chaque hypothèse
3. Vérifier visuellement que `frame_w` est logique (≥ 16px, multiple de 8)

**Lien avec L-SPRITE-001 :** Même anti-pattern racine — assumer le layout d'une spritesheet sans mesurer. L-SPRITE-001 s'applique à `frame_height`, A-AGENT-004 à `cols/rows`.

**Evidence :** First fix `sheet_rows=12` → frames 32×32px incorrects. Human enforcement requis. Corrigé en `sheet_rows=4` → frames 32×96px. commit `9fac11b`.

---

*Last updated: 2026-05-17 — A-AGENT-004 (mesurer les dimensions sprite avant de proposer cols/rows).*

---

### A-DOC-003 · 2026-05-22 · U · Minor Rework
**Contrat de retour d'une méthode partagée non documenté dans la spec → drift cross-spec détecté seulement en HARDEN**

Quand une méthode est appelée depuis **plusieurs specs** (ex: `draw_foreground()` dans `camera-rendering.md` ET `intra-map-teleport.md §4.6`), changer son type de retour (`bool` → `list[tuple]`) sans documenter le nouveau contrat dans TOUTES les specs consommatrices crée un drift croisé silencieux. Ici, `intra-map-teleport.md §4.6` et `§9.2` décrivaient encore l'ancien `return False` 6 semaines après la mise à jour.

**Quand ça se produit :**
- Méthode utilisée comme signal entre 2 systèmes (render + teleport walk guard)
- La spec primaire (`camera-rendering.md`) est mise à jour en SPEC phase
- La spec secondaire (`intra-map-teleport.md`) est oubliée car elle est dans un autre domaine

**Fix — à ajouter en SPEC phase, section "Cross-Spec Contracts" :**
```markdown
### Tracked Interface Changes
| Method | Old contract | New contract | Specs to update |
|--------|-------------|-------------|-----------------|
| `draw_foreground()` | `bool` | `list[tuple[Rect,int]]` | `intra-map-teleport.md §4.6, §9.2` |
```

**Règle :** Pour tout changement de signature ou type de retour d'une méthode partagée, lancer :
```bash
grep -rn "draw_foreground\|method_name" docs/game/specs/
# → chaque fichier listé = spec à mettre à jour
```

**Evidence :** `intra-map-teleport.md §4.6` et `§9.2` corrigés en HARDEN/doc-update (dérive ~6 semaines). La SPEC phase ne l'avait pas identifié car les specs ne s'étaient pas cross-référencées explicitement sur le contrat de retour.

**Scope :** Universal

---

### A-TEST-014 · 2026-05-22 · U · Minor Rework
**Tests legacy qui assertent le type de retour exact d'une méthode → cassent silencieusement sur changement de contrat**

Quand `draw_foreground()` retournait `bool`, des tests dans `test_render_order.py` écrivaient `assert result is True` / `assert result is False`. Après changement vers `list[tuple]`, ces tests ont cassé (2 FAIL sur 971). Le contenu testé (blit de occluded_image ou non) était correct — seule l'assertion sur le return type était stale.

```python
# ❌ Assertion sur le type exact (fragile au refactoring de contrat)
result = rm.draw_foreground()
assert result is True   # → échoue si contrat change de bool à list

# ✅ Assertion sur le comportement (robuste)
result = rm.draw_foreground()
assert isinstance(result, list) and len(result) > 0  # contrat: non-vide = occlusion active
assert len(occluded_blits) == 1                       # comportement: blit occluded_image
```

**Règle :** Quand une méthode change de type de retour, exécuter :
```bash
grep -rn "assert.*method_name\|result is True\|result is False" tests/
# → chaque match = test à adapter au nouveau contrat
```

Ne pas limiter la recherche au fichier de test direct — les tests de régression cross-domaine (ici `test_render_order.py` pour une méthode de `render_manager.py`) sont les plus exposés.

**Evidence :** 2 tests (`test_render_order.py::TestOcclusionSkippedDuringWalk`) — cassés lors du passage `bool→list`. Adaptés en VERIFY. 971/971 verts.

**Scope :** Universal

---

### A-DOC-004 · 2026-05-22 · U · Methodology Gap
**Créer une spec standalone pour un sous-système d'un module existant → doublon doc silencieux**

Lors de la SPEC phase du cycle "Partial Sprite Occlusion", `partial-sprite-occlusion.md` a été créé comme fichier indépendant alors que toute la logique vit dans `RenderManager` — déjà documenté dans `camera-rendering.md`. Résultat : deux fichiers décrivant le même système pendant 2 sessions, avec risque croissant de divergence. Seule une question de l'utilisateur a déclenché la correction.

**Signal d'alerte :** Si le nouveau fichier spec décrit uniquement des méthodes/comportements d'un module déjà couvert par une spec existante, c'est un sous-système — pas un système indépendant.

**Règle — décision SPEC phase :**
```
SPEC STANDALONE si :
  - La feature touche ≥ 2 modules distincts (ex: intra-map-teleport → player + map + camera)
  - La feature introduit un nouveau module (ex: DialogueManager)
  - La feature est suffisamment grande pour dépasser 1/3 de la spec existante

SECTION DANS SPEC EXISTANTE si :
  - La feature est entièrement implémentée dans un module déjà spécifié
  - Les nouvelles méthodes s'ajoutent au même fichier source
  - Exemples : partial occlusion → camera-rendering.md §4.3, bridge physics → entities-system.md §5
```

**Question à se poser en SPEC :** "Dans quel fichier source vit 100% de l'implémentation ?" → C'est la spec cible.

**Evidence :** `partial-sprite-occlusion.md` (447L) existait en doublon de `camera-rendering.md` pendant 2 sessions. Fusion en 1 commit `87c8b55`. Human enforcement requis.

**Scope :** Universal

---

### A-DOC-005 · 2026-05-22 · U · Perfect
**`grep -rn "filename" docs/ .agents/` avant tout `git rm` d'un fichier de documentation**

Avant de supprimer un fichier spec, blueprint, ou doc, toujours vérifier qu'aucun autre fichier ne le référence. Un lien cassé dans `00_MASTER.md`, un ADR, ou une autre spec passe inaperçu jusqu'à ce qu'un agent IA charge le mauvais chemin.

```bash
# ✅ Pattern systématique avant git rm d'un fichier doc
grep -rn "partial-sprite-occlusion" docs/ .agents/ scripts/
# Si 0 résultat → suppression safe
# Si N résultats → mettre à jour chaque référence avant de supprimer
git rm docs/game/specs/partial-sprite-occlusion.md
```

**Règle :** La commande grep doit cibler `docs/`, `.agents/`, et `scripts/` (pas seulement `docs/game/specs/`) — les scripts TC report ou les learnings peuvent aussi pointer vers des specs.

**Evidence :** `partial-sprite-occlusion.md` supprimé proprement — grep = 0 résultats, zéro lien cassé. Distinct de L-DOC-007 (qui concerne la relocation de scripts, pas la suppression de specs).

**Scope :** Universal

---

### A-SPEC-003 · 2026-05-22 · U · Minor Rework
**Sur-génération de spécifications et d'ADR temporaires menant à une dette documentaire et des suppressions accidentelles**

Créer un fichier de spécification ou d'ADR indépendant pour chaque micro-optimisation de performance (ex : un ADR par règle F1, F2, F3, F4) ou chaque cycle de révision produit un éparpillement documentaire extrême. Cela engendre des risques de confusion pour l'agent (références fantômes, corpus saturé) et pousse le développeur à faire des suppressions massives au cours desquelles des blueprints stratégiques indispensables (ex : `docs/game/strategic/*.md`) sont accidentellement supprimés.

**Anti-pattern :** Éparpiller la conception technique d'une même feature sur 5+ fichiers d'ADR ou de brouillons au lieu de centraliser l'implémentation dans une spécification technique unique.

**Fix :**
1. Maintenir un seul fichier de spécification par module ou feature active (ex : `camera-rendering.md`).
2. Consolider les règles connexes (ex : optimisations F1-F4) sous forme de sections claires au lieu de fichiers multiples.
3. Supprimer les fichiers de travail temporaires immédiatement après leur validation fonctionnelle.
4. **Règle absolue (Override d'intégration) :** Tous les documents de conception (Specs, ADRs, Blueprints) doivent résider dans le workspace du projet (ex : `docs/game/strategic/`), tandis que seuls les artifacts de conversation éphémères (`task.md`, `walkthrough.md`) restent dans le répertoire Antigravity.

**Evidence :** Suppression de 7 brouillons d'ADR-PERF et de spec-gate temporaires. Restauration via git de 3 blueprints stratégiques accidentellement supprimés dans `docs/game/strategic/`. Urbanisation réussie avec centralisation sur les codemaps.

---

### L-AGENT-005 · 2026-05-27 · U · Perfect
**Pattern `str(Path(x) / y)` pour la migration `os.path.join` → `pathlib` sans rework**

Migrer `os.path.join(a, b, c)` vers `str(Path(a) / b / c)` au site d'appel est la stratégie minimale-risk pour une codebase qui passe des `str` aux APIs existantes (pygame, json, etc.). Conserver `os` pour `os.path.exists`, `os.listdir`, `os.makedirs` — uniquement remplacer les constructions de chemin.

```python
# ❌ os.path.join — verbeux, pas chainable
path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "images", "sprites", name)
path = os.path.normpath(path)

# ✅ pathlib — lisible, chainable, .resolve() = normpath + abspath
path = str((Path(__file__).parent / ".." / ".." / "assets" / "images" / "sprites" / name).resolve())

# ✅ Pour les chemins relatifs simples (pas __file__)
path = str(Path("assets") / "audio" / "bgm")
```

**Règle :** Ne pas migrer `os.path.exists`, `os.listdir`, `os.makedirs` — ils acceptent déjà les `Path`. Garder `os` importé dans les fichiers qui en ont encore besoin. Retirer `import os` uniquement si 0 usage `os.*` résiduel.

**Résultats :** 28 fichiers migrés, 55 occurrences supprimées, pyright: 0 errors, pytest: 1094/1094 — zéro régression.

**Evidence :** Steps 1-11 remediation cycle `remediation_03_modernization.md`. 2026-05-27.

---

### A-AGENT-005 · 2026-05-27 · U · Minor Rework
**`multi_replace_file_content` échoue sur lignes identiques sans `AllowMultiple=true`**

Quand deux lignes identiques existent dans un fichier (ex: `path = os.path.join(self.sfx_dir, file)` à deux endroits différents), le chunk `multi_replace_file_content` avec un seul chunk renvoie une erreur silencieuse. La ligne n'est pas remplacée mais le tool ne lève pas d'exception bloquante.

```python
# ❌ Échoue si la target_content apparaît 2× dans le fichier
multi_replace_file_content(chunks=[{"TargetContent": "path = os.path.join(self.sfx_dir, file)", ...}])
# → "target content not found in specified range and not unique in the file"

# ✅ Option 1 : AllowMultiple=true (si les 2 doivent être remplacées identiquement)
replace_file_content(AllowMultiple=True, TargetContent="...", ReplacementContent="...")

# ✅ Option 2 : Deux chunks avec des ranges distincts (StartLine/EndLine)
multi_replace_file_content(chunks=[
    {"StartLine": 126, "EndLine": 126, "TargetContent": "...", ...},
    {"StartLine": 137, "EndLine": 137, "TargetContent": "...", ...},
])
```

**Règle :** Avant tout chunk de remplacement, vérifier l'unicité : `grep -c "pattern" file`. Si count > 1 dans le range → utiliser `AllowMultiple=True` ou des ranges distincts.

**Evidence :** `save_manager.py` — 2 lignes identiques `os.path.join(self._saves_dir, f"slot_{slot_id}_thumb.png")`. Résolu avec `AllowMultiple=True` après 2 tentatives échouées. 2026-05-27.

---

*Last updated: 2026-05-27 — L-AGENT-005 pathlib migration pattern, A-AGENT-005 multi_replace identical lines.*

---

### A-SPEC-004 · 2026-05-27 · U · Minor Rework
**i18n fallback string grep misses method-argument call sites — spec gap in FR→EN translation tasks**

A spec for a FR→EN translation pass identified FR strings via `grep -rn "[àâæçéèêëîïôœùûüÿ]"` on the codebase pre-spec. This correctly found `_BUTTON_DEFAULTS`, docstrings, and log strings — but **missed 5 additional FR strings** embedded as positional arguments in method calls, not in named constant assignments:

```python
# NOT caught by accent grep — these were method arguments, not constants
self._i18n.get("save_menu.title_load", "Charger une partie")   # title_screen.py line 74
self._i18n.get("pause_menu.saved_success", "Partie sauvegardée !")  # pause_screen.py line 260
self._i18n.get("save_menu.level", "Niveau: {level}")           # save_slot.py line 98
```

**Root cause:** Spec grep scope was: "files with accented characters" → "what constant does that character live in?" — it didn't follow the i18n pattern `self._i18n.get("key", "FR_DEFAULT")` systematically across ALL call sites.

**Fix — Add to any FR→EN spec:**
```bash
# ✅ Two complementary greps required for complete FR scan:
# 1. Accent scan (catches docstrings, comments, raw strings)
grep -rn "[àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ]" src/ --include="*.py"

# 2. i18n fallback scan (catches method-argument defaults that may not have accents)
grep -rn 'i18n.get(' src/ --include="*.py" | grep -v "#"
# → manually review each default="" argument for FR text
```

**Also:** Explicitly mark proper nouns in the spec's exclusion list with rationale (e.g., game titles that must stay in the original language).

**Evidence:** 5 FR strings found during BUILD (not in spec). Required BUILD addendum to close divergence. 2026-05-27 — code-quality-constants-i18n spec.

**Scope:** Universal

---

### L-DOC-011 · 2026-05-28 · U · Perfect
**Reorganizing developmental scripts in subfolders with mirrored test suites and auto-traceability**

When reorganizing miscellaneous utility scripts into clean category folders (e.g. `scripts/dev/` and `scripts/build/`), always reorganize the corresponding test suite with a mirrored subfolder structure (e.g. `tests/scripts/build/test_release.py`). This guarantees test isolation, clean structure, and continuous validation.

**Pattern:**
1. **Parent Path Resolution**: Update relative path walk-ups inside the scripts (`os.path.dirname(__file__)` plus additional `..` levels) to preserve workspace root detection.
2. **Test Mirroring**: Move tests to exact mirrored paths under `tests/scripts/<category>/` to satisfy automated test location expectations.
3. **Lock Sync**: Update path mappings and compute SHA-256 hashes in `.tdd_lock` to prevent TDD sequence validation failures.
4. **Auto-Traceability Matrix**: Rather than manually updating test paths in documentation, run the relocated traceability generator (e.g. `python3 scripts/dev/tc_report.py --markdown`) to automatically update `docs/traceability.md` references.

**Evidence:** Relocation of 5 root utility scripts and tests to `scripts/dev/`, `scripts/build/`, and `tests/scripts/build/` with a perfect 324/324 test traceability match and 100% `verify.py` success.

**Scope:** Universal

---

### A-AGENT-006 · 2026-05-28 · U · Minor Rework
**Running directory-level batch scripts for single-file operations**

Launching a utility script designed for directory-level batch processing (e.g., `flat_wall_to_diagonal.py` with `--input-dir`) directly on a shared folder containing multiple files will process all files, violating the user's intent to target a single file and wasting performance or corrupting existing outputs.

**Anti-pattern:**
Running batch processing scripts directly on a directory with multiple files when only one or a subset of files needs to be processed.

**Fix:**
If the script does not support single-file targeting, dynamically isolate the target file(s) by copying them into a temporary input directory, execute the script targeting that temporary directory, and clean up the temporary directory afterward.

**Evidence:** Running `flat_wall_to_diagonal.py` on the shared `scripts/input` folder processed `asset1.png` and `asset2.png` along with `asset3.png`. Restricting execution to `asset3.png` was successfully achieved by creating `scripts/input_single/` containing only `asset3.png`.

---

*Last updated: 2026-05-28 — added L-DOC-011 scripts folder urbanization pattern, A-AGENT-006 directory-level batch isolation.*

---

### L-AGENT-006 · 2026-05-31 · U · Perfect
**Parallel subagent orchestration with independent module boundaries produces zero-conflict builds**

When building a multi-module system (Asset Convertor V1→V2→V3), defining strict module boundaries in the spec enables parallel subagent execution with zero merge conflicts. Each subagent gets a self-contained scope: its own source file(s), its own test file(s), and explicit dependency declarations.

**Pattern — in the spec, define for each build step:**
1. **Input files** — what already exists that this step reads (read-only)
2. **Output files** — what this step creates (exclusive write)
3. **Wait-for** — which other steps must complete first (dependency DAG)

```yaml
# Example from Asset Convertor V3 orchestration:
Step 1 (minimap):   outputs=[core/minimap.py, test_minimap.py]    wait=[]
Step 2 (state):     outputs=[gui/state.py, test_gui_state.py]      wait=[]
Step 3 (preview):   outputs=[gui/preview.py, test_gui_preview.py]  wait=[]
Step 4 (canvas):    outputs=[gui/canvas.py, test_canvas.py]         wait=[Step1]
Step 5 (app+cli):   outputs=[gui/app.py, gui/pipeline.py, cli.py]  wait=[Step1,2,3,4]
```

**Evidence:** 5 subagents ran in parallel (2 for V2, 3 for V3). Steps 1-3 ran simultaneously with zero conflicts. 371 tests green on first full integration. Total wall-clock ~2h for what would be ~6h sequential.

---

### L-SPEC-003 · 2026-05-31 · U · Perfect
**Extract DPG-independent modules to enable testing without GUI context**

Separating framework-agnostic logic (state, preview conversion, canvas grid, generation pipeline) from DPG-specific rendering code enables full test coverage without needing a display or GPU context. The framework-dependent code (`app.py`) is the only file that imports `dearpygui`.

**Pattern — split into 3 layers:**
1. **Pure data** (testable, no imports): `state.py` (frozen dataclass), `canvas.py` (grid state + coord helpers)
2. **Pure computation** (testable, PIL/numpy only): `preview.py` (PIL→float32), `pipeline.py` (generation + export)
3. **Framework glue** (NOT unit-tested): `app.py` (DPG widgets, callbacks, textures)

```python
# ❌ Everything in app.py — untestable
import dearpygui.dearpygui as dpg
class App:
    def regenerate(self): ...  # Can't test without display

# ✅ Pipeline in separate module — fully testable
# gui/pipeline.py (no DPG imports)
def regenerate_tileset(state, presets): ...  # Pure computation
def do_export_autotile(state, tiles): ...   # Pure I/O
```

**Evidence:** 371 tests including 108 GUI-related tests (state, preview, canvas, integration) — all run in headless CI without `dearpygui` installed. `app.py` is the only untestable module.

---

### A-SPEC-005 · 2026-05-31 · U · Minor Rework
**GUI specs underestimate size and miss interactive features that emerge from real use**

The V3 GUI spec estimated `app.py` at ~300-400 lines. Reality: 881 lines in `app.py` alone, 1,365 total across 5 GUI files. More critically, the spec was designed from a "CLI with sliders" mental model and missed 4 features that only became obvious when the user actually interacted with the GUI:

| Feature missed | Why it was missed | User intervention |
|----------------|-------------------|-------------------|
| Color pickers (4 pickers) | Spec assumed palette from YAML only | User: "la partie de selection des couleurs" |
| History panel with undo | Spec assumed "regenerate = enough" | User: "l'historique" |
| macOS dark theme | Spec said "default DPG theme" | User: "standard UI/UX de mac os" |
| French UI labels | Spec was English | User: "le text est toujours en anglais" |

**Anti-pattern:** Writing a GUI spec from a CLI developer's perspective — "I'll expose the same params as sliders" — without considering the interactive workflow the user will actually follow.

**Fix — add to GUI specs:**
1. **User workflow narrative**: Write "User opens app → adjusts X → sees Y → exports Z" as a first-class section
2. **Interaction patterns table**: List every feedback loop (param change → preview update, history undo, color override)
3. **Size estimate multiplier**: Apply 3× to initial line-count estimates for GUI specs (DPG callback boilerplate, theme code, layout groups)
4. **Localization section**: If the project has French UI elsewhere, spec must mandate French labels

**Evidence:** 6 user interventions on UI/UX features not in spec. `app.py` 2.5× estimated size. 4 features (F_HIST, F_COLOR, F_MACUI, F_LOG) added post-spec.

---

### L-ARCH-010 · 2026-05-31 · P · Minor Rework
**DPG `width=-1` (fluid sizing) only works on the LAST `child_window` in a horizontal group**

In Dear PyGui, when multiple `child_window` elements are in a `horizontal` group, `width=-1` (fill remaining space) only works correctly on the **rightmost** element. Placing it on a middle panel causes overlapping or zero-width rendering.

**Workaround — fixed+fluid layout:**
```python
# ❌ Doesn't work: middle panel with width=-1
with dpg.group(horizontal=True):
    dpg.add_child_window(width=280)   # left: config
    dpg.add_child_window(width=-1)    # center: BROKEN — DPG ignores this
    dpg.add_child_window(width=300)   # right: history

# ✅ Works: rightmost panel gets width=-1
with dpg.group(horizontal=True):
    dpg.add_child_window(width=280)   # left: config (fixed)
    dpg.add_child_window(width=max(canvas_w + 40, 620))  # center: calculated
    dpg.add_child_window(width=-1)    # right: fills remainder ✅
```

**Evidence:** Center panel was invisible (0px width) until the layout was restructured. User reported "la partie central n'est plus assez grand". Fixed by making history panel (rightmost) the fluid one.

---

### L-ARCH-011 · 2026-05-31 · U · Perfect
**Centralized leaf constants module for circular dependency prevention**

When refactoring a modular system with interdependent files, centralize all magic variables, sizes, presets, and matrices in a dedicated "leaf" constants module (e.g., `constants.py`) that contains **zero internal imports** from the package. This guarantees that any submodule can import parameters without any risk of circular dependency loops.

**Evidence:** Created `tools/asset_convertor/core/constants.py` and successfully migrated tile dimensions, preview layouts, noise levels, and Pygame/Dear PyGui color tokens from 7 different submodules. All 361 unit/integration tests passed cleanly on the first pass with zero circular imports.

---

### L-DOC-012 · 2026-05-31 · U · Perfect
**Ruff Pro-Max Configuration for Methodology Enforcement**

Activating the strict Ruff configuration (`"SIM", "PT", "RUF", "C90"`) instantly surfaced ~300 stylistic, formatting, and structural issues that previously went undetected. Aligning the static analyzer to the exact boundaries required by the specs (`max-statements = 50`) offloads the structural enforcement of the Stream Coding methodology from manual review loops directly into the pre-commit pipeline.

**Pattern:**
1. Add strictly aligned config: `[tool.ruff.lint.pylint] max-statements = 50`
2. Extend `select` to enforce simplicity and Pytest rules: `["SIM", "PT", "RUF", "C90"]`
3. Explicitly allow exceptions via `# noqa: PLR0915` only when thoroughly justified (e.g., UI theme definitions) instead of raising the global limit.

**Evidence:** Applied to monorepo urbanization on 2026-05-31. Caught 50+ lines violation in `theme.py` immediately. Caught >300 docstring ambiguous unicode characters (`×` vs `x`).

### L-DOC-013 · 2026-06-03 · U · Perfect
**Urbanisation de monorepo multi-domaines : Centralisation de l'infrastructure de build**

**Contexte :** Un monorepo contenant un domaine jeu (`game/`) et un domaine outillage (`tools/`), avec des `Makefile` et environnements virtuels séparés.
**Outcome :** La fragmentation de l'infrastructure de build crée de la friction (context switching, doublons de dépendances, scripts redondants). Bien que le code source et les tests des domaines doivent rester strictement isolés, l'infrastructure d'exécution et de tooling doit être unifiée.
**Pattern :** Déplacer le `Makefile` et le `requirements.txt` à la racine du monorepo. Utiliser un seul `venv` global. Exposer des commandes de build préfixées par domaine (e.g., `make run-game`, `make run-tools`, `make test-all`).

**Evidence :** Consolidation de 3 Makefiles et 2 venvs en une seule infrastructure racine. 1163/1163 tests passent avec une seule commande `make test` couvrant les deux domaines.

### A-AGENT-007 · 2026-06-04 · U · False Positives
- **Source:** game — Stream Coding Verify
- **Evidence:** `verify.py` run at root `.` caused `P8_SpecConformance` to skip (looked in `./docs` instead of `./tools/docs/specs`) and `P4_Tests` to fail trying to run `game/tests` when only `tools/` was modified.
- **Anti-pattern:** Running `verify.py` on the monorepo root without targeting the specific sub-project (`tools` vs `game`). This causes false positive test failures and falsely skipped spec checks.
- **Fix:** In a monorepo setup, run `verify.py` explicitly targeting the sub-project directory (e.g., `cd tools && verify.py .` or manual `pytest tools/` if root `pyproject.toml` forces a global context).

### A-SPEC-006 · 2026-06-11 · U · Major Rework
- **Source:** game — ADR-013-stair-climbing-alignment.md
- **Evidence:** Adversarial review caught 2 HIGH severity bugs before code generation: a ZeroDivisionError in a stated interpolation formula, and an AttributeError on a Pygame Group iteration.
- **Anti-pattern:** Writing specs with raw mathematical formulas (e.g. `dist / total`) without specifying zero guards, and referencing groups/collections with an assumption of homogeneity (e.g. "update `CameraGroup` to apply `sprite.offset`") when the collection can contain heterogeneous objects.
- **Fix:** When a spec contains a mathematical formula for interpolation or state, it MUST include the boundary guard (e.g., `if total > 0`). When a spec describes iterating a collection, it MUST specify safe attribute access (e.g., `getattr(sprite, 'prop', default)`) if the collection can contain objects without that property.

---

### L-AGENT-008 · 2026-06-12 · U · Perfect
**Parallel 3-agent BUILD for independent file-domain streams completes with zero conflicts**

When a BUILD task can be split into streams with zero shared-file overlap at the git level (e.g., code constants vs. test additions vs. doc urbanization), running 3 parallel subagents completes the work in under 6 minutes with no merge conflicts. The key constraint is **no two streams write to the same file**.

**Pattern:**
1. Identify independent streams by file domain (source files, test files, doc files).
2. Verify zero overlap: run `git diff --stat` mentally — no file appears in two streams.
3. Launch all streams simultaneously via `invoke_subagent` with distinct file lists.
4. Integrate sequentially only for the final commit.

```yaml
# Example split from 2026-06-12 audit BUILD:
Stream A (code):  src/engine/*.py, src/ui/*.py, src/entities/*.py  # NO overlap with B/C
Stream B (tests): tests/engine/*.py, tests/ui/*.py                  # NO overlap with A/C
Stream C (docs):  game/docs/specs/*.md, game/docs/strategic/*.md     # NO overlap with A/B
```

**Contrast with L-AGENT-006:** L-AGENT-006 describes module-boundary spec setup for complex multi-step builds. This pattern is simpler: when the task is a cleanup pass across independent domains, no dependency DAG is needed — just verify zero file overlap and launch.

**Evidence:** 3-stream parallel BUILD (code/tests/docs) for 2026-06-12 audit. Zero conflicts. All streams completed in <6 minutes wall-clock vs. estimated 18+ minutes sequential.

---

### A-AGENT-008 · 2026-06-12 · U · Minor Rework
**Subagent audit scoped to subdirectories misses root-level `src/*.py` files**

When delegating a code audit (FR comments, magic constants, etc.) to a subagent with scope `engine/, entities/, graphics/, map/, ui/`, root-level source files (`src/config.py`, `src/main.py`) are silently skipped. These files can contain the same issues the audit targets.

**Anti-pattern:**
```bash
# ❌ Scoped to subdirectories only — config.py invisible
rg "pattern" src/engine/ src/entities/ src/graphics/ src/map/ src/ui/

# ✅ Include root-level files explicitly
rg "pattern" src/ --include="*.py"  # covers src/*.py AND all subdirs
```

**Fix:** Any audit prompt targeting `src/` sub-domains MUST also include `src/*.py` (or use `src/` as the root with no subdirectory filtering). Enumerate this explicitly in the subagent prompt.

**Evidence:** 4 FR-language comments in `src/config.py` missed by the code-audit subagent in the 2026-06-12 BUILD. Discovered during verification. Corrected manually.

---

### A-SPEC-008 · 2026-06-12 · U · Minor Rework
**Adding a constant for a pattern identified in an audit report without verifying the pattern exists in source**

An audit report identified a pattern `sprite.rect.bottom - 2` and a constant `ENTITY_FOOT_Y_OFFSET` was added to `player_constants.py` for it. During refactor-clean, the literal `sprite.rect.bottom - 2` was found to not exist anywhere in source. The constant was dead on arrival.

**Anti-pattern:** Treating an audit report's pattern description as a confirmed source literal. Audit reports describe intent or architecture patterns — they do NOT guarantee the exact expression appears in code.

**Fix — Pre-edit investigation gate for new constants:**
```bash
# ✅ Before adding a constant, verify the literal EXISTS in the file:
grep -n "rect.bottom - 2" src/entities/player.py
# If 0 results → do NOT add the constant. Document in BUILD Addendum instead.
```

**Rule:** The Pre-Edit Investigation Gate (coding-standards.md) applies to constant extraction too. A constant that replaces nothing is dead code on arrival.

**Evidence:** `ENTITY_FOOT_Y_OFFSET` added to `player_constants.py` — removed during refactor-clean. Zero usages. Root cause: audit report listed the pattern; source investigation was skipped.

---

*Last updated: 2026-06-12 — L-AGENT-008 (parallel 3-stream BUILD), A-AGENT-008 (root-level src files in audit), A-SPEC-008 (speculative constant for non-existent pattern).*
