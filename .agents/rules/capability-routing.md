# Capability Surface Routing

> **Core principle:** Put each capability in the **narrowest surface** that preserves correctness, keeps token cost under control, and avoids unnecessary complexity.
> If the agent has to decide where to find information, you've already lost velocity. (Mantra M4)

## Decision Order

When adding a new capability to the methodology, ask these questions **in order**:

### 1. Should this happen every time a path or event matches, with no model judgment?

→ **Use a rule** (`.agents/rules/`)

Rules are deterministic, always-on constraints injected when a path or event matches. They should be:
- Short enough to not bloat every matching request
- Deterministic (no judgment calls — the rule IS the decision)
- Universal within their scope

**Use for:**
- Coding invariants (naming, immutability, error handling)
- Safety floors and permission constraints (security.md)
- Process constraints (spec-gate-rule.md, tdd-gate-rule.md)
- Language-specific standards (typescript.md, golang.md)

**Do NOT use for:**
- Large playbooks or multi-step workflows (too many tokens per injection)
- Optional or situational guidance
- Domain-specific knowledge that only matters sometimes (e.g., Next.js 16 patterns)

---

### 2. Is this a playbook, advisory layer, or workflow that should load only when the task needs it?

→ **Use a skill** (`.agents/skills/`)

Skills are on-demand workflows loaded when context matches the `description` in SKILL.md frontmatter. They should be:
- Rich enough to justify the token cost of loading
- Self-contained (readable without other docs)
- Activated by context detection, not manual invocation

**Use for:**
- Multi-step workflows with judgment (verification-loop, security-review)
- Domain playbooks (architect, planner, ui-ux-pro-max)
- Advisory layers that are expensive to load and only relevant sometimes
- Tools with companion scripts (security-review/scripts/, verification-loop/scripts/)

**Do NOT use for:**
- Static invariants that should always apply (those are rules)
- Simple step-by-step processes invoked manually (those are workflows)

---

### 3. Is this a step-by-step process invoked by a slash command?

→ **Use a workflow** (`.agents/workflows/`)

Workflows are manual processes invoked via `/slash-command`. They should be:
- Linear and sequential (step 1, step 2, ...)
- Invoked explicitly by the user or by another workflow
- Focused on a single process (not a library of guidance)

**Use for:**
- Mandatory processes (/spec-gate, /tdd, /orchestrate)
- Recovery procedures (/build-fix, /self-debug)
- Maintenance operations (/doc-update, /refactor-clean, /learn-eval)
- Context management (/checkpoint, /reload, /aside)

**Do NOT use for:**
- Domain knowledge (that's a skill)
- Always-on constraints (that's a rule)

---

### 4. Is this a one-shot local action that runs as a script?

→ **Use a script** (inside a skill's `scripts/` directory)

Scripts are deterministic executables called by skills. They should be:
- Executable without interactive input
- Producing structured output (JSON, exit codes)
- Scoped to a single skill (live inside the skill's directory)

**Use for:**
- Automated verification (verify.py, security_scan.py)
- Data-driven lookups (search.py for ui-ux-pro-max)
- Spec conformance checks (spec_conformance.py)

---

## Routing Anti-Patterns

| ❌ Don't | ✅ Do Instead | Why |
|----------|---------------|-----|
| Put framework-specific knowledge in a rule | Discover it during `/research`, or create an on-demand skill | Rules are always-on — framework knowledge is situational |
| Create a skill that just wraps a single script | Put the script in an existing skill's `scripts/` dir | Skill overhead (loading, context) isn't justified for a wrapper |
| Create a workflow for static guidance | Make it a skill (loaded on demand by context) | Workflows are processes, not libraries |
| Duplicate rule content in a skill | Reference the rule from the skill with a deep link | Single source of truth |
| Add a new surface before checking if an existing one covers it | Search existing rules/skills/workflows first | Avoids surface sprawl |

## Cost and Reliability Bias

When two surfaces are both viable, prefer:
1. **Smaller token overhead** — rules < workflows < skills (in injection cost)
2. **Fewer moving parts** — native content > scripts > external tools
3. **Narrower scope** — an addition to an existing skill > a new standalone skill

## External Adoption Policy

When bringing in ideas from external repos (ECC, antigravity-kit, community):

1. **Copy the idea**, not the external dependency
2. **Adapt to our surfaces** (rules/skills/workflows/scripts)
3. **Rename** if the functionality has been materially reshaped for Stream Coding
4. **Strip** external-specific references (harness names, tool names, vendor framing)
5. **Validate** against the 4 core mantras before integrating (see `/research` adaptation gate)

---

**Remember**: Surface sprawl is methodology debt. Every new rule/skill/workflow adds token cost and routing complexity. Justify the addition.
