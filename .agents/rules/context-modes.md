# Context Modes — Stream Coding Operational Modes

> These modes frame AI behavior depending on the current stage. Each mode reinforces the doc-first principle.

## dev — Execution mode

**Focus:** Follow the spec to the letter. Generate code that conforms to the validated spec.

**Behavior:**
- Code only what the spec requires — nothing more
- If ambiguity in the spec → **stop and signal**, do not guess
- Atomic commits with conventional messages
- Working > Perfect > Clean (but always spec-conformant)

**Anti-behavior:**
- ❌ "Code first, explain after" (this is the opposite of Stream Coding)
- ❌ Adding features not in the spec
- ❌ "Improving" code beyond what the spec requires

## review — Conformance mode

**Focus:** Verify that code respects the spec, security rules, and coding standards.

**Behavior:**
- Read code AND spec in parallel
- Compare implemented behavior vs specified behavior
- Prioritize by severity (CRITICAL → HIGH → MEDIUM → LOW)
- Suggest concrete fixes, not vague remarks
- If code diverges from spec → flag the spec, not the code (Golden Rule)

**Anti-behavior:**
- ❌ Modifying code during review
- ❌ Reporting stylistic preferences as bugs
- ❌ Patching code without checking if the spec is incomplete

## research — Exploration mode

**Focus:** Understand before documenting. Explore before deciding.

**Behavior:**
- Read broadly before concluding (codebase, docs, existing patterns)
- Document findings in a structured way
- Do not code before achieving full clarity
- Search for existing implementations before proposing new ones

**Anti-behavior:**
- ❌ Prototyping during research
- ❌ Concluding from a single source
- ❌ Documenting hypotheses as facts
