import argparse
import json
import os
import re
import subprocess
import sys


def validate_version(version):
    """Validate version format (SemVer-ish)."""
    # Simple regex for SemVer: x.y.z(-suffix)?
    pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$"
    return re.match(pattern, version) is not None


def update_version(settings_path, new_version):
    """Update version in settings.json."""
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Settings file not found: {settings_path}")

    with open(settings_path) as f:
        data = json.load(f)

    data["version"] = new_version

    with open(settings_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print(f"Bumped {settings_path} to version {new_version}")  # noqa: P5


def run_command(cmd, dry_run=False):
    """Run a shell command and return its output."""
    if dry_run:
        print(f"[DRY RUN] Would run: {' '.join(cmd)}")  # noqa: P5
        return str()  # noqa: P6

    print(f"Running: {' '.join(cmd)}")  # noqa: P5
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)  # noqa: P5
        sys.exit(result.returncode)
    return result.stdout.strip()


def run_git_commands(version, dry_run=False):
    """Run git add, commit, tag, and push."""
    # 1. Check if working directory is clean
    status = run_command(["git", "status", "--porcelain"])
    # If settings.json is the only change, we can proceed
    if status and status.strip() != "M game/settings.json":
        print(f"Error: Working directory is dirty:\n{status}", file=sys.stderr)  # noqa: P5
        if not dry_run:
            sys.exit(1)

    # 2. Check if tag already exists
    tags = run_command(["git", "tag", "-l", version])
    if tags:
        print(f"Error: Tag {version} already exists.", file=sys.stderr)  # noqa: P5
        if not dry_run:
            sys.exit(1)

    # 3. Get current branch
    branch = run_command(["git", "branch", "--show-current"])
    if not branch:
        print("Error: Could not determine current branch.", file=sys.stderr)  # noqa: P5
        if not dry_run:
            sys.exit(1)

    # 4. Git operations
    run_command(["git", "add", "game/settings.json"], dry_run=dry_run)
    run_command(["git", "commit", "-m", f"chore: bump version to {version}"], dry_run=dry_run)
    run_command(["git", "tag", version], dry_run=dry_run)
    run_command(["git", "push", "origin", branch], dry_run=dry_run)
    run_command(["git", "push", "origin", version], dry_run=dry_run)

    print(f"Successfully released version {version} on branch {branch}")  # noqa: P5


def main():
    parser = argparse.ArgumentParser(description="Release a new version of the game.")
    parser.add_argument("version", help="The new version string (e.g., 0.6.1)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without doing it")
    args = parser.parse_args()

    if not validate_version(args.version):
        print(f"Error: Invalid version format '{args.version}'. Must be x.y.z", file=sys.stderr)  # noqa: P5
        sys.exit(1)

    # Go up 2 directories from scripts/build/release.py to reach workspace root
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    settings_path = os.path.join(root_dir, "game", "settings.json")

    try:
        if not args.dry_run:
            update_version(settings_path, args.version)
        else:
            print(f"[DRY RUN] Would set version in settings.json to {args.version}")  # noqa: P5

        run_git_commands(args.version, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)  # noqa: P5
        sys.exit(1)


if __name__ == "__main__":
    main()
