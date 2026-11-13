/**
 * Colours as JavaScript values, for the few places that cannot use a CSS class:
 * chart fills, the knowledge-graph canvas, and "colour + alpha" patterns.
 *
 * Nothing is defined here. Every value is read from the colour tokens in src/index.css,
 * so both themes stay in one place and cannot drift apart.
 */
import { useMemo } from 'react'
import { useTheme } from './ThemeProvider'

const TOKENS = [
  'canvas', 'surface', 'surface-2', 'ink', 'accent', 'accent-soft', 'accent2', 'accent2-soft', 'accent2-strong',
  'highlight', 'ok', 'warn', 'danger', 'critical', 'slate', 'slate-dim', 'on-accent',
  'node-moc', 'node-asset', 'node-hazard', 'node-workorder', 'node-personnel', 'node-risk', 'node-lesson',
  'node-hazop', 'node-pssr', 'node-query', 'node-default', 'node-characterisation', 'node-category',
  'node-mode', 'node-dimension',
] as const

export type Token = (typeof TOKENS)[number]
export type Palette = Record<Token, string>

/**
 * CSS references for inline styles. These follow the theme automatically, with no re-render.
 * Prefer them over palette values wherever a style prop is enough.
 */
export const cssVar = (t: Token) => `var(--color-${t})`

/** The token mixed with transparency, e.g. tint('ok', 25) for a 25 % green border. */
export const tint = (t: Token, pct: number) => `color-mix(in srgb, var(--color-${t}) ${pct}%, transparent)`

/** Foreground ink at a given strength (white in dark mode, near-black in light mode). */
export const ink = (pct: number) => `color-mix(in srgb, var(--color-white) ${pct}%, transparent)`

/** Severity / rating names mapped to tokens. */
export function severityToken(level: string | null | undefined): Token {
  switch ((level ?? '').toLowerCase()) {
    case 'low':
      return 'ok'
    case 'medium':
    case 'med':
      return 'warn'
    case 'high':
      return 'danger'
    case 'critical':
      return 'critical'
    default:
      return 'slate'
  }
}

/** Read every token from the document's current theme. Values are 6-digit hex, so `color + '40'` works. */
export function readPalette(): Palette {
  const style = getComputedStyle(document.documentElement)
  const out = {} as Palette
  for (const t of TOKENS) out[t] = style.getPropertyValue(`--color-${t}`).trim() || 'gray'
  return out
}

/** The palette for the current theme; recomputed when the theme changes. */
export function usePalette(): Palette {
  const { theme } = useTheme()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  return useMemo(() => readPalette(), [theme])
}

/** Shared Recharts styling for the current theme. */
export function chartStyle(p: Palette) {
  return {
    tooltip: { background: p.surface, border: `1px solid ${p.accent}4d`, borderRadius: 8, color: p.ink, fontSize: 12 },
    tooltipLabel: { color: p.ink },
    tooltipItem: { color: p.ink },
    tick: { fill: p.slate, fontSize: 11 },
    smallTick: { fill: p.slate, fontSize: 10 },
    cursor: { fill: `${p.accent}14` },
  }
}

/** Severity colour as a palette value (for chart fills and canvas). */
export function severityColor(p: Palette, level: string | null | undefined): string {
  return p[severityToken(level)]
}
