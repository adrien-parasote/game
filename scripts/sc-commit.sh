#!/usr/bin/env bash
# sc-commit.sh — Stream Coding commit wrapper
# Usage (all forms callable by both agent and user):
#
#   Stage then commit with inline message:
#     ./scripts/sc-commit.sh "type(scope): message" [file1 file2 ...]
#
#   Commit with message file (pre-staged files):
#     ./scripts/sc-commit.sh -F /tmp/msg.txt
#
#   Allow empty commit (testing):
#     ./scripts/sc-commit.sh --empty "type(scope): message"
#
# Automatically creates .sc-learn-eval sentinel (Antigravity sandbox gate).

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
SENTINEL="${REPO_ROOT}/.sc-learn-eval"

# 1. Create sentinel
echo "done=$(date -Iseconds)" > "${SENTINEL}"
echo "✅ Sentinel: ${SENTINEL}"

# 2. Parse mode
if [[ "$1" == "-F" ]]; then
    # Message from file, files already staged by caller
    git commit -F "$2"
elif [[ "$1" == "--empty" ]]; then
    # Empty commit (testing / placeholder)
    git commit --allow-empty -m "$2"
else
    # Inline message — remaining args are files to stage
    MSG="$1"
    shift
    if [[ $# -gt 0 ]]; then
        git add "$@"
    fi
    git commit -m "${MSG}"
fi
