# Strategic Blueprint: Workspace Restructure & Wiki Separation

## The 7 Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | What exact problem are you solving? | The mixing of Game Design Documentation (lore, rules) and AI Specifications (technical contracts, prompts) in the same repo pollutes the AI's context and creates hallucination risks. |
| 2 | What are your success metrics? | A clean, functional VSCode workspace where `game` (code/AI specs) and `game-wiki` (user/design docs) coexist side-by-side without nested `.git` issues. |
| 3 | Why will you win? | By decoupling the game design lifecycle from the code lifecycle, we leverage native GitHub Wiki rendering while keeping a pristine context for the AI agents in the main repository. |
| 4 | What's the core architecture decision? | Using a multi-root `.code-workspace` in a parent directory, with the `game` and `game.wiki` repositories cloned as sibling directories. |
| 5 | What's the tech stack rationale? | GitHub Wiki natively uses Markdown (compatible with our agents) and VSCode natively supports multi-root workspaces, ensuring no friction. |
| 6 | What are the features? | 1. Create parent folder. 2. Move existing `game` repo into it. 3. Clone `game.wiki` repo alongside it. 4. Migrate user/GDD docs to the wiki. 5. Set up `workspace.code-workspace`. |
| 7 | What are you NOT building? | We are NOT migrating AI-specific documentation (specs, ADRs, codemaps). The AI documentation REMAINS in the `game` repository. The user/lore documentation GOES to the `game-wiki`. |

## Gap Discovery

| # | Gap | Impact if unresolved | Owner |
|---|-----|---------------------|-------|
| 1 | **Image & Asset Management for Docs:** How do we handle images referenced in the GDD? Do we store them in the wiki repo, or reference them via raw URLs from the game repo? | Broken image links in the GitHub Wiki or a bloated wiki repository if large assets are committed incorrectly. | User / Team |
| 2 | **AI Access to Lore:** If the AI needs context from the GDD (e.g., to write a quest script), how does it access the Wiki if it's considered "human documentation"? Does the AI have permission to read the wiki repo locally? | The AI might hallucinate game lore if it loses access to the GDD, leading to out-of-character scripts or mechanics. | User / Agent Workflow |
| 3 | **Exact File Migration Map:** Which specific files/folders currently in `game/docs/` qualify as "User/GDD" vs "AI/Specs"? (e.g., are there files that mix both and need to be split?) | Incomplete or inconsistent separation, leaving AI with polluted context or users with missing documentation. | User |
