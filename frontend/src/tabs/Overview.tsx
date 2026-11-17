/**
 * Overview — the dashboard home. Live figures from the knowledge graph and the allocation
 * model, the latest Change Case, service status and the platform's building blocks.
 * Read-only; every panel handles its own loading and failure.
 */
import React, { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  ArrowRight, Boxes, BrainCircuit, CircleDollarSign, FileStack, Gauge as GaugeIcon, LayoutDashboard,
  Network, ScanSearch, Scale, ShieldCheck, Sparkles, Workflow, Bot, Activity, type LucideIcon,
} from 'lucide-react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { getAssets, getMocs } from '../api'
import { getAllocationCases, getAllocationMocs, type AllocationCode } from '../allocation/api'
import { ALLOCATION_LABEL, ALLOCATION_TONE } from '../allocation/theme'
import { Btn, ErrorBox, IconTile, Panel, Spinner, StatTile } from '../components/ui'
import { ServicePill, useHealth } from '../components/shell/TopBar'
import { navigate, tabIndex, PATH_CHANGE_CASE } from '../navigation'
import { useStore } from '../store'
import { chartStyle, cssVar, usePalette, type Token } from '../theme/palette'

interface MocRow { moc_id: string; title: string | null; change_type: string | null; cost: number | null; asset_id: string | null }
interface AssetRow { id: string; type: string | null; criticality: number | null; area: string | null }

const CODES: AllocationCode[] = ['AI_LED', 'AI_SUPPORTED', 'HUMAN_LED']
const money = (n: number) => `$${Math.round(n).toLocaleString('en-US')}`

function useOpen() {
  const setActiveTab = useStore(s => s.setActiveTab)
  return (path: string) => {
    setActiveTab(tabIndex(path))
    navigate(path)
    window.scrollTo({ top: 0 })
  }
}

export default function Overview() {
  const palette = usePalette()
  const chart = chartStyle(palette)
  const open = useOpen()
  const caseRecord = useStore(s => s.caseRecord)
  const health = useHealth()

  const mocs = useQuery<MocRow[]>({ queryKey: ['mocs'], queryFn: getMocs, staleTime: 5 * 60_000 })
  const assets = useQuery<AssetRow[]>({ queryKey: ['assets'], queryFn: getAssets, staleTime: 5 * 60_000 })
  const allocations = useQuery({ queryKey: ['allocation-mocs'], queryFn: getAllocationMocs, staleTime: 5 * 60_000 })
  const cases = useQuery({ queryKey: ['allocation-cases'], queryFn: getAllocationCases, staleTime: 5 * 60_000 })

  const totalCost = useMemo(() => (mocs.data ?? []).reduce((s, m) => s + (Number(m.cost) || 0), 0), [mocs.data])

  const allocationMix = useMemo(() => {
    const rows = allocations.data?.mocs ?? []
    return CODES.map(code => ({ code, name: ALLOCATION_LABEL[code], value: rows.filter(r => r.allocation === code).length }))
  }, [allocations.data])
  const mostCommon = [...allocationMix].sort((a, b) => b.value - a.value)[0]

  const byChangeType = useMemo(() => {
    const counts = new Map<string, number>()
    for (const m of mocs.data ?? []) counts.set(m.change_type || 'Other', (counts.get(m.change_type || 'Other') ?? 0) + 1)
    return [...counts.entries()].map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
  }, [mocs.data])

  const costPerMoc = useMemo(
    () => (mocs.data ?? []).map(m => ({ name: m.moc_id, title: m.title ?? m.moc_id, value: Number(m.cost) || 0 })),
    [mocs.data],
  )

  const byCriticality = useMemo(() => {
    const counts = new Map<number, number>()
    for (const a of assets.data ?? []) if (a.criticality != null) counts.set(a.criticality, (counts.get(a.criticality) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => a[0] - b[0]).map(([level, value]) => ({ name: `Level ${level}`, level, value }))
  }, [assets.data])

  const critTone = (level: number): Token => (level >= 5 ? 'critical' : level >= 4 ? 'danger' : level >= 3 ? 'warn' : 'ok')

  const why = caseRecord?.why_trust
  const alloc = caseRecord?.who_decides?.result

  const platform: { icon: LucideIcon; tone: Token; title: string; sub: string }[] = [
    { icon: Network, tone: 'accent', title: 'Knowledge graph', sub: 'Neo4j: assets, changes, hazards' },
    { icon: Sparkles, tone: 'highlight', title: 'Language model', sub: health.data?.openai?.ok ? `OpenAI ${health.data.openai.message}` : 'OpenAI' },
    { icon: ScanSearch, tone: 'node-lesson', title: 'Vector search', sub: 'ChromaDB embeddings of past MoCs' },
    { icon: BrainCircuit, tone: 'node-risk', title: 'Cost model', sub: 'KNN blended with a heuristic' },
    { icon: Workflow, tone: 'accent2', title: '7 agents', sub: 'Supervisor, specialists, verifier' },
    { icon: Scale, tone: 'ok', title: 'Decision model', sub: cases.data ? `Allocation model v${cases.data.model_version}` : 'Allocation model' },
  ]

  return (
    <div className="space-y-5">
      {/* ── Welcome + status ── */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <section className="moc-glass-card relative overflow-hidden rounded-2xl p-5 xl:col-span-2">
          <div className="flex items-start gap-4">
            <IconTile icon={LayoutDashboard} size={52} />
            <div className="min-w-0">
              <div className="text-[11px] font-semibold uppercase tracking-widest text-accent">FCC unit · Symmetra Systems</div>
              <h2 className="mt-1 text-xl font-bold text-white">MoC Intelligence Platform</h2>
              <p className="mt-1 max-w-2xl text-sm text-white/60">
                Assess an engineering change against the plant&apos;s knowledge graph, see who should make the decision,
                and see why the recommendation can be trusted.
              </p>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Btn onClick={() => open(PATH_CHANGE_CASE)}>
              <Workflow className="h-4 w-4" strokeWidth={1.75} />Start a Change Case
            </Btn>
            <Btn variant="ghost" onClick={() => open('/app/mocbot')}>
              <Bot className="h-4 w-4" strokeWidth={1.75} />Ask MoCBot
            </Btn>
            <Btn variant="ghost" onClick={() => open('/app/allocation')}>
              <Scale className="h-4 w-4" strokeWidth={1.75} />Decision Allocation
            </Btn>
          </div>
        </section>

        <Panel title="System status" icon={Activity}>
          <ul className="space-y-2.5 text-sm">
            {([['Neo4j', 'Knowledge graph', health.data?.neo4j], ['OpenAI', 'Language model', health.data?.openai]] as const).map(([name, role, info]) => (
              <li key={name} className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <div className="font-semibold text-white/85">{role}</div>
                  <div className="truncate text-xs text-white/45">
                    {health.isError ? 'Backend unreachable: it may be waking up' : info?.message ?? 'Checking…'}
                  </div>
                </div>
                <ServicePill name={name} info={info} failed={health.isError} />
              </li>
            ))}
          </ul>
          <p className="mt-3 text-[11px] text-white/35">Checked every 30 seconds. If the knowledge graph is down, scoring and the reference cases still work.</p>
        </Panel>
      </div>

      {/* ── Stat tiles ── */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <StatTile icon={FileStack} label="MoC records" value={mocs.data?.length ?? '–'} loading={mocs.isLoading}
          sub={mocs.isError ? 'Graph unavailable' : 'in the knowledge graph'} />
        <StatTile icon={Boxes} tone="node-asset" label="Assets" value={assets.data?.length ?? '–'} loading={assets.isLoading}
          sub={assets.isError ? 'Graph unavailable' : `${new Set((assets.data ?? []).map(a => a.area).filter(Boolean)).size} plant areas`} />
        <StatTile icon={CircleDollarSign} tone="highlight" label="Recorded change cost" value={mocs.data ? money(totalCost) : '–'}
          loading={mocs.isLoading} sub="all recorded MoCs" />
        <StatTile icon={Scale} tone={mostCommon ? ALLOCATION_TONE[mostCommon.code] : 'slate'} label="Most common allocation"
          value={mostCommon && mostCommon.value ? mostCommon.name : '–'} loading={allocations.isLoading}
          sub={mostCommon && mostCommon.value ? `${mostCommon.value} of ${allocations.data?.mocs.length ?? 0} recorded MoCs` : 'no allocations stored'} />
        <StatTile icon={ShieldCheck} tone="ok" label="Thesis cases reproduced"
          value={cases.data ? `${cases.data.reproduced} / ${cases.data.total}` : '–'} loading={cases.isLoading}
          sub="published results" />
      </div>

      {/* ── Charts ── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Who decides recorded changes" icon={Scale}>
          {allocations.isLoading ? <Spinner /> : allocations.isError ? <ErrorBox error={allocations.error} title="Could not load allocations" /> : (
            <div className="flex items-center gap-4">
              <div className="h-[170px] w-[170px] shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={allocationMix} dataKey="value" nameKey="name" innerRadius={50} outerRadius={78} paddingAngle={3} stroke="none">
                      {allocationMix.map(d => <Cell key={d.code} fill={palette[ALLOCATION_TONE[d.code]]} />)}
                    </Pie>
                    <Tooltip contentStyle={chart.tooltip} itemStyle={chart.tooltipItem} labelStyle={chart.tooltipLabel} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="min-w-0 space-y-2 text-sm">
                {allocationMix.map(d => (
                  <li key={d.code} className="flex items-center gap-2">
                    <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: cssVar(ALLOCATION_TONE[d.code]) }} aria-hidden />
                    <span className="text-white/70">{d.name}</span>
                    <span className="font-semibold text-white">{d.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Panel>

        <Panel title="Changes by type" icon={FileStack} className="lg:col-span-2">
          {mocs.isLoading ? <Spinner /> : mocs.isError ? <ErrorBox error={mocs.error} title="Could not load MoC records" /> : (
            <ResponsiveContainer width="100%" height={Math.max(170, byChangeType.length * 30)}>
              <BarChart data={byChangeType} layout="vertical" margin={{ left: 8, right: 16, top: 4, bottom: 4 }}>
                <CartesianGrid horizontal={false} stroke={palette.slate} strokeOpacity={0.15} />
                <XAxis type="number" allowDecimals={false} tick={chart.smallTick} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={190} tick={chart.tick} axisLine={false} tickLine={false} />
                <Tooltip contentStyle={chart.tooltip} itemStyle={chart.tooltipItem} labelStyle={chart.tooltipLabel} cursor={chart.cursor} />
                <Bar dataKey="value" name="MoCs" fill={palette.accent} radius={[0, 8, 8, 0]} barSize={16} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Recorded cost per change" icon={CircleDollarSign} className="lg:col-span-2">
          {mocs.isLoading ? <Spinner /> : mocs.isError ? <ErrorBox error={mocs.error} title="Could not load MoC records" /> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={costPerMoc} margin={{ left: 8, right: 8, top: 8, bottom: 4 }}>
                <CartesianGrid vertical={false} stroke={palette.slate} strokeOpacity={0.15} />
                <XAxis dataKey="name" tick={chart.smallTick} axisLine={false} tickLine={false} />
                <YAxis tick={chart.smallTick} axisLine={false} tickLine={false} width={56}
                  tickFormatter={v => `$${Math.round(Number(v) / 1000)}k`} />
                <Tooltip contentStyle={chart.tooltip} itemStyle={chart.tooltipItem} labelStyle={chart.tooltipLabel} cursor={chart.cursor}
                  formatter={v => [money(Number(v)), 'Actual cost']}
                  labelFormatter={(_, p) => (p?.[0]?.payload as { title?: string } | undefined)?.title ?? ''} />
                <Bar dataKey="value" name="Actual cost" fill={palette.accent2} radius={[8, 8, 0, 0]} barSize={22} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>

        <Panel title="Assets by criticality" icon={GaugeIcon}>
          {assets.isLoading ? <Spinner /> : assets.isError ? <ErrorBox error={assets.error} title="Could not load assets" /> : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byCriticality} margin={{ left: 0, right: 8, top: 8, bottom: 4 }}>
                <CartesianGrid vertical={false} stroke={palette.slate} strokeOpacity={0.15} />
                <XAxis dataKey="name" tick={chart.smallTick} axisLine={false} tickLine={false} />
                <YAxis allowDecimals={false} tick={chart.smallTick} axisLine={false} tickLine={false} width={28} />
                <Tooltip contentStyle={chart.tooltip} itemStyle={chart.tooltipItem} labelStyle={chart.tooltipLabel} cursor={chart.cursor} />
                <Bar dataKey="value" name="Assets" radius={[8, 8, 0, 0]} barSize={26}>
                  {byCriticality.map(d => <Cell key={d.level} fill={palette[critTone(d.level)]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </Panel>
      </div>

      {/* ── Latest case + platform ── */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Panel title="Latest Change Case" icon={Workflow}
          actions={caseRecord ? (
            <button type="button" onClick={() => open(PATH_CHANGE_CASE)}
              className="inline-flex items-center gap-1 text-xs font-semibold text-accent hover:text-accent-soft">
              Open <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
            </button>
          ) : undefined}>
          {caseRecord && why ? (
            <div className="space-y-3">
              <div>
                <div className="text-sm text-white/80">
                  <span className="font-mono text-accent mr-1.5">{caseRecord.request.asset_id}</span>{caseRecord.request.change_type}
                </div>
                <p className="mt-0.5 line-clamp-2 text-xs text-white/50">{caseRecord.request.description}</p>
              </div>
              {alloc && (
                <div className="text-lg font-bold" style={{ color: cssVar(ALLOCATION_TONE[alloc.allocation]) }}>
                  {ALLOCATION_LABEL[alloc.allocation]} <span className="font-mono text-sm text-white/40">{alloc.signature}</span>
                </div>
              )}
              <div className="grid grid-cols-3 gap-2 text-center">
                {[
                  ['Evidence', why.counts.evidence, 'accent'],
                  ['Conflicts', why.counts.conflicts, why.counts.conflicts ? 'danger' : 'ok'],
                  ['Checkpoints', why.checkpoints.length, 'accent2'],
                ].map(([label, value, tone]) => (
                  <div key={label as string} className="moc-status-row rounded-xl px-2 py-2">
                    <div className="text-lg font-bold" style={{ color: cssVar(tone as Token) }}>{value}</div>
                    <div className="text-[10px] uppercase tracking-wider text-white/45">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-white/55">
                No case has been run in this session. A Change Case runs seven agents on one change and shows what happens,
                who should decide, and why.
              </p>
              <Btn onClick={() => open(PATH_CHANGE_CASE)}>
                <Workflow className="h-4 w-4" strokeWidth={1.75} />Start a Change Case
              </Btn>
            </div>
          )}
        </Panel>

        <Panel title="Platform" icon={Boxes} className="lg:col-span-2">
          <ul className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {platform.map(p => (
              <li key={p.title} className="flex items-center gap-3 rounded-2xl p-2">
                <IconTile icon={p.icon} tone={p.tone} size={48} className="glass-hover" />
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-white/90">{p.title}</div>
                  <div className="truncate text-[11px] text-white/45" title={p.sub}>{p.sub}</div>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  )
}
