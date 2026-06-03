## Research Results: Separation of Game Documentation (Wiki) and AI Specifications (Repo)

### Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | How to structure a workspace with a main repo and its GitHub Wiki? | To avoid nested `.git` issues and keep editor context clean while editing both. | Official GitHub docs, Git workflows, StackOverflow |
| 2 | How to split Game Design Document (GDD) vs Technical AI Documentation? | To prevent AI agents from hallucinating based on loose lore, while keeping the GDD accessible. | Game Dev AI papers, BDD specs, Medium articles |

### Source Evaluation
| Source | Type | Date | Credibility | Key Findings | Conflicts? |
|--------|------|------|-------------|-------------|------------|
| GitHub Docs / Community | Official / Forums | 2023+ | High | A GitHub wiki is a separate repo (`repo.wiki.git`). DO NOT nest them. Use a side-by-side structure in a parent workspace folder. | No |
| Game AI Architecture (Medium/Dev.to) | Technical Blogs | 2023+ | Medium | Keep AI specs as "executable contracts" (Markdown in repo). Keep lore/GDD separate. Specs should use BDD (Given/When/Then) and be modular. | No |

### Conflict Analysis
| Sources | Claim A | Claim B | Reason for Discrepancy | Resolution |
|---------|---------|---------|----------------------|------------|
| N/A | | | | |

### Gaps Identified
| Gap | Why It Matters | What Research Would Fill It |
|-----|---------------|---------------------------|
| VS Code Workspace configuration | How to open both folders easily | A `.code-workspace` file is the standard way to group side-by-side repos. |
| Existing AI dependencies on GDD | If AI needs lore, how does it access it? | Ensure AI context only reads the specific rules it needs, or provide an extraction step. |

### Recommendation
- **Chosen approach:** **Adopt** the side-by-side workspace pattern and **Adapt** the AI specification structure.
- **Justification:** Nesting a `.wiki.git` inside the main `.git` repository causes submodule complexity or ignored files issues. A side-by-side setup with a `.code-workspace` file allows seamless editing of both. The Game repo should retain ONLY the `docs/specs`, `docs/ADRs`, and AI context rules, while all game mechanics, lore, and user-facing documentation move to the Wiki.
- **Impact on spec:** The workspace will be refactored by creating a new parent directory (e.g. `game-workspace`), moving the current `game` repo into it, and cloning `game.wiki` next to it. 

### Discovered Patterns
- **Side-by-side Workspace:** Create a root directory containing both repositories, and a `workspace.code-workspace` file to open them simultaneously in IDEs.
- **Behavior-Driven AI Specs:** AI specs (remaining in the repo) should follow the GIVEN/WHEN/THEN format to act as a clear contract for the AI agents, independent of the unstructured GDD in the wiki.
