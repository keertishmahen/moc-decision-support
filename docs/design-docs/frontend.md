# Frontend

React 19 + Vite + TypeScript (strict) + Tailwind 4, in `frontend/`. Served from GitHub
Pages under `/moc-decision-support/`.

## Structure

```
src/
  App.tsx            shell: sidebar, tab bar, panel area
  navigation.ts      hash routes (#/app/...), no router library
  store.ts           zustand: chat, graph context, active tab, the change under assessment
  api.ts             axios client and functions for the original endpoints
  constants.ts       dropdown options
  components/ui.tsx  Card, KpiCard, Btn, Select, Textarea, Spinner, ErrorBox, ...
  tabs/              one file per tab
  allocation/        api.ts (typed client), theme.ts, components.tsx
```

## Conventions

- **One logo component.** `components/SymmetraLogo.tsx` is the only place the Symmetra
  Systems logo is defined (icon from `assets/symmetra-mark.png`, wordmark as text). It is
  used in the landing-page header, hero and footer and in the sidebar of every app page.
  The browser-tab icon is `public/brand/symmetra-icon.png`.
- **Tabs are registered by index.** `TABS` and `panels` in `App.tsx` and `TAB_PATHS` in
  `navigation.ts` must stay in the same order.
- **Hash routing** so GitHub Pages needs no fallback page; `base: './'` in `vite.config.ts`.
- **The API address** comes from `VITE_API_URL` at build time; unset means same-origin `/api`.
- **One change, shared.** Smart Form, Risk, Cost and Decision Allocation read and write
  `store.currentChange` (type, asset, description, HAZOP/PSSR findings), so the flow
  carries through the tabs. The Risk tab hands over to Decision Allocation.
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
