# ADR-009: Side-by-Side Workspace for GitHub Wiki and AI Specs

## Status ✅ Accepted — Migration deferred  

## Context
Our current repository `game` contains both the source code/AI specifications and the Game Design Documentation (lore, rules, user-facing docs). 
Mixing these two types of documentation pollutes the AI context. AI agents might read unstructured lore and hallucinate technical specifications, or read user manuals instead of strict executable contracts (specs).
The user requested to move the Game Design / User documentation to the GitHub Wiki, keeping only AI-centric documentation (specs, ADRs, blueprints) in the `game` repository.
Additionally, cloning a GitHub Wiki (`repo.wiki.git`) inside the main repository (`repo.git`) creates nested git repositories, which leads to staging conflicts and `.gitignore` complexity.

## Decision
1. **Documentation Split:** 
   - **Main Repo (`game`):** Retains strictly technical, AI-centric documentation (`docs/specs/`, `docs/ADRs/`, `docs/CODEMAPS/`, `docs/strategic/`).
   - **Wiki Repo (`game.wiki`):** Hosts the Game Design Document (GDD), lore, user manuals, and game mechanics explanations.
2. **Workspace Architecture:**
   - We will adopt a **Side-by-Side (Sibling) Directory Structure**. 
   - A parent folder (e.g., `workspace/`) will contain both `game/` and `game.wiki/`.
   - A VSCode `.code-workspace` file will be created in the parent folder to allow editing both repositories in the same IDE window seamlessly without Git conflicts.

## Consequences
### Positive
- **Clean AI Context:** Agents will only index technical specifications when scanning the `game` repository, drastically reducing hallucination risks.
- **Native Rendering:** Game design documents can be natively viewed and navigated on the GitHub Wiki interface.
- **Git Hygiene:** No nested `.git` folders. Each repository maintains its own commit history independently.

### Negative / Risks
- **Workspace Setup Overhead:** Developers and AI agents must be aware of the `.code-workspace` context rather than opening just the `game` folder.
- **Cross-Linking:** Linking between an AI spec and a Game Design Document requires absolute URLs to the GitHub wiki, as relative local paths won't resolve on GitHub.
