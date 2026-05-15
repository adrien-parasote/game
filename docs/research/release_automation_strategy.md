# Strategy: Release Automation Script

## Goal
Automate the version bumping, tagging, and pushing process to ensure consistency between the codebase and repository tags.

## Proposed Solution
A Python script `scripts/release.py` that:
1. Validates the provided version (SemVer format).
2. Updates the `version` field in `settings.json`.
3. Performs a Git commit for the version bump.
4. Creates a Git tag for the new version.
5. Pushes the commit and the tag to the remote repository.

## Dependencies
- Git installed and configured.
- `settings.json` exists in the root.
- Python 3.

## Risks & Mitigations
- **Risk**: Overwriting `settings.json` with invalid JSON.
  - **Mitigation**: Parse JSON, update, and write back with formatting.
- **Risk**: Git operations fail (e.g., tag already exists).
  - **Mitigation**: Check for existing tags before proceeding. Use `subprocess.run` with error checking.
- **Risk**: Pushing to the wrong branch.
  - **Mitigation**: Only allow release from `main` (standard practice).

## Decision: Adopt/Adapt/Build
- **Build**: We will build a custom script as it's a simple, project-specific automation.

## Questions for User
1. Do you want to restrict releases to a specific branch (e.g., `main`)?
2. Should the script automatically run tests before releasing?
