# Technical Specification: Release Automation Script

## 1. Overview
The `release.py` script simplifies the release process by automating the version update in `settings.json`, committing the change, tagging the commit, and pushing both to the remote repository.

## 2. Deep Links
- **Configuration**: [settings.json](../../settings.json)
- **Reference Script**: [scripts/get_version.py](../../scripts/get_version.py)
- **Strategy**: [release_automation_strategy.md](../../docs/research/release_automation_strategy.md)

## 3. Interface
```bash
python scripts/release.py <version>
```
- `<version>`: Required. Must follow Semantic Versioning (e.g., 0.6.1, 1.0.0).

## 3. Workflow
1. **Pre-checks**:
   - Verify that the working directory is clean (`git status --porcelain`).
   - Verify that the provided version is valid (SemVer).
   - Verify that the tag `<version>` does not already exist locally or remotely.
2. **Update Settings**:
   - Read `settings.json`.
   - Update the `"version"` field.
   - Write back to `settings.json` with 2-space indentation.
3. **Git Operations**:
   - `git add settings.json`
   - `git commit -m "chore: bump version to <version>"`
   - `git tag <version>`
   - `git push origin <current_branch>`
   - `git push origin <version>`

## 4. Error Handling
- The script must exit with a non-zero status code if any operation fails.
- Explicit error messages for:
  - Invalid version format.
  - Dirty working directory.
  - Tag already exists.
  - Git push failure.

## 6. Anti-patterns
- **Manual Versioning**: Never manually edit `settings.json` and `git tag` separately. Use the script to ensure they are in sync.
- **Dirty Releases**: Never release from a dirty working directory. This ensures the released version matches exactly what is in the repository.
- **Force Pushing**: The script should not use `--force` for pushing, to avoid overwriting history.

## 7. Linked Test Functions
| TC ID | Test Function | File |
|-------|---------------|------|
| TC-REL-01 | `test_validate_version` | `../../tests/scripts/test_release.py` |
| TC-REL-02 | `test_update_version` | `../../tests/scripts/test_release.py` |
| TC-REL-03 | `test_run_git_commands` | `../../tests/scripts/test_release.py` |
