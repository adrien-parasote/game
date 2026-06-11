#!/usr/bin/env python3
"""
detect_subproject.py — Détecte le sous-projet cible pour VERIFY.

Priorité de détection :
1. Argument explicite : --subproject game | tools | all
2. Fichiers staged (git diff --cached) : premier sous-projet touché
3. Fichiers modifiés non staged (git diff) : premier sous-projet touché
4. Dernier commit : premier sous-projet touché
5. Fallback : "all" (les deux sous-projets)

Retourne sur stdout : "game", "tools", ou "all"
Exit code 0 toujours (fallback vers "all" si détection impossible).

Usage :
    python detect_subproject.py
    python detect_subproject.py --subproject game
    python detect_subproject.py --verbose
"""

import argparse
import subprocess
import sys
from pathlib import Path


SUBPROJECTS = {
    "game": "game/",
    "tools": "tools/",
}

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]  # .agents/skills/verification-loop/scripts/ -> workspace root


def run_git(args: list[str]) -> list[str]:
    """Run a git command and return non-empty lines, or [] on failure."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=WORKSPACE_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return []
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def detect_from_files(files: list[str]) -> str | None:
    """Given a list of file paths, return the first matching subproject or None."""
    for f in files:
        for name, prefix in SUBPROJECTS.items():
            if f.startswith(prefix):
                return name
    return None


def detect_subproject(explicit: str | None, verbose: bool) -> str:
    """
    Detect which subproject to verify.

    Returns "game", "tools", or "all".
    """

    # 1. Explicit override
    if explicit:
        if explicit not in (*SUBPROJECTS.keys(), "all"):
            print(f"[detect_subproject] ⚠️  Unknown subproject '{explicit}'. Using 'all'.", file=sys.stderr)
            return "all"
        if verbose:
            print(f"[detect_subproject] Explicit override: {explicit}", file=sys.stderr)
        return explicit

    # 2. Staged files
    staged = run_git(["diff", "--cached", "--name-only"])
    if verbose and staged:
        print(f"[detect_subproject] Staged files: {staged[:5]}", file=sys.stderr)
    if staged:
        found = detect_from_files(staged)
        if found:
            if verbose:
                print(f"[detect_subproject] Detected from staged files: {found}", file=sys.stderr)
            return found

    # 3. Unstaged modified files
    unstaged = run_git(["diff", "--name-only"])
    if verbose and unstaged:
        print(f"[detect_subproject] Unstaged files: {unstaged[:5]}", file=sys.stderr)
    if unstaged:
        found = detect_from_files(unstaged)
        if found:
            if verbose:
                print(f"[detect_subproject] Detected from unstaged files: {found}", file=sys.stderr)
            return found

    # 4. Last commit files
    last_commit = run_git(["diff", "--name-only", "HEAD~1", "HEAD"])
    if verbose and last_commit:
        print(f"[detect_subproject] Last commit files: {last_commit[:5]}", file=sys.stderr)
    if last_commit:
        found = detect_from_files(last_commit)
        if found:
            if verbose:
                print(f"[detect_subproject] Detected from last commit: {found}", file=sys.stderr)
            return found

    # 5. Fallback
    if verbose:
        print("[detect_subproject] No subproject detected — fallback to 'all'.", file=sys.stderr)
    return "all"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect which subproject to run VERIFY on.",
    )
    parser.add_argument(
        "--subproject",
        choices=[*SUBPROJECTS.keys(), "all"],
        default=None,
        help="Explicit override: game | tools | all",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detection reasoning to stderr",
    )
    args = parser.parse_args()

    result = detect_subproject(args.subproject, args.verbose)
    print(result)


if __name__ == "__main__":
    main()
