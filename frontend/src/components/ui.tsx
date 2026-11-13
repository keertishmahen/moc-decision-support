import React from 'react'
import { motion } from 'framer-motion'
import { CircleCheck, CircleHelp, TriangleAlert } from 'lucide-react'
import { cssVar, ink, tint, type Token } from '../theme/palette'

// ── Card ──────────────────────────────────────────────────────────────────
export const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`moc-glass-card rounded-2xl p-4 ${className}`}>
    {children}
  </div>
)

// ── KPI Card ──────────────────────────────────────────────────────────────
export const KpiCard = ({ label, value, sub, tone = 'accent' }: {
  label: string; value: React.ReactNode; sub?: string; tone?: Token
}) => (
  <motion.div
    whileHover={{ y: -2 }}
    className="moc-glass-card rounded-2xl p-4 transition-colors"
  >
    <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50 mb-2">{label}</div>
    <div className="text-2xl font-bold leading-none" style={{ color: cssVar(tone) }}>{value}</div>
    {sub && <div className="text-[12px] text-white/40 mt-1">{sub}</div>}
  </motion.div>
)

// ── Risk Badge ────────────────────────────────────────────────────────────
const RISK_STYLES: Record<string, string> = {
  Low:      'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  Medium:   'bg-amber-500/15 text-amber-400 border-amber-500/30',
  High:     'bg-red-500/15 text-red-400 border-red-500/30',
  Critical: 'bg-red-600/25 text-red-400 border-red-600/40',
  Unknown:  'bg-white/10 text-white/50 border-white/20',
}
export const RiskBadge = ({ rating }: { rating: string }) => (
  <span className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold border backdrop-blur-sm ${RISK_STYLES[rating] ?? RISK_STYLES.Unknown}`}>
    {rating}
  </span>
)

// ── Section Label ─────────────────────────────────────────────────────────
export const SectionLabel = ({ children }: { children: React.ReactNode }) => (
  <div className="text-[11px] font-semibold uppercase tracking-widest text-accent mb-2">{children}</div>
)

// ── Button ────────────────────────────────────────────────────────────────
export const Btn = ({ children, onClick, loading, disabled, variant = 'primary', className = '', 'aria-label': ariaLabel }: {
  children: React.ReactNode; onClick?: () => void; loading?: boolean
  disabled?: boolean; variant?: 'primary' | 'ghost'; className?: string
  'aria-label'?: string
}) => {
  const base = 'inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed'
  const styles = {
    primary: 'moc-btn-primary text-white hover:-translate-y-0.5',
    ghost:   'moc-glass bg-white/[0.04] border border-white/12 text-white/70 hover:bg-white/[0.08] hover:text-white',
  }
  return (
    <button className={`${base} ${styles[variant]} ${className}`} onClick={onClick} disabled={disabled || loading} aria-label={ariaLabel}>
      {loading ? <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : null}
      {children}
    </button>
  )
}

// ── Select ────────────────────────────────────────────────────────────────
export const Select = ({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void; options: string[]
}) => (
  <div>
    <label className="block text-[11px] font-semibold uppercase tracking-widest text-white/50 mb-1.5">{label}</label>
    <select value={value} onChange={e => onChange(e.target.value)}
      className="moc-input-glass w-full rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none transition-colors">
      {options.map(o => <option key={o} value={o} className="bg-surface">{o}</option>)}
    </select>
  </div>
)

// ── Textarea ──────────────────────────────────────────────────────────────
export const Textarea = ({ label, value, onChange, placeholder, rows = 4 }: {
  label?: string; value: string; onChange: (v: string) => void; placeholder?: string; rows?: number
}) => (
  <div>
    {label && <label className="block text-[11px] font-semibold uppercase tracking-widest text-white/50 mb-1.5">{label}</label>}
    <textarea value={value} onChange={e => onChange(e.target.value)} rows={rows} placeholder={placeholder}
      className="moc-input-glass w-full rounded-xl px-3 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none transition-colors resize-none" />
  </div>
)

// ── Input ─────────────────────────────────────────────────────────────────
export const Input = ({ value, onChange, placeholder, onKeyDown }: {
  value: string; onChange: (v: string) => void; placeholder?: string; onKeyDown?: (e: React.KeyboardEvent) => void
}) => (
  <input value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} onKeyDown={onKeyDown}
    className="moc-input-glass w-full rounded-xl px-3 py-2.5 text-sm text-white placeholder-white/25 focus:outline-none transition-colors" />
)

// ── Error box ─────────────────────────────────────────────────────────────
export const ErrorBox = ({ error, title = 'Something went wrong' }: { error: unknown; title?: string }) => {
  if (!error) return null
  const message = error instanceof Error ? error.message : String(error)
  return (
    <div role="alert" className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
      <div className="font-semibold text-red-200">{title}</div>
      <div className="mt-0.5 text-red-300/90 break-words">{message}</div>
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────────────────────
export const Spinner = ({ text = 'Loading…' }: { text?: string }) => (
  <div className="flex items-center gap-3 text-white/50 text-sm py-6 justify-center">
    <span className="w-5 h-5 border-2 border-white/20 border-t-accent rounded-full animate-spin" />
    {text}
  </div>
)

// ── Gauge (SVG arc) ───────────────────────────────────────────────────────
export const Gauge = ({ value, max = 100, label, tone = 'accent', prefix = '', suffix = '' }: {
  value: number; max?: number; label: string; tone?: Token; prefix?: string; suffix?: string
}) => {
  const safeMax = Number.isFinite(max) && max > 0 ? max : 1
  const pct = Math.max(0, Math.min(value / safeMax, 1))
  const r = 52, cx = 64, cy = 64
  const startAngle = -210, endAngle = 30
  const totalArc = endAngle - startAngle
  const angle = startAngle + totalArc * pct
  const toRad = (d: number) => (d * Math.PI) / 180
  const arcPath = (a1: number, a2: number) => {
    const x1 = cx + r * Math.cos(toRad(a1)), y1 = cy + r * Math.sin(toRad(a1))
    const x2 = cx + r * Math.cos(toRad(a2)), y2 = cy + r * Math.sin(toRad(a2))
    const large = a2 - a1 > 180 ? 1 : 0
    return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`
  }
  return (
    <div className="flex flex-col items-center">
      <svg width="128" height="100" viewBox="0 0 128 100">
        <path d={arcPath(startAngle, endAngle)} fill="none" style={{ stroke: ink(8) }} strokeWidth="8" strokeLinecap="round" />
        {pct > 0 && <path d={arcPath(startAngle, angle)} fill="none" style={{ stroke: cssVar(tone) }} strokeWidth="8" strokeLinecap="round" />}
        <text x={cx} y={cy + 8} textAnchor="middle" style={{ fill: cssVar('ink') }} fontSize="16" fontWeight="700" fontFamily="Inter">
          {prefix}{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : value}{suffix}
        </text>
      </svg>
      <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50 -mt-2">{label}</div>
    </div>
  )
}

// ── Flag tile (Yes / No / Unknown review needs) ───────────────────────────
/** A review flag such as "HAZOP required": Yes is a caution, No is clear, anything else is unknown. */
export const FlagTile = ({ label, value, compact = false }: { label: string; value: string | null | undefined; compact?: boolean }) => {
  const v = (value ?? '').toString().trim().toLowerCase()
  const yes = ['yes', 'true', 'triggered', 'required'].includes(v)
  const no = ['no', 'false', 'not required'].includes(v)
  const tone: Token = yes ? 'warn' : no ? 'ok' : 'slate'
  const Icon = yes ? TriangleAlert : no ? CircleCheck : CircleHelp
  const text = yes ? 'Yes' : no ? 'No' : (value || 'Unknown')
  return (
    <div className={`moc-glass-card rounded-2xl flex flex-col items-center justify-center gap-1.5 ${compact ? 'p-3' : 'p-4 min-h-[110px]'}`}
      style={{ borderColor: tint(tone, 35) }}>
      <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50 text-center">{label}</div>
      <div className={`flex items-center gap-1.5 font-bold ${compact ? 'text-lg' : 'text-xl'}`} style={{ color: cssVar(tone) }}>
        <Icon className={compact ? 'h-4 w-4' : 'h-5 w-5'} strokeWidth={2} aria-hidden />
        {text}
      </div>
    </div>
  )
}

// ── Confidence Bar ────────────────────────────────────────────────────────
export const CIBar = ({ estimate, low, high, label, prefix = '', suffix = '' }: {
  estimate: number; low: number; high: number; label: string; prefix?: string; suffix?: string
}) => {
  const range = high - low || 1
  const pct = ((estimate - low) / range) * 100
  return (
    <div>
      <div className="flex justify-between text-[11px] text-white/50 mb-1">
        <span>{label}</span>
        <span className="font-semibold text-accent">{prefix}{estimate.toLocaleString(undefined, { maximumFractionDigits: 1 })}{suffix}</span>
      </div>
      <div className="relative h-2 rounded-full bg-white/8 overflow-hidden border border-white/5">
        <div className="absolute inset-y-0 rounded-full bg-accent/30"
          style={{ left: '0%', right: '0%' }} />
        <div className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-accent border-2 border-white/30 shadow-[0_0_10px_var(--color-accent)]"
          style={{ left: `calc(${pct}% - 6px)` }} />
      </div>
      <div className="flex justify-between text-[10px] text-white/30 mt-0.5">
        <span>{prefix}{low.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        <span>{prefix}{high.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
      </div>
    </div>
  )
}
