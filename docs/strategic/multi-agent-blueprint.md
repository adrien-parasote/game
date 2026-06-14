# Strategic Blueprint: Multi-Agent Git Workflow

## 1. Success Metrics
- **Zero Merge Conflicts** on the main branch caused by agent interference.
- **100% Autonomous Branching & Push**: Subagents must be able to checkout, commit, and push their work to the remote repository without user intervention.

## 2. Constraint Mapping
- **Branch Naming Conventions**:
  - Features: `feat/issue-[ID]`
  - Bugs: `bug/issue-[ID]`
- **Push Policy**: Agents are required to push their branches to `origin` automatically when the `HARDEN` phase is completed.
- **Worktree Isolation**: Subagents MUST be invoked with the `Workspace: "share"` parameter to prevent working directory corruption.

## 3. Exclusions & Boundaries
- **NO MERGING**: Subagents are strictly forbidden from merging branches into `main` or `master`.
- **NO PR CREATION (via CLI)**: For now, agents push the branch, but the user is responsible for clicking "Create Pull Request" and "Merge" in the GitHub UI.

## 4. Risk Assessment
- **Risk**: Subagent gets stuck in a loop during implementation.
- **Mitigation**: Agents are bound by Stream Coding rules — if blocked at `BUILD` or `VERIFY`, they must stop and escalate to the user instead of infinitely accumulating commits on the isolated branch.

## 5. Intent Trace (Usage Assumption)
The workflow is triggered by the user with a prompt like:
*"Assign Issue #15 to a subagent, use multi-agent mode, and fix it."*

The Main Agent is responsible for orchestrating the `invoke_subagent` call with the correct parameters, and the Subagent is responsible for executing the SC methodology within its isolated worktree.
