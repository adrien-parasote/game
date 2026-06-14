# Research: Multi-Agent Parallel Workflow (GitHub Issues)

## 1. Problem Statement
The user wants to implement a robust tracking workflow:
1. Requirements enter via GitHub Issues.
2. Each resolution happens on a dedicated Git branch.
3. The user wants the ability to have Antigravity (AGY) work on multiple issues in parallel (Multi-Agent, Multi-Branch).
4. Code is merged via Pull Requests when approved.

## 2. The Core Challenge: The Working Directory Conflict
Git tracks a single working tree by default. If Agent A works on `feat/issue-1` and Agent B works on `feat/issue-2` in the same `/game` folder simultaneously:
- Git will be in a detached or conflicting state.
- Agent A's file edits will pollute Agent B's workspace.
- Tests run by Agent A will compile Agent B's half-finished code.

## 3. The Solution: Git Worktrees via Antigravity Native Support
The industry-standard solution for this in Git is **Git Worktrees** (`git worktree add`). It creates a secondary folder on the hard drive linked to the same `.git` database, allowing a completely isolated checkout of a different branch.

**Antigravity (AGY) natively supports this.** 
The `invoke_subagent` tool has a specific parameter for this exact use case: `Workspace: "share"`.
- When invoked with `share`, AGY creates a new isolated worktree on the disk.
- The subagent can checkout its own branch and edit files without touching the parent agent's main directory.

## 4. Proposed Workflow

### Step A: Triage (Main Agent)
- User: *"Assign Issue #12 to a subagent."*
- Main Agent reads Issue #12 from GitHub (via curl/API or user copy-paste).

### Step B: Parallel Delegation (Main Agent spawns Subagent)
- Main Agent calls `invoke_subagent` with:
  - `Role`: "Issue #12 Developer"
  - `Workspace`: `"share"`
  - `Prompt`: "Checkout branch `feat/issue-12`. Implement the following issue using the full SC pipeline (STRATEGY -> SPEC -> BUILD -> HARDEN). Issue details: [...]"

### Step C: Isolated Development (Subagent)
- The Subagent wakes up in its isolated worktree.
- Runs `git checkout -b feat/issue-12`.
- Executes the Stream Coding pipeline independently.
- Commits the code via `./scripts/sc-commit.sh`.
- Pushes the branch: `git push origin feat/issue-12`.
- Notifies the Main Agent that the Pull Request is ready.

### Step D: Review & Merge (User)
- The user reviews the PR on GitHub, gives the "Go", and clicks Merge.

## 5. Do we need a custom Skill?
**Strictly speaking, no.** The native tools (`invoke_subagent`, `run_command` for git) already cover 100% of the technical needs. 

However, we can create a **Workflow Rule** (a simple markdown file like `.agents/rules/multi-agent-workflow.md`) to standardize this so both the user and the agent remember the exact exact commands and prompt structures to use when spawning parallel workers.
