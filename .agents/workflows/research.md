---
description: Mandatory research before implementation. GitHub/registries → docs → web. Adopt > Adapt > Build-New.
---

# /research — Research Before Implementation

## When to Use

**ALWAYS** before coding a feature or component. This workflow is the first step of the 🔬 DISCOVER stage.

## Stream Coding Integration

- **Stage:** 🔬 DISCOVER — before the 7 Questions
- **Principle:** Never reinvent what already exists. Research informs the spec, not the code.
- **Output:** Results feed the spec, not the implementation directly

## Search Hierarchy

### 0. Load project context (BEFORE searching)

If `docs/CODEMAPS/` exists, read all codemaps **before** any search:
1. Read every `.md` file in `docs/CODEMAPS/`
2. Use them to **scope your search** — target specific modules and paths instead of grepping the entire codebase

> If no codemaps exist, skip to step 1. Consider running `/update-codemaps` after research completes.

### 1. Search existing code (scoped by codemaps)

```bash
# Search in the current project
rg -n "search_pattern" --include="*.ts" --include="*.py"

# Search on GitHub (public repos)
gh search repos "topic:keyword" --sort=stars --limit=5
gh search code "function_name language:typescript" --limit=10

# Search in package registries
npm search <keyword>
pip search <keyword>  # or pip index versions <package>
cargo search <keyword>
```

### 2. Library documentation (SECOND)

- Consult official framework/library documentation
- Check examples in the library GitHub repo
- Look for recommended patterns in official guides

### 3. Web search (LAST RESORT)

- Use only if the first two steps were insufficient
- Prioritize official sources and recent technical articles
- Verify publication date (< 2 years preferred)

## Decision Matrix

| Situation | Approach | Justification |
|-----------|----------|---------------|
| Existing solution in the project | **Reuse** | Consistency, no duplication |
| Well-maintained package available | **Adopt** | Do not reinvent the wheel |
| Close but imperfect package | **Adapt** | Fork/extend > build from scratch |
| Nothing exists | **Build** | Only case where new code is justified |

## Adaptation Gate (for external patterns)

When research finds an external pattern (from ECC, antigravity-kit, community repos, or other sources) worth adopting into our methodology, apply this gate **before** integrating:

### 5 Review Questions

| # | Question | If answer is weak → |
|---|----------|---------------------|
| 1 | Is this a **real reusable surface** in our methodology, or just documentation for another tool? | Do not adopt — it's a reference, not a capability |
| 2 | Does the name match **our vocabulary**? (rules/skills/workflows, Stream Coding stages) | Rename to fit our terminology |
| 3 | Do we **already own** this behavior in an existing rule/skill/workflow? | Absorb into existing surface — don't create a new one |
| 4 | Are we importing a **concept**, or importing someone else's **product identity**? | Strip external branding, keep the idea |
| 5 | Would a Stream Coding user understand the purpose **without knowing the upstream repo**? | Reframe in our methodology's language |

### Compliance Check

Before adopting, verify against the 4 core mantras:

| Mantra | Test |
|--------|------|
| M1: "Documentation IS the work" | Does this improve specs/docs, not just add domain knowledge? |
| M2: "Fix the spec, not the code" | Does this respect the spec→code direction? |
| M3: "A 7/10 spec generates 7/10 code" | Does this reduce ambiguity in the methodology? |
| M4: "No routing ambiguity" | Does this reduce (not increase) where the agent looks for information? |

### Surface Routing

Decide where the adopted pattern lives (see `.agents/rules/capability-routing.md`):
- Always-on constraint → **rule**
- On-demand playbook → **skill**
- Step-by-step process → **workflow**
- Deterministic script → **script** inside a skill

> **Anti-pattern:** Hardcoding framework-specific domain knowledge into always-on rules. The agent should discover framework patterns during `/research`, not pre-load them.

## Expected Output

Research results must include:

```markdown
## Research Results: [topic]

### Existing Solutions Found
| Solution | Source | License | Maintenance | Fit (1-5) |
|----------|--------|---------|-------------|-----------|
| [name] | [link] | [MIT/Apache/etc] | [active/archived] | [score] |

### Recommendation
- **Chosen approach:** [Adopt/Adapt/Build]
- **Justification:** [why this approach]
- **Impact on spec:** [how it modifies the spec]

### Discovered Patterns
- [pattern 1 to integrate into the spec]
- [pattern 2 to integrate into the spec]
```

## Checklist

- [ ] Existing codebase search performed
- [ ] Package registries consulted
- [ ] Official documentation read
- [ ] At least 3 solutions compared (if available)
- [ ] Adopt/Adapt/Build decision taken and justified
- [ ] Results documented for spec integration
