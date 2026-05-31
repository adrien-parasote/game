## Research Results: Repository Architecture for Growing Game Projects

### Topic Decomposition
| # | Sub-Question | Why Necessary | Source Types |
|---|-------------|---------------|-------------|
| 1 | Monorepo vs Multi-repo for game development | To determine if splitting code, assets, and tools is beneficial or harmful for a growing project. | Industry best practices, DevOps blogs |
| 2 | Managing large binary assets (Tiled, images, sound) | Git is inherently bad at binaries; we need to know if multi-repo solves this or if Git LFS is the standard. | Git documentation, Game dev forums |
| 3 | Separation of tools and game code | To understand if custom tools (e.g., map editors, build scripts) should live in the game repo or be isolated. | Architecture blogs |

### Source Evaluation
| Source | Type | Date | Credibility | Key Findings | Conflicts? |
|--------|------|------|-------------|-------------|------------|
| Spacelift / Dev.to | Tech Blog | Recent | High | Monorepos are heavily favored for game dev due to atomic commits and shared code. Multi-repo introduces dependency hell. | No |
| Raftt.io / Bitbebop | Tech Blog | Recent | High | Git LFS is mandatory for large assets; keeping them in the same repo as code is preferred unless sharing across many games. | No |
| Epic Games / Unreal Docs | Official Docs | N/A | High | Asset naming conventions and folder structure are more important than repo splits. Monorepo is standard. | No |

### Conflict Analysis
There are no major conflicts among credible sources. The consensus is strongly against splitting a single game project into multiple repositories unless the tools/assets are being shared across multiple *different* games by *independent* teams. 

### Gaps Identified
| Gap | Why It Matters | What Research Would Fill It |
|-----|---------------|---------------------------|
| Scope of the Tools | If the tools are being built to be generic and sold/used for other future games, polyrepo might make sense. | Clarification from the user. |
| Current Git LFS usage | If Git LFS isn't configured, the repo size is the real problem making it feel "heavy", not the structure itself. | Checking local `.gitattributes`. |

### Recommendation
- **Chosen approach:** **Adopt Monorepo with Git LFS** (Keep code, assets, and tools in a single repository).
- **Justification:** Game development relies heavily on atomic commits—a code change often requires a simultaneous asset or tool change. Multi-repo introduces massive versioning overhead ("Dependency Hell") and makes refactoring across tools and game code very difficult. The performance issues of large assets are solved by Git LFS, not by multi-repo.
- **Impact on spec:** We will keep everything in one repo but enforce strict folder boundaries (`/src`, `/assets`, `/tools`) and ensure Git LFS is properly tracking all binary files (`.png`, `.wav`, `.tmx` map binaries if applicable).

### Discovered Patterns
- **Atomic Commits:** Update a game feature, its asset, and its tool in a single commit to ensure the build is never broken for other team members. [source: Spacelift / Raftt.io]
- **Git LFS as standard:** Use Git LFS for all binary assets instead of git submodules. [source: Bitbebop]
- **Directory Isolation (Not Repo Isolation):** Use clear domain-based folders rather than splitting repositories. [source: Epic Games Best Practices]
