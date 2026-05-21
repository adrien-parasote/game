# Stream Coding v6.0: Documentation-First Development

> "If your docs are good enough, AI writes the code. The hard work IS the documentation. Code is just the printout."

⚠️ **THIS IS AN AI DOCUMENTATION-DRIVEN CODING METHODOLOGY, NOT A CODE-FIRST METHODOLOGY.**

```
Messy Docs → Vague Specs → AI Guesses → Rework Cycles → 2-3x Velocity
Clear Docs → Clear Specs → AI Executes → Minimal Rework → 10-20x Velocity
```

### Core Mantras

1. "Documentation IS the work. Code is just the printout."
2. "When code fails, fix the spec — then the code."
3. "A 7/10 spec generates 7/10 code that needs 30% rework."
4. "If AI has to decide where to find information, you've already lost velocity."

---

## METHODOLOGY OVERVIEW

### Stages & Pipeline

| Stage | Icon | Purpose | Workflows (in order) | Time |
|-------|------|---------|---------------------|------|
| **DISCOVER** | 🔬 | Research, reuse, and concept shaping | `/research`, `/experiment`, `/clarify` | 5% |
| **STRATEGY** | 🎯 | Strategic thinking — WHAT and WHY | `/strategy` | 40% |
| **SPEC** | 📋 | AI-ready documentation + gates | `/spec-gate` → `/adversarial-review` | 40% |
| **BUILD** | ⚡ | Code generation from spec | `/plan` → `/orchestrate` → `/tdd` → implement | 5% |
| **VERIFY** | 🔍 | Quality gates — verification, review, security | `/verification-loop` → `/code-review` → `/security-review` | 5% |
| **HARDEN** | ✅ | Iteration, divergence prevention, learning | `/doc-update` → `/refactor-clean` → `/learn-eval` → **COMMIT** | 5% |

> 5% Research (DISCOVER) · 80% Documentation (STRATEGY + SPEC) · 15% Code + Quality (BUILD + VERIFY + HARDEN) · ⛔ Commits happen in HARDEN only

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

1. **DISCOVER first (MANDATORY):** Run `/research` — perform actual web search for existing implementations, official API docs, SDKs. Listing the project directory is NOT research. You must web-search before writing any documentation or asking strategy questions.
2. **If idea is vague or half-formed:** Run `/clarify` — shape the concept through structured dialogue before entering STRATEGY. Skip if the idea is already sharp (Clarity Score ≥ 4/5).
3. **Check for existing docs:** "Do you have existing documentation for this project?"
4. **If existing docs:** "Let's start with a Documentation Audit."
5. **If STRATEGY incomplete:** "Before building, let's clarify strategy. [Ask 7 Questions]"
6. **If SPEC incomplete:** "Before coding, let's ensure documentation is AI-ready. [Run Spec Gate]"
7. **If Spec Gate not passed:** "Documentation scores [X]/10. Let's fix [specific issues]."
8. **If BUILD ready:** "Running /tdd first — writing tests from spec..."
9. **If implementing without tests:** ⛔ "RED tests are step 1. Running /tdd now."
10. **If maintaining (HARDEN):** "Is this change spec-conformant? Let's update docs first."

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
| Behaviors | `.agents/rules/sc-behaviors.md` — 7 Operating Behaviors, 10 Failure Modes |
| Antigravity | `.agents/rules/antigravity-integration.md` — AG mapping, artifact paths |
| Orchestration | `.agents/rules/workflow-orchestration.md` — Decision tree, skill reference |
| Git | `.agents/rules/git-discipline.md` — Safety rules, -F protocol, commit format |
| Coding | `.agents/rules/coding-standards.md` — Universal code rules, investigation gate |

> **Load the relevant rule file when entering a stage.** GEMINI.md enforces the gates and pipeline; the topic files provide the detailed procedures.

