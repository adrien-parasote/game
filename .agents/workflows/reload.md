---
description: Force full reload of all agent rules, workflows, skills, and methodology into context.
---

# /reload — Re-ingest Agent Configuration

Use this when the AI loses track of the methodology, forgets rules, or stops following Stream Coding conventions mid-session.

## Steps

// turbo-all

1. **Read global methodology.** Use `view_file` to read `~/.gemini/GEMINI.md` in full. This is the Stream Coding methodology — the foundation of everything.

2. **Read all rules.** List `.agents/rules/` in the current workspace, then `view_file` every `.md` file found there. These are coding standards, security rules, language-specific constraints, and context modes.

3. **Read all workflow descriptions.** List `.agents/workflows/` in the current workspace, then `view_file` every `.md` file found there. These define the slash commands available.

4. **Read all skills.** List `.agents/skills/` in the current workspace, then `view_file` every `SKILL.md` found in each skill subdirectory.

5. **Confirm reload.** After reading everything, output a summary table:

```
## ✅ Agent Configuration Reloaded

| Category     | Files Loaded | Key Items |
|--------------|-------------|-----------|
| Methodology  | 1           | GEMINI.md (Stream Coding v5.x) |
| Rules        | N           | [list basenames] |
| Workflows    | N           | [list slash commands] |
| Skills       | N           | [list skill names] |

**Active context modes:** [list from context-modes.md]
**Current phase reminder:** [identify which phase we're in based on conversation so far]
```

6. **Resume work.** Ask the user: "Configuration reloaded. What should I focus on?"

## Important

- Do NOT summarize or paraphrase the files. **Read them in full** using `view_file`.
- The point is to get the actual content back into your context window, not to skim.
- If any file is longer than 800 lines, read it in chunks until fully loaded.
