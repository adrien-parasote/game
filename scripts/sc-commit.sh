#!/usr/bin/env bash
# sc-commit.sh — Stream Coding commit wrapper
# Usage: ./scripts/sc-commit.sh "type(scope): message" [files...]
#        ./scripts/sc-commit.sh -F /tmp/msg.txt [files...]
#
# Automatically creates the .sc-learn-eval sentinel required by the
# Antigravity sandbox commit gate, then runs git commit.
#
# Examples:
#   ./scripts/sc-commit.sh "feat(engine): add feature"
#   ./scripts/sc-commit.sh -F /tmp/msg.txt
#   ./scripts/sc-commit.sh "fix(ui): fix button" src/ui/button.py tests/ui/test_button.py

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
SENTINEL="${REPO_ROOT}/.sc-learn-eval"

# 1. Create sentinel
echo "done=$(date -Iseconds)" > "${SENTINEL}"
echo "✅ Sentinel created: ${SENTINEL}"

# 2. Parse args — support -F <file> or inline message
if [[ "$1" == "-F" ]]; then
    MSG_FILE="$2"
    shift 2
    # Stage remaining files if provided
    if [[ $# -gt 0 ]]; then
        git add "$@"
    fi
    git commit -F "${MSG_FILE}"
else
    MSG="$1"
    shift
    # Stage remaining files if provided
    if [[ $# -gt 0 ]]; then
        git add "$@"
    fi
    git commit -m "${MSG}"
fi
