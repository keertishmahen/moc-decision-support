import React from 'react'
import { motion } from 'framer-motion'

// ── Card ──────────────────────────────────────────────────────────────────
export const Card = ({ children, className = '' }: { children: React.ReactNode; className?: string }) => (
  <div className={`moc-glass-card rounded-2xl p-4 ${className}`}>
    {children}
  </div>
)

// ── KPI Card ──────────────────────────────────────────────────────────────
export const KpiCard = ({ label, value, sub, color = '#4f8ef7' }: {
  label: string; value: React.ReactNode; sub?: string; color?: string
}) => (
  <motion.div
    whileHover={{ y: -2, borderColor: 'rgba(79,142,247,0.4)' }}
    className="moc-glass-card rounded-2xl p-4 transition-colors"
  >
    <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50 mb-2">{label}</div>
    <div className="text-2xl font-bold leading-none" style={{ color }}>{value}</div>
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
  <div className="text-[11px] font-semibold uppercase tracking-widest text-[#4f8ef7] mb-2">{children}</div>
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
      {options.map(o => <option key={o} value={o} className="bg-[#0d1220]">{o}</option>)}
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

// ── Spinner ───────────────────────────────────────────────────────────────
export const Spinner = ({ text = 'Loading…' }: { text?: string }) => (
  <div className="flex items-center gap-3 text-white/50 text-sm py-6 justify-center">
    <span className="w-5 h-5 border-2 border-white/20 border-t-[#4f8ef7] rounded-full animate-spin" />
    {text}
  </div>
)

// ── Gauge (SVG arc) ───────────────────────────────────────────────────────
export const Gauge = ({ value, max = 100, label, color = '#4f8ef7', prefix = '', suffix = '' }: {
  value: number; max?: number; label: string; color?: string; prefix?: string; suffix?: string
}) => {
  const pct = Math.min(value / max, 1)
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
        <path d={arcPath(startAngle, endAngle)} fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="8" strokeLinecap="round" />
        {pct > 0 && <path d={arcPath(startAngle, angle)} fill="none" stroke={color} strokeWidth="8" strokeLinecap="round" />}
        <text x={cx} y={cy + 8} textAnchor="middle" fill="#e8eeff" fontSize="16" fontWeight="700" fontFamily="Inter">
          {prefix}{typeof value === 'number' ? value.toLocaleString(undefined, { maximumFractionDigits: 0 }) : value}{suffix}
        </text>
      </svg>
      <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50 -mt-2">{label}</div>
    </div>
  )
}

// ── Binary Card ───────────────────────────────────────────────────────────
export const BinaryCard = ({ label, value }: { label: string; value: string }) => {
  const yes = ['yes','true','triggered','required'].includes(value?.toLowerCase())
  const color = yes ? '#fbbf24' : '#34d399'
  const icon  = yes ? '⚠' : '✓'
  return (
    <div className="moc-glass-card rounded-2xl p-4 flex flex-col items-center justify-center gap-2 min-h-[120px]"
      style={{ borderColor: color + '55', boxShadow: `0 0 28px ${color}18` }}>
      <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50">{label}</div>
      <div className="text-2xl font-bold" style={{ color }}>{icon} {value}</div>
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
        <span className="font-semibold text-[#4f8ef7]">{prefix}{estimate.toLocaleString(undefined, { maximumFractionDigits: 1 })}{suffix}</span>
      </div>
      <div className="relative h-2 rounded-full bg-white/8 overflow-hidden border border-white/5">
        <div className="absolute inset-y-0 rounded-full bg-[#4f8ef7]/30"
          style={{ left: '0%', right: '0%' }} />
        <div className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-[#4f8ef7] border-2 border-white/30 shadow-[0_0_10px_rgba(79,142,247,0.6)]"
          style={{ left: `calc(${pct}% - 6px)` }} />
      </div>
      <div className="flex justify-between text-[10px] text-white/30 mt-0.5">
        <span>{prefix}{low.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
        <span>{prefix}{high.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
      </div>
    </div>
  )
}
