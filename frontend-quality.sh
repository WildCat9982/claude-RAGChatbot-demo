#!/usr/bin/env bash
# Frontend code quality checks
# Run from the project root: ./frontend-quality.sh
# Options:
#   --fix   auto-fix formatting and lint issues

set -e

FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"
FIX=false

for arg in "$@"; do
    case $arg in
        --fix) FIX=true ;;
    esac
done

echo "==> Checking frontend dependencies..."
if ! command -v node &>/dev/null; then
    echo "ERROR: Node.js is not installed. Install it from https://nodejs.org" >&2
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "==> Installing frontend devDependencies..."
    (cd "$FRONTEND_DIR" && npm install)
fi

cd "$FRONTEND_DIR"

if $FIX; then
    echo "==> Formatting with Prettier..."
    npx prettier --write .
    echo "==> Fixing lint issues with ESLint..."
    npx eslint --fix . || true
    echo "==> Done. All fixes applied."
else
    echo "==> Checking formatting with Prettier..."
    npx prettier --check .

    echo "==> Linting with ESLint..."
    npx eslint .

    echo "==> All quality checks passed."
fi