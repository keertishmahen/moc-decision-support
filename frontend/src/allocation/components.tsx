/** Presentational pieces of the Decision Allocation tab. No data fetching here. */
import React from 'react'
import { ArrowRight, ArrowUp, ChevronRight, CircleCheck, CircleX } from 'lucide-react'
import { Card, SectionLabel } from '../components/ui'
import { cssVar, tint, type Token } from '../theme/palette'
import type {
  AllocationDimension, AllocationFactor, AllocationModel, AllocationResult, AxisAssessment,
  ImpactAssessment, LevelCode, ReferenceCases,
} from './api'
import {
  ALLOCATION_LABEL, ALLOCATION_MEANING, ALLOCATION_TONE, FACTOR_TONE, LEVEL_TONE,
  LEVELS_LEFT_RIGHT, LEVELS_TOP_DOWN, SOURCE_LABEL, fmtScore,
} from './theme'

const LABEL = 'text-[11px] font-semibold uppercase tracking-widest text-white/50'

// ── Axis selector ───────────────────────────────────────────────────────────
export function AxisField({ axis, model, value, onChange }: {
  axis: AxisAssessment | undefined
  model: AllocationModel['axes'][number]
  value: string
  onChange: (categoryId: string) => void
}) {
  const suggested = axis?.suggested ?? null
  const reference = axis?.reference ?? null
  const baseline = reference?.value ?? suggested?.value
  const changed = baseline !== undefined && value !== baseline
  const lowConfidence = !reference && suggested?.confidence === 'low'

  let origin = 'Your selection'
  let originTone: Token = 'accent2'
  if (!changed && reference) { origin = 'Reference characterisation'; originTone = 'accent' }
  else if (!changed && suggested) {
    origin = SOURCE_LABEL[suggested.source] ?? suggested.source
    originTone = lowConfidence ? 'warn' : 'ok'
  }
  const originColor = cssVar(originTone)

  return (
    <div className="moc-glass-card rounded-xl p-3" style={{ borderColor: lowConfidence && !changed ? tint('warn', 30) : undefined }}>
      <label className={`block ${LABEL} mb-1.5`} htmlFor={`axis-${model.id}`}>
        <span className="font-mono text-accent mr-1.5">{model.id}</span>{model.name}
        <span className="ml-1.5 normal-case tracking-normal font-normal text-white/30">{model.hint}</span>
      </label>
      <select id={`axis-${model.id}`} value={value} onChange={e => onChange(e.target.value)}
        className="moc-input-glass w-full rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none transition-colors">
        {model.categories.map(c => <option key={c.id} value={c.id} className="bg-surface">{c.name}</option>)}
      </select>
      <div className="mt-2 flex items-center gap-1.5 text-[11px]">
        <span className="h-1.5 w-1.5 rounded-full flex-shrink-0" style={{ background: originColor }} />
        <span style={{ color: originColor }} className="font-semibold">{origin}</span>
        {lowConfidence && !changed && <span className="text-amber-300/80">· please confirm</span>}
      </div>
      {suggested && (
        <p className="mt-1 text-[11px] leading-snug text-white/45">
          {reference && suggested.value !== reference.value
            ? <>Graph rule suggests <b className="text-white/70">{suggested.name}</b>: {suggested.evidence}</>
            : suggested.evidence}
        </p>
      )}
      {changed && baseline !== undefined && (
        <button type="button" onClick={() => onChange(baseline)}
          className="mt-1 text-[11px] text-accent hover:text-blue-300 transition-colors">
          Reset to {reference ? 'reference' : 'suggestion'}
        </button>
      )}
    </div>
  )
}

// ── Score tile ──────────────────────────────────────────────────────────────
export function ScoreTile({ dim }: { dim: AllocationDimension }) {
  const tone = LEVEL_TONE[dim.level]
  const color = cssVar(tone)
  const pct = Math.max(0, Math.min(100, dim.normalised * 100))
  const lowPct = (dim.low_boundary / dim.max) * 100
  const highPct = (dim.high_boundary / dim.max) * 100
  return (
    <div className="moc-glass-card rounded-2xl p-4" style={{ borderColor: tint(tone, 25) }}>
      <div className={LABEL}>{dim.name}</div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="text-2xl font-bold leading-none" style={{ color }}>{dim.score.toFixed(2)}</span>
        <span className="text-xs text-white/40 font-mono">/ {fmtScore(dim.max)}</span>
        <span className="ml-auto rounded-full border px-2 py-0.5 text-[10px] font-bold"
          style={{ color, borderColor: tint(tone, 35), background: tint(tone, 10) }}>{dim.level}</span>
      </div>
      <div className="relative mt-3 h-1.5 rounded-full bg-white/10" aria-hidden="true">
        <div className="absolute inset-y-0 left-0 rounded-full" style={{ width: `${pct}%`, background: color }} />
        <div className="absolute -top-1 h-3.5 w-px bg-white/50" style={{ left: `${lowPct}%` }} />
        <div className="absolute -top-1 h-3.5 w-px bg-white/50" style={{ left: `${highPct}%` }} />
      </div>
      <div className="mt-2 text-[11px] text-white/40">
        Boundaries {dim.low_boundary.toFixed(2)} / {dim.high_boundary.toFixed(2)} · margin {dim.margin.toFixed(2)}
      </div>
      <div className="mt-2 space-y-0.5">
        {dim.contributions.length === 0
          ? <div className="text-[11px] text-white/30">No selected category contributes.</div>
          : dim.contributions.map(c => (
            <div key={c.axis_id} className="flex justify-between gap-2 text-[11px] text-white/60">
              <span className="truncate">{c.category} <span className="text-white/30">· {c.axis}</span></span>
              <span className="font-mono text-white/70">+{fmtScore(c.weight)}</span>
            </div>
          ))}
      </div>
    </div>
  )
}

// ── 3×3 factor matrix (dimension level against the shared Impact level) ─────
export function FactorMatrix({ factor, matrix }: {
  factor: AllocationFactor
  matrix: AllocationModel['factor_matrix']
}) {
  const color = cssVar(FACTOR_TONE[factor.factor])
  return (
    <div className="moc-glass-card rounded-2xl p-4">
      <div className="flex items-baseline justify-between">
        <div className={LABEL}>{factor.dimension} factor</div>
        <div className="text-xl font-bold font-mono" style={{ color }}>{factor.factor}</div>
      </div>
      <div className="mt-3 grid grid-cols-[auto_repeat(3,1fr)] gap-1 text-center text-[11px]">
        {LEVELS_TOP_DOWN.map(row => (
          <React.Fragment key={row}>
            <div className={`pr-1.5 text-right font-mono self-center ${row === factor.level ? 'text-white font-bold' : 'text-white/35'}`}>{row}</div>
            {LEVELS_LEFT_RIGHT.map(col => {
              const cell = matrix[row][col]
              const active = row === factor.level && col === factor.impact_level
              const t = FACTOR_TONE[cell]
              return (
                <div key={col} className="rounded-md py-1.5 font-mono font-bold border"
                  aria-current={active ? 'true' : undefined}
                  style={{
                    color: active ? cssVar('canvas') : tint(t, 85),
                    background: active ? cssVar(t) : tint(t, 9),
                    borderColor: active ? cssVar(t) : 'transparent',
                  }}>{cell}</div>
              )
            })}
          </React.Fragment>
        ))}
        <div />
        {LEVELS_LEFT_RIGHT.map(col => (
          <div key={col} className={`font-mono pt-0.5 ${col === factor.impact_level ? 'text-white font-bold' : 'text-white/35'}`}>{col}</div>
        ))}
      </div>
      <div className="mt-1.5 flex items-center justify-center gap-1 text-[10px] text-white/35">
        Level of {factor.dimension} <ArrowUp className="h-2.5 w-2.5" strokeWidth={2} aria-hidden />
        <span className="mx-0.5">·</span>
        Level of Impact <ArrowRight className="h-2.5 w-2.5" strokeWidth={2} aria-hidden />
      </div>
    </div>
  )
}

// ── Recommendation banner ───────────────────────────────────────────────────
export function AllocationBanner({ result, status }: { result: AllocationResult; status: string }) {
  const tone = ALLOCATION_TONE[result.allocation]
  const color = cssVar(tone)
  const summary = result.reasons[result.reasons.length - 1]
  return (
    <div className="moc-glass-card rounded-2xl p-5" style={{ borderColor: tint(tone, 40), background: tint(tone, 7) }}>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div>
          <div className={LABEL}>Recommended allocation</div>
          <div className="mt-1 text-3xl font-bold tracking-tight" style={{ color }}>{ALLOCATION_LABEL[result.allocation]}</div>
          <div className="mt-1 text-sm text-white/60">{ALLOCATION_MEANING[result.allocation]}</div>
        </div>
        <div className="ml-auto text-right">
          <div className={LABEL}>Signature R / C / U</div>
          <div className="mt-1 flex justify-end gap-1.5 font-mono text-lg font-bold">
            {result.factors.map((f, i) => (
              <React.Fragment key={f.dimension_id}>
                {i > 0 && <span className="text-white/25">/</span>}
                <span style={{ color: cssVar(FACTOR_TONE[f.factor]) }}>{f.factor}</span>
              </React.Fragment>
            ))}
          </div>
          <div className="mt-1 text-[11px] text-white/40">Model v{result.model_version} · {status.replace(/-/g, ' ')}</div>
        </div>
      </div>
      <p className="mt-3 text-sm text-white/80">{summary}</p>
    </div>
  )
}

// ── Why this allocation ─────────────────────────────────────────────────────
export function Explanation({ result }: { result: AllocationResult }) {
  const perDimension = result.reasons.slice(0, -1)
  const flips = result.flips
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card>
        <SectionLabel>Why this allocation</SectionLabel>
        <ul className="space-y-2">
          {perDimension.map(r => (
            <li key={r} className="text-sm leading-relaxed text-white/75">{r}</li>
          ))}
        </ul>
      </Card>
      <Card>
        <SectionLabel>What would change it</SectionLabel>
        {flips.length === 0 ? (
          <p className="text-sm text-white/60">No single axis change moves this allocation. It is robust to any one characterisation being different.</p>
        ) : (
          <>
            <p className="text-sm text-white/60 mb-2">Changing one axis alone would move the recommendation:</p>
            <ul className="space-y-1">
              {flips.map(f => (
                <li key={`${f.axis_id}-${f.to}`} className="flex items-center justify-between gap-3 py-1.5 border-b border-white/5 last:border-0 text-xs">
                  <span className="text-white/70 inline-flex flex-wrap items-center gap-1"><span className="font-mono text-accent">{f.axis_id}</span> {f.axis}
                    <ArrowRight className="h-3 w-3" strokeWidth={2} aria-hidden /> <b className="text-white/90">{f.to_name}</b></span>
                  <span className="font-semibold flex-shrink-0" style={{ color: cssVar(ALLOCATION_TONE[f.allocation]) }}>{ALLOCATION_LABEL[f.allocation]}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </Card>
    </div>
  )
}

// ── Impact assessment from the knowledge graph ──────────────────────────────
const yesNo = (v: boolean | null) => (v === null ? 'Not recorded' : v ? 'Required' : 'Not required')

function Fact({ label, value, tone }: { label: string; value: React.ReactNode; tone?: Token }) {
  return (
    <div className="moc-glass-card rounded-xl p-3">
      <div className="text-[11px] text-white/40">{label}</div>
      <div className="mt-0.5 text-sm font-semibold" style={{ color: cssVar(tone ?? 'ink') }}>{value}</div>
    </div>
  )
}

export function ImpactSummary({ impact }: { impact: ImpactAssessment }) {
  const { asset, reach, safety, risk_assessment: ra, parameter, history } = impact
  const warn = (v: boolean | null): Token | undefined => (v ? 'warn' : v === false ? 'ok' : undefined)
  return (
    <Card className="space-y-3">
      <SectionLabel>Impact assessment · from the knowledge graph</SectionLabel>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Fact label="Target asset" value={<span className="font-mono">{asset.asset_id ?? '—'}</span>} />
        <Fact label="Equipment · criticality" value={`${asset.equipment_type ?? '—'} · ${asset.criticality ?? '—'}`}
          tone={(asset.criticality ?? 0) >= 5 ? 'danger' : undefined} />
        <Fact label="Downstream assets reached" value={reach.available ? `${reach.assets_affected} in ${reach.areas_reached.length} area(s)` : 'Unavailable'} />
        <Fact label="Risk assessment" value={ra ? `${ra.category ?? '—'} (${ra.overall_score ?? '—'})` : 'None on record'} />
        <Fact label="HAZOP" value={yesNo(safety.hazop_required)} tone={warn(safety.hazop_required)} />
        <Fact label="PSSR" value={yesNo(safety.pssr_required)} tone={warn(safety.pssr_required)} />
        <Fact label="Shutdown" value={yesNo(safety.shutdown_required)} tone={warn(safety.shutdown_required)} />
        <Fact label="MoCs on this asset" value={history.mocs_on_asset.length ? history.mocs_on_asset.join(', ') : 'None'} />
      </div>
      {parameter && (
        <p className="text-xs text-white/55">
          Parameter change: <span className="text-white/80">{parameter.old ?? '—'}</span>
          <ArrowRight className="mx-1 inline h-3 w-3 align-[-1px]" strokeWidth={2} aria-label="to" />
          <span className="text-white/80">{parameter.new ?? '—'}</span>
          {parameter.threshold ? <> · limit <span className="text-white/80">{parameter.threshold}</span></> : null}
        </p>
      )}
      {reach.available && reach.assets.length > 0 && (
        <details className="group">
          <summary className="cursor-pointer list-none inline-flex items-center gap-1 text-xs text-accent hover:text-accent-soft">
            <ChevronRight className="h-3.5 w-3.5 group-open:rotate-90 transition-transform" strokeWidth={2} aria-hidden />
            Dependency chain ({reach.assets_affected} assets)
          </summary>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {reach.assets.map(a => (
              <span key={a.asset_id} className="moc-chip rounded-full px-2 py-0.5 text-[11px] font-mono"
                style={{ color: cssVar((a.criticality ?? 0) >= 5 ? 'danger' : 'ink') }}
                title={`${a.equipment_type ?? ''} · criticality ${a.criticality ?? '—'} · ${a.area ?? ''}`}>
                {a.asset_id}<span className="text-white/35"> · {a.hops} hop{a.hops > 1 ? 's' : ''}</span>
              </span>
            ))}
          </div>
        </details>
      )}
    </Card>
  )
}

// ── Reference cases: thesis output next to this engine's output ─────────────
const DIMS = ['R', 'C', 'U', 'I'] as const

export function ReferenceCasesTable({ cases, onOpen }: { cases: ReferenceCases; onOpen: (mocId: string) => void }) {
  return (
    <Card>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <SectionLabel>Reference cases · thesis Table 2 reproduced</SectionLabel>
        <span className="text-xs font-semibold" style={{ color: cssVar(cases.reproduced === cases.total ? 'ok' : 'warn') }}>
          {cases.reproduced} of {cases.total} match the published output
        </span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[640px] text-xs">
          <thead>
            <tr className="text-left text-white/40">
              <th className="py-1.5 pr-2 font-semibold">Case</th>
              <th className="py-1.5 pr-2 font-semibold">Change</th>
              {DIMS.map(d => <th key={d} className="py-1.5 px-1 text-right font-semibold">{d}</th>)}
              <th className="py-1.5 px-2 font-semibold">Levels R/C/U/I</th>
              <th className="py-1.5 px-2 font-semibold">Signature</th>
              <th className="py-1.5 px-2 font-semibold">Allocation</th>
              <th className="py-1.5 pl-2 font-semibold">Thesis</th>
            </tr>
          </thead>
          <tbody>
            {cases.cases.map(c => (
              <tr key={c.case_id} className="border-t border-white/5 hover:bg-white/[0.03]">
                <td className="py-1.5 pr-2">
                  <button type="button" onClick={() => onOpen(c.moc_id)} className="font-mono text-accent hover:text-blue-300">{c.moc_id}</button>
                </td>
                <td className="py-1.5 pr-2 text-white/75">{c.title}</td>
                {DIMS.map(d => <td key={d} className="py-1.5 px-1 text-right font-mono text-white/80">{fmtScore(c.computed.scores[d])}</td>)}
                <td className="py-1.5 px-2 font-mono text-white/55">{DIMS.map(d => c.computed.levels[d] as LevelCode).join('/')}</td>
                <td className="py-1.5 px-2 font-mono text-white/80">{c.computed.signature}</td>
                <td className="py-1.5 px-2 font-semibold" style={{ color: cssVar(ALLOCATION_TONE[c.computed.allocation]) }}>{ALLOCATION_LABEL[c.computed.allocation]}</td>
                <td className="py-1.5 pl-2" style={{ color: cssVar(c.matches ? 'ok' : 'danger') }}>
                  <span className="inline-flex items-center gap-1">
                    {c.matches
                      ? <><CircleCheck className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />match</>
                      : <><CircleX className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />{c.differences.join(', ')}</>}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-[11px] leading-relaxed text-white/40">{cases.reconstruction_note}</p>
    </Card>
  )
}

// ── Model card ──────────────────────────────────────────────────────────────
export function ModelCard({ model, enumeration }: {
  model: AllocationModel
  enumeration?: { total: number; allocations: Record<string, number>; signatures_reached: number; signatures_possible: number }
}) {
  return (
    <Card>
      <SectionLabel>Model · v{model.version}</SectionLabel>
      <p className="text-sm text-white/75">{model.title}</p>
      <p className="mt-1 text-xs text-white/50">
        {model.attribution.author} — {model.attribution.work}. Supervisor: {model.attribution.supervisor}.
      </p>
      <p className="mt-2 text-xs text-white/60"><b className="text-white/80">Rule.</b> {model.allocation_rule.text}</p>
      {enumeration && (
        <p className="mt-2 text-xs text-white/60">
          <b className="text-white/80">Whole space.</b> {enumeration.total.toLocaleString()} characterisations:{' '}
          <span style={{ color: cssVar(ALLOCATION_TONE.AI_LED) }}>{enumeration.allocations.AI_LED} AI-led</span>,{' '}
          <span style={{ color: cssVar(ALLOCATION_TONE.AI_SUPPORTED) }}>{enumeration.allocations.AI_SUPPORTED} AI-supported</span>,{' '}
          <span style={{ color: cssVar(ALLOCATION_TONE.HUMAN_LED) }}>{enumeration.allocations.HUMAN_LED.toLocaleString()} human-led</span>;{' '}
          {enumeration.signatures_reached} of {enumeration.signatures_possible} signatures occur.
        </p>
      )}
      <details className="group mt-3">
        <summary className="cursor-pointer list-none inline-flex items-center gap-1 text-xs text-accent hover:text-accent-soft">
          <ChevronRight className="h-3.5 w-3.5 group-open:rotate-90 transition-transform" strokeWidth={2} aria-hidden />
          Weight matrix and thresholds
        </summary>
        <div className="mt-2 overflow-x-auto">
          <table className="w-full min-w-[420px] text-xs">
            <thead>
              <tr className="text-left text-white/40">
                <th className="py-1 pr-2 font-semibold">Axis · category</th>
                {model.dimensions.map(d => <th key={d.id} className="py-1 px-2 text-right font-semibold">{d.id}</th>)}
              </tr>
            </thead>
            <tbody>
              {model.axes.map(a => (
                <React.Fragment key={a.id}>
                  <tr className="border-t border-white/10">
                    <td colSpan={5} className="pt-2 pb-0.5 font-semibold text-white/70"><span className="font-mono text-accent">{a.id}</span> {a.name}</td>
                  </tr>
                  {a.categories.map(c => (
                    <tr key={c.id}>
                      <td className="py-0.5 pr-2 pl-4 text-white/60">{c.name}</td>
                      {model.dimensions.map(d => (
                        <td key={d.id} className={`py-0.5 px-2 text-right font-mono ${c.weights[d.id] ? 'text-white/85' : 'text-white/20'}`}>{fmtScore(c.weights[d.id] ?? 0)}</td>
                      ))}
                    </tr>
                  ))}
                </React.Fragment>
              ))}
              <tr className="border-t border-white/10 text-white/70">
                <td className="py-1 pr-2 font-semibold">Column maximum</td>
                {model.dimensions.map(d => <td key={d.id} className="py-1 px-2 text-right font-mono">{fmtScore(d.max)}</td>)}
              </tr>
              <tr className="text-white/55">
                <td className="py-0.5 pr-2">LOW | MED boundary</td>
                {model.dimensions.map(d => <td key={d.id} className="py-0.5 px-2 text-right font-mono">{d.low_boundary.toFixed(2)}</td>)}
              </tr>
              <tr className="text-white/55">
                <td className="py-0.5 pr-2">MED | HIGH boundary</td>
                {model.dimensions.map(d => <td key={d.id} className="py-0.5 px-2 text-right font-mono">{d.high_boundary.toFixed(2)}</td>)}
              </tr>
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[11px] text-white/40">{model.attribution.note}</p>
      </details>
    </Card>
  )
}
