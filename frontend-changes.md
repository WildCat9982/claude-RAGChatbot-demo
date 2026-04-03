# Frontend Code Quality Changes

## Summary

Added Prettier (auto-formatter) and ESLint (linter) to the frontend development workflow, plus a shell script for running quality checks from the project root.

---

## New Files

### `frontend/package.json`
Declares the project as a Node.js devtools project (private, no publish). Defines the following npm scripts:

| Script | What it does |
|--------|-------------|
| `npm run format` | Auto-format all frontend files with Prettier |
| `npm run format:check` | Check formatting without modifying files |
| `npm run lint` | Lint `script.js` with ESLint |
| `npm run lint:fix` | Auto-fix lint issues |
| `npm run quality` | Run both Prettier check and ESLint (CI use) |
| `npm run quality:fix` | Auto-fix formatting and lint issues |

DevDependencies added:
- `prettier@^3.3.3` — opinionated code formatter (frontend equivalent of black)
- `eslint@^9.9.0` — JavaScript linter
- `@eslint/js@^9.9.0` — ESLint recommended JS ruleset

### `frontend/.prettierrc`
Prettier configuration that codifies the existing style:
- 4-space indentation
- Print width: 100 characters
- Double quotes, semicolons, trailing commas (ES5)
- LF line endings

### `frontend/eslint.config.js`
ESLint flat config (ESLint v9 format) with:
- `@eslint/js` recommended rules as base
- Browser globals declared (`document`, `window`, `fetch`, `marked`, etc.)
- Key rules: `no-var` (error), `prefer-const` (warn), `eqeqeq` (error), `no-unused-vars` (warn)

### `frontend/.prettierignore`
Excludes `node_modules/` and `package-lock.json` from formatting.

### `frontend-quality.sh` (project root)
Convenience script for running all frontend quality checks from the project root.

```bash
# Check formatting and lint (no changes made)
./frontend-quality.sh

# Auto-fix all formatting and lint issues
./frontend-quality.sh --fix
```

The script auto-installs `node_modules` on first run if not already present.

---

## Modified Files

### `frontend/script.js`
- Removed two instances of consecutive blank lines (lines 33–34 and 44–45 in the original) to match Prettier's single-blank-line formatting rule.

---

## How to Use

**First-time setup** (installs devDependencies):
```bash
cd frontend && npm install
```

**Check formatting and lint before committing:**
```bash
./frontend-quality.sh
# or from frontend/:
npm run quality
```

**Auto-fix everything:**
```bash
./frontend-quality.sh --fix
# or from frontend/:
npm run quality:fix
```
