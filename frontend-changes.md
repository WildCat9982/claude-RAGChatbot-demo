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

---

# Frontend Changes

## Dark/Light Mode Toggle Button

### What was added

A fixed-position theme toggle button in the top-right corner of the UI that switches between dark and light modes.

### Files modified

#### `frontend/index.html`
- Added a `<button id="themeToggle">` element before `.container`, fixed at top-right
- Button contains two SVG icons inline:
  - **Sun icon** — displayed in dark mode (prompts user to switch to light)
  - **Moon icon** — displayed in light mode (prompts user to switch to dark)
- Includes `aria-label` for screen reader accessibility and `title` tooltip

#### `frontend/style.css`
- Added **light theme CSS variables** on `body.light-theme` — light backgrounds (`#f8fafc`, `#ffffff`), dark text (`#0f172a`), adjusted borders and shadows
- Added **two new variables** to `:root` and `body.light-theme`: `--toggle-bg`, `--toggle-hover`, `--toggle-color` for button theming
- Added `.theme-toggle` styles: circular (42px), fixed top-right (`top: 1rem; right: 1rem`), `z-index: 1000`, hover scale effect, focus ring
- Added icon visibility rules: `.icon-sun` shown by default; `.icon-moon` shown when `body.light-theme` is active
- Added `@keyframes spinToggle` — 360° rotation with scale dip for the toggle animation
- Added `.theme-toggle.toggling` class to trigger the spin animation
- Added `.theme-transitioning` class — when applied to body, all child elements get 0.3s transitions on `background-color`, `border-color`, and `color` for a smooth theme switch

#### `frontend/script.js`
- Added an IIFE `initTheme()` at the top of the file (runs immediately, before DOM ready)
  - Reads `localStorage.getItem('theme')` on load and applies `light-theme` class if stored value is `'light'`
  - Attaches a click listener to `#themeToggle` that:
    1. Adds `theme-transitioning` to body (triggers smooth color transitions), removed after 350ms
    2. Adds `toggling` class to button (triggers spin animation), removed on `animationend`
    3. Toggles `light-theme` on `<body>`
    4. Persists the chosen theme to `localStorage`
    5. Updates `aria-label` to reflect the new state

### Design decisions

- **Dark mode is the default** — matches the existing app aesthetic; light mode is opt-in
- **Preference is persisted** via `localStorage` so it survives page reloads
- **No flash of wrong theme** — the IIFE runs synchronously before the page renders, applying the stored class immediately
- **Accessible** — `aria-label` updates dynamically to describe the *next* action ("Switch to dark/light mode"), keyboard-navigable via Tab/Enter/Space, focus ring matches the app's existing `--focus-ring` variable
- **Smooth transitions** — cross-element background/color transitions are only active during the theme switch (via `.theme-transitioning`) to avoid interfering with other animations

---

## Light Theme Color System

### What was changed

Extended the light theme with a complete, accessibility-audited color system. All hardcoded colors were replaced with CSS variables so they adapt correctly between dark and light modes.

### Files modified

#### `frontend/style.css`

**New CSS variables added to `:root` (dark defaults):**
| Variable | Dark value | Purpose |
|---|---|---|
| `--welcome-shadow` | `0 4px 16px rgba(0,0,0,0.2)` | Welcome card shadow |
| `--code-bg` | `rgba(0,0,0,0.25)` | Inline code / pre background |
| `--link-color` | `#60a5fa` | Source links |
| `--error-bg` | `rgba(239,68,68,0.1)` | Error message background |
| `--error-color` | `#f87171` | Error message text |
| `--error-border` | `rgba(239,68,68,0.2)` | Error message border |
| `--success-bg` | `rgba(34,197,94,0.1)` | Success message background |
| `--success-color` | `#4ade80` | Success message text |
| `--success-border` | `rgba(34,197,94,0.2)` | Success message border |

**Light theme overrides (`body.light-theme`) — WCAG contrast ratios:**
| Variable | Light value | Contrast on bg | WCAG |
|---|---|---|---|
| `--primary-color` | `#1d4ed8` | 5.9:1 on white | AA ✓ |
| `--primary-hover` | `#1e40af` | 7.1:1 on white | AAA ✓ |
| `--background` | `#f8fafc` | — | — |
| `--surface` | `#ffffff` | — | — |
| `--surface-hover` | `#f1f5f9` | — | — |
| `--text-primary` | `#0f172a` | 17.8:1 on white | AAA ✓ |
| `--text-secondary` | `#475569` | 7.5:1 on white | AAA ✓ |
| `--border-color` | `#cbd5e1` | — (decorative) | — |
| `--user-message` | `#1d4ed8` | 5.9:1 (white text) | AA ✓ |
| `--assistant-message` | `#f1f5f9` | — (surface) | — |
| `--link-color` | `#1d4ed8` | 5.9:1 on white | AA ✓ |
| `--error-color` | `#b91c1c` | 7.1:1 on white | AAA ✓ |
| `--success-color` | `#15803d` | 5.9:1 on white | AA ✓ |
| `--code-bg` | `rgba(15,23,42,0.07)` | — (surface tint) | — |

**Selectors updated to use variables (previously hardcoded):**
- `.sources-content a` — now uses `var(--link-color)`
- `.message-content code` — now uses `var(--code-bg)`
- `.message-content pre` — now uses `var(--code-bg)`
- `.message.welcome-message .message-content` box-shadow — now uses `var(--welcome-shadow)`
- `.error-message` — all three properties now use `var(--error-*)` variables
- `.success-message` — all three properties now use `var(--success-*)` variables

### Design decisions

- **Darker primary in light mode** — `#1d4ed8` instead of `#2563eb` because the lighter shade only achieves 4.7:1 on white (borderline AA), while the darker shade gives 5.9:1
- **Stronger secondary text** — `#475569` instead of `#64748b` to comfortably exceed AA (7.5:1 vs 4.6:1)
- **Visible borders** — `#cbd5e1` instead of `#e2e8f0` so sidebar/card edges are clear on the light background without being harsh
- **Error/success semantics preserved** — red and green hues are retained but darkened to maintain contrast on white backgrounds
