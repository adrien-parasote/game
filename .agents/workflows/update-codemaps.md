---
description: Generate token-lean architecture documentation for fast AI onboarding. Produces compact codemaps in docs/CODEMAPS/.
---

# /update-codemaps — Architecture Documentation

Generate compact, token-lean architecture maps so the AI can understand the project structure without reading the entire codebase.

## When to Use

- Starting a new project with an AI assistant
- After major feature additions or refactoring
- When the AI seems to lose project understanding
- Before onboarding a new team member or AI model

## Process

### 1. Scan project structure

1. Identify project type (monorepo, single app, library, microservice)
2. Find all source directories (src/, lib/, app/, packages/)
3. Map entry points (main.ts, index.ts, app.py, main.go, etc.)
4. Detect the tech stack from config files (package.json, go.mod, pyproject.toml, etc.)

### 2. Generate codemaps

Create or update files in `docs/CODEMAPS/`:

| File | Contents |
|------|----------|
| `architecture.md` | High-level system diagram, service boundaries, data flow |
| `backend.md` | API routes, middleware chain, service → repository mapping |
| `frontend.md` | Page tree, component hierarchy, state management flow |
| `data.md` | Database tables, relationships, migration history |
| `dependencies.md` | External services, third-party integrations, shared libraries |

Only create files relevant to the project. A pure backend has no `frontend.md`.

### 3. Codemap format

Each codemap must be **token-lean** — optimized for AI context consumption:

```markdown
<!-- Generated: YYYY-MM-DD | Files scanned: N | Token estimate: ~N -->

# Backend Architecture

## Routes
POST /api/users → UserController.create → UserService.create → UserRepo.insert
GET  /api/users/:id → UserController.get → UserService.findById → UserRepo.findById
DELETE /api/users/:id → UserController.delete → [auth middleware] → UserRepo.delete

## Key Files
src/services/user.ts (business logic, 120 lines)
src/repos/user.ts (database access, 80 lines)
src/middleware/auth.ts (JWT validation, 40 lines)

## Dependencies
- PostgreSQL (primary data store)
- Redis (session cache, rate limiting)
- Stripe (payment processing)
```

### 4. Diff detection

1. If previous codemaps exist, calculate the diff percentage
2. If changes > 30%, show the diff and request user approval before overwriting
3. If changes <= 30%, update in place

### 5. Add metadata header

Add a freshness header to each codemap:

```markdown
<!-- Generated: YYYY-MM-DD | Files scanned: N | Token estimate: ~N -->
```

## Rules

- Focus on **high-level structure**, not implementation details
- Prefer **file paths and function signatures** over full code blocks
- Keep each codemap under **1000 tokens** for efficient context loading
- Use ASCII route chains (`→`) instead of verbose descriptions
- Version control the codemaps (they belong in git)

## Stream Coding Integration

- **Stage:** 🔬 DISCOVER — helps the AI understand the project before documenting
- **Also useful in:** ⚡ BUILD — the AI can reference codemaps instead of re-reading files
- **Run `/doc-update`** after generating codemaps to ensure consistency
