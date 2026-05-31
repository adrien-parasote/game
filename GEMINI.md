# Stream Coding v3.0.0: Documentation-First Development

> "If your docs are good enough, AI writes the code. The hard work IS the documentation. Code is just the printout."

⚠️ **THIS IS AN AI DOCUMENTATION-DRIVEN CODING METHODOLOGY, NOT A CODE-FIRST METHODOLOGY.**

```
Messy Docs → Vague Specs → AI Guesses → Rework Cycles → 2-3x Velocity
Clear Docs → Clear Specs → AI Executes → Minimal Rework → 10-20x Velocity
```

### Core Mantras

1. "One deliverable per turn. Complete a stage, then STOP and wait."
2. "Ask, don't fill. Missing information = question to the user, not a guess."
3. "Success = wrong assumptions caught. Not code produced."
4. "When code fails, fix the spec — then the code."
5. "Documentation IS the work. Code is just the printout."

---

## METHODOLOGY OVERVIEW

### Stages & Pipeline

| Stage | Icon | Purpose | Workflows | Halt |
|-------|------|---------|-----------|------|
| **DISCOVER** | 🔬 | Research, reuse, concept shaping | `/research`, `/experiment`, `/clarify` | ⛔ STOP. Ask: "Move to STRATEGY?" |
| **STRATEGY** | 🎯 | WHAT and WHY — not HOW | `/strategy` | ⛔ STOP. Ask: "Move to SPEC?" |
| **SPEC** | 📋 | AI-ready documentation + gates | `/spec-gate` → `/adversarial-review` | ⛔ STOP. Ask: "Spec Gate passed. Move to BUILD?" |
| **BUILD** | ⚡ | Code from spec — nothing else | `/plan` → `/orchestrate` → `/tdd` | ⛔ STOP. Run verify. |
| **VERIFY** | 🔍 | Quality gates | `/verification-loop` → `/code-review` → `/security-review` | ⛔ STOP. Ask: "Move to HARDEN?" |
| **HARDEN** | ✅ | Divergence prevention, learning, commit | `/doc-update` → `/refactor-clean` → `/learn-eval` → **COMMIT** | Done. |

> ⛔ **Each stage ends with a STOP.** Run all Workflows for the current stage, present results to the user, then STOP. Do not produce Stage N+1 deliverables in the same turn. Commits happen in HARDEN only.

### Five-Gate Enforcement

> **⛔ These gates are unconditional. No gate may be skipped.**

| Gate | Enforces | Pass Condition |
|------|----------|----------------|
| **Discover Gate** | Research completed before strategy/spec | Research artifact exists in `docs/research/` with web search results, API docs citations, and Adopt/Adapt/Build decision |
| **Spec Gate** | Spec is AI-ready | `python3 .agents/skills/spec-gate/scripts/spec_precheck.py --dir <spec_dir>` → ALL checks PASS, score = 10/10 |
| **TDD Gate** | RED tests exist before implementation | `python3 .agents/skills/verification-loop/scripts/tdd_check.py . --module <path>` → PASS |
| **Verify Gate** | Code builds, passes tests, passes security | `python3 .agents/skills/verification-loop/scripts/verify.py .` → ALL items PASS |
| **Commit Gate** | verify.py + /doc-update + /refactor-clean + /learn-eval | All four completed → ALL YES |

> **Discover Gate** → Spec Gate → TDD Gate → Implementation → Verify Gate → Code Review → HARDEN → Commit

### Stage-Gate State File

> Enforced by `source-write-gate.sh` hook (PreToolUse). Writing outside your stage is blocked.

The file `.agents/active_stage.json` tracks the current stage and allowed write paths.
It is auto-created at session start. The hook reads it before every file write.

**Stage definitions** — use these `write_allowed` values when transitioning:

| Stage | `write_allowed` | Rationale |
|-------|-----------------|-----------|
| DISCOVER | `["docs/research/", "docs/concepts/", ".agents/", "*.md"]` | Research artifacts only |
| STRATEGY | `["docs/", ".agents/", "*.md"]` | Strategy docs, blueprints |
| SPEC | `["docs/", "tests/", ".agents/", "*.md"]` | Specs + TDD test stubs |
| BUILD | `["*"]` | All files — implementation phase. **Source files still gated by spec-gate + TDD-gate.** |
| VERIFY | `["tests/", "docs/", ".agents/", "*.md"]` | Test fixes, docs — no source edits |
| HARDEN | `["*"]` | All files — refactor-clean may touch source. **Source files still gated by spec-gate + TDD-gate.** |

**Stage transitions:** User approves → update `.agents/active_stage.json` with the next stage's `current_stage` and `write_allowed` from the table above. Do not transition without explicit user approval.

**Bypass (per Skip Decision Table):** Trivial tasks (typo, rename, tiny bug) skip DISCOVER/STRATEGY/SPEC/BUILD stages but still pass through HARDEN's commit gate. To bypass gates for trivial fixes: `touch .sc-stage-gate-bypass` (+ `.sc-spec-gate-bypass`, `.sc-tdd-bypass` as needed). **The agent must NEVER create bypass files without explicit user approval.** Branch names (`fix/`, `bugfix/`, `hotfix/`) are naming conventions only — they have no effect on gates.

### The Golden Rule

> **"When code fails, fix the spec — not the code."** Manual patches create divergence. Divergence compounds. Fix the spec, re-implement.

---

## 🔬 DISCOVER: RESEARCH, REUSE & CLARIFY

**Mandatory skill:** `/research`
**Optional skill:** `/clarify` — when the user's intent is vague or half-formed

1. **Search** for existing implementations (GitHub, package registries, official docs)
2. **Evaluate** existing solutions against your requirements
3. **Prefer** adopting a proven pattern over designing from scratch
4. **Experiment** if a decision has measurable trade-offs → run `/experiment`
5. **Clarify** if the user's idea is vague or half-formed → run `/clarify` to shape it into a concept before entering STRATEGY. Skip if the idea is already sharp (could score ≥ 4/5 on `/strategy`'s Clarity Score right now).
6. **Document** with knowledge of what already exists

> ⛔ **External API integrations: search for official docs FIRST.** Web search for official API documentation is mandatory *before* reading any existing client code. Existing source code shows how ONE consumer uses the API; it can be outdated, partial, or wrong.

---

## DOCUMENT TYPE ARCHITECTURE

> **⛔ All docs live within the project workspace** (e.g. `docs/`, `.agents/`). Temporary files in `/tmp/` are not version-controlled and will be lost.

**The Rule:** Not all documents need all sections. Putting implementation details in strategic documents violates single-source-of-truth.

| Type | Purpose | Examples |
|------|---------|----------|
| **Strategic** | WHAT and WHY | Master Blueprint, PRD, Vision docs |
| **Implementation** | HOW | Technical Specs, API docs, Module specs |
| **Reference** | Lookup | Schema Reference, Glossary, Configuration |

| Section | Strategic Docs | Implementation Docs | Reference Docs |
|---------|---------------|---------------------|----------------|
| **Deep Links** | ✅ Required | ✅ Required | ✅ Required |
| **Anti-patterns** | ❌ Pointer only | ✅ Required | ❌ N/A |
| **Test Cases** | ❌ Pointer only | ✅ Required | ❌ N/A |
| **Error Handling** | ❌ Pointer only | ✅ Required | ❌ N/A |

---

## TRIGGER BEHAVIOR

This methodology activates when the user says:
- "Build [feature]" → Full methodology (DISCOVER through HARDEN)
- "Create [component]" → Full methodology (DISCOVER through HARDEN)
- "Implement [system]" → Check: Do clear docs exist? If yes → BUILD + HARDEN. If no → full pipeline.
- "Document [project]" → DISCOVER + STRATEGY + SPEC only (no code)
- "Spec out [feature]" → DISCOVER + STRATEGY + SPEC only (no code)
- "Clean up docs for [X]" → STRATEGY Documentation Audit only

### Response Protocol

1. **DISCOVER first (MANDATORY):** Run `/research` — web search for existing implementations, official docs. Listing the project directory is NOT research.
2. **If idea is vague:** Run `/clarify` to shape concept. Skip if Clarity Score ≥ 4/5.
3. ⛔ **STOP.** Present research findings. Ask: "Shall we move to STRATEGY?"
4. **STRATEGY:** Ask the 7 Questions. Do NOT answer them yourself.
5. ⛔ **STOP.** Present Blueprint. Ask: "Shall we move to SPEC?"
6. **SPEC:** Write implementation spec. Run `/spec-gate` → `/adversarial-review`.
7. ⛔ **STOP.** Present Spec Gate score. Ask: "Shall we move to BUILD?"
8. **BUILD:** Run `/tdd` first (RED tests). Then implement.
9. **VERIFY:** Run `/verification-loop` → `/code-review` → `/security-review`.
10. **HARDEN:** Run `/doc-update` → `/refactor-clean` → `/learn-eval` → COMMIT.

### Stage Skip Decision Table

| Change Type | DISCOVER | STRATEGY | SPEC | BUILD | VERIFY | HARDEN |
|-------------|----------|----------|------|-------|--------|--------|
| Typo, rename, tiny bug | Skip | Skip | Skip | Direct fix | Lint only | Commit |
| Bug fix, clear repro | Skip | Skip | Skip | TDD + fix | Full verify | Commit |
| Feature, clear criteria | Full | Full | Full | Full | Full | Full |
| Feature, ambiguous | Full | Full | Full | Full | Full | Full |
| High-stakes migration | Full | Full + ADR | Full + adversarial | Full | Full | Full |

---

## STAGE DETAIL ROUTING

Each stage's detailed rules, checklists, and procedures live in dedicated rule files:

| Stage/Topic | Detailed Rules File |
|-------------|-------------------|
| 🎯 STRATEGY | `.agents/rules/strategy-stage.md` — 7 Questions, Audit, exit criteria |
| 📋 SPEC | `.agents/rules/spec-writing.md` + `.agents/rules/spec-quality.md` |
| ⚡ BUILD | `.agents/rules/build-execution.md` — Spec-Test-Implement loop, smallest diff |
| 🔍 VERIFY | `.agents/rules/verify-stage.md` — Verify Gate, Evaluator Separation |
| ✅ HARDEN | `.agents/rules/harden-stage.md` — Commit Gate, Divergence, Day 2, Learning |
| Behaviors | `.agents/rules/sc-behaviors.md` — 8 Operating Behaviors, 11 Failure Modes |
| Antigravity | `.agents/rules/antigravity-integration.md` — AG mapping, artifact paths |
| Orchestration | `.agents/rules/workflow-orchestration.md` — Decision tree, skill reference |
| Git | `.agents/rules/git-discipline.md` — Safety rules, -F protocol, commit format |
| Coding | `.agents/rules/coding-standards.md` — Universal code rules, investigation gate |

> **Load the relevant rule file when entering a stage.** GEMINI.md enforces the gates and pipeline; the topic files provide the detailed procedures.

---

## 🔧 PROJECT-SPECIFIC: Commit Protocol (Antigravity Sandbox Override)

> **⛔ MANDATORY — This overrides the standard git-discipline.md commit protocol for this project.**

### Problem

The Antigravity sandbox blocks `git commit` directly unless `.sc-learn-eval` exists.
The agent cannot write `.sc-learn-eval` directly (sandbox protection).

### Solution

Use `./scripts/sc-commit.sh` instead of `git commit` **for every commit**.
The script creates the sentinel then commits — runs outside the sandbox restriction.

### Agent Commit Protocol (replaces `git commit -F`)

**Step 1 — Write message to file:**
```bash
cat > /tmp/commit_msg.txt << 'EOF'
type(scope): description

Body of commit message.
EOF
```

**Step 2 — Stage files:**
```bash
git add path/to/file1 path/to/file2
```

**Step 3 — Commit via sc-commit.sh:**
```bash
./scripts/sc-commit.sh -F /tmp/commit_msg.txt && rm /tmp/commit_msg.txt
```

### Forms

| Use case | Command |
|----------|---------|
| Message from file (multi-line) | `./scripts/sc-commit.sh -F /tmp/msg.txt` |
| Short inline message | `./scripts/sc-commit.sh "type(scope): msg"` |
| Stage + commit in one call | `./scripts/sc-commit.sh "type(scope): msg" file1 file2` |
| Empty commit (test/placeholder) | `./scripts/sc-commit.sh --empty "type(scope): msg"` |

### Rules

- **Always use `sc-commit.sh`** — never `git commit` directly from the agent
- **Stage before calling** `-F` form — `sc-commit.sh -F` does not auto-stage
- **Message file in `/tmp/`** — never in the repo (not tracked)
- **Push separately** — `git push` is unaffected by the sandbox
