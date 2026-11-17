# Frontend

React 19 + Vite + TypeScript (strict) + Tailwind 4, in `frontend/`. Served from GitHub
Pages under `/moc-decision-support/`.

## Structure

```
src/
  App.tsx            shell: background, sidebar, top bar, lazy page area
  nav.ts             the page registry: path, label, group, icon, description, lazy component
  navigation.ts      hash routes (#/app/...), no router library; TAB_PATHS comes from nav.ts
  components/shell/  Sidebar (grouped navigation, collapse, phone drawer), TopBar (status, theme)
  store.ts           zustand: chat, graph context, active tab, the change under assessment, last case
  api.ts             axios client and functions for the original endpoints
  constants.ts       dropdown options
  components/ui.tsx  Card, KpiCard, StatTile, IconTile, Panel, Btn, Select, Spinner, ErrorBox, ...
  tabs/              one file per page (Overview is the home page)
  allocation/        api.ts (typed client), theme.ts, components.tsx
  case/              api.ts (typed client), components.tsx (Why panel, pipeline, checkpoints, review)
```

## Glass design system

Surfaces are frosted glass in both themes. They are defined once, as `--glass-*` variables
in `index.css` (dark under `:root`, light under `:root[data-theme='light']`), and used through
a few classes. A test checks every variable has a light value.

| Class | Use |
|---|---|
| `moc-glass-card` / `glass` | Cards and panels (`Card`, `Panel`, `StatTile` use it) |
| `glass-strong` | The sidebar and the top bar |
| `glass-tile` | Square frosted icon tiles (`IconTile`) and icon buttons |
| `glass-hover` | Lift on hover, for small items only, never for large panels |
| `moc-input-glass`, `moc-chip`, `moc-status-row` | Inputs, chips, status pills |

The blur needs something behind it: the canvas is a soft gradient with two drifting orbs
(`--glass-canvas`, `--glass-orb-*`). Without `backdrop-filter` support, surfaces fall back
to an opaque colour; with reduced motion, nothing drifts or lifts.

Two rules learned the hard way, both enforced by `tests/structure/test_frontend.py` or
noted here:

- **Write `backdrop-filter` only, never `-webkit-backdrop-filter`.** The CSS build adds the
  prefix itself; given both, it keeps only the prefixed one, which Chrome and Edge ignore,
  so every surface loses its blur without any error. (Tested.)
- **Component classes go in `@layer components`.** Unlayered CSS beats every Tailwind utility,
  so `glass-tile` (`display: grid`) silently overrode `lg:hidden`, and the glass border
  overrode `border-accent/25`.
- **No overflow container and no transform around the shell.** The sidebar, the top bar and
  the Change Case agent panel are `position: sticky` against the window, and the phone drawer
  is `position: fixed`; an `overflow` other than `visible`/`clip` or a transform on an ancestor
  breaks them. The root uses `overflow-clip`, and the shell animates opacity only.

## Conventions

- **Light and dark mode.** The theme is `data-theme` on `<html>`, set before first paint by a
  script in `index.html` (stored choice, else the operating-system setting) and switched by
  `ThemeToggle` (landing header and app top bar). `src/theme/ThemeProvider.tsx` keeps React in step.
- **Colours live only in `src/index.css`.** Dark values in `@theme static`, light values under
  `:root[data-theme='light']`. Use them as classes (`text-accent`, `bg-surface`, `border-ok/30`),
  as CSS references in style props (`cssVar('ok')`, `tint('warn', 30)`), or, for charts and the
  graph canvas, through `usePalette()`. In light mode `--color-white` points at dark ink, so the
  existing `text-white/60`-style utilities read as "ink at 60 %" in both themes. No hex or rgba in
  `.ts`/`.tsx` files (`tests/structure/test_frontend.py`).
- **Icons, not emojis.** Every icon is from `lucide-react`; emoji and symbol characters are not
  allowed in `frontend/src` (same test). Model replies are stripped of emojis before display
  (`MarkdownMessage.stripEmoji`), and the chat and agent prompts ask for none.
- **One logo component.** `components/SymmetraLogo.tsx` is the only place the Symmetra
  Systems logo is defined (icon from `assets/symmetra-mark.png`, wordmark as text). It is
  used in the landing-page header, hero and footer and in the sidebar of every app page.
  The browser-tab icon is `public/brand/symmetra-icon.png`.
- **Pages are registered once, in `nav.ts`.** The sidebar, top bar, routes and code splitting
  all read that list; each page is loaded on first visit (`React.lazy`).
- **Hash routing** so GitHub Pages needs no fallback page; `base: './'` in `vite.config.ts`.
- **The API address** comes from `VITE_API_URL` at build time; unset means same-origin `/api`.
- **One change, shared.** Smart Form, Risk, Cost and Decision Allocation read and write
  `store.currentChange` (type, asset, description, HAZOP/PSSR findings), so the flow
  carries through the tabs. The Risk tab hands over to Decision Allocation.
- **Overview is the home page.** "Enter Platform" opens `#/app/overview`: live counts, charts,
  the latest Change Case and service status, all from existing endpoints.
- **Change Case** is the guided flow, first in the Assess group.
  Live run state (agent statuses, activity feed) is in the store (`caseRun`, reduced by
  `src/case/run.ts`) so a run survives switching tabs; `streamCase` falls back to the plain
  endpoint when streaming is unavailable.
  Its human review lives in `localStorage` per run id and goes out only in the JSON export.
- **Print** uses the light theme (`printLight()`) and the `@media print` rules in `index.css`;
  mark screen-only controls with `no-print`.
- **Errors are shown.** Every mutation renders `ErrorBox`; a degraded answer
  (`llm_status: "unavailable"`) renders an amber notice.
- **No model numbers in the frontend.** The allocation tab fetches the model from
  `GET /api/allocation/model` and every score from the backend.
- **Typed where new.** `allocation/api.ts` types every response. The original `api.ts`
  returns untyped data (see the tech-debt tracker).
- **Strings from the database are escaped** before being used in HTML tooltips.

## Checks

`npm run build` runs `tsc` then the Vite build; it is the only frontend gate. There is no
ESLint configuration and no test runner (tech-debt tracker).
