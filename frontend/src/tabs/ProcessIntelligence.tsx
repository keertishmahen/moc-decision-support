import React, { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Link2, Radio, Sparkles, type LucideIcon } from 'lucide-react'
import {
  getTopology, getConnectivity, propagateDowntime,
  getPropagationMatrix, runAgent,
} from '../api'
import {
  Card, KpiCard, SectionLabel, Btn, Select, Textarea, RiskBadge, Spinner,
} from '../components/ui'
import { ASSET_IDS } from '../constants'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
  ScatterChart, Scatter, ZAxis,
} from 'recharts'
import { motion, AnimatePresence } from 'framer-motion'

const RISK_COLORS: Record<string, string> = {
  Critical: '#ef4444',
  High:     '#f87171',
  Medium:   '#fbbf24',
  Low:      '#34d399',
}

// ── Sub-tab: Process Topology ──────────────────────────────────────────────
function TopologyPanel() {
  const [selectedAsset, setSelectedAsset] = useState(ASSET_IDS[2]) // R-201

  const { data: connectivity, mutate: fetchConn, isPending: connLoading } = useMutation({
    mutationFn: () => getConnectivity({ asset_id: selectedAsset }),
  })

  const conn = connectivity?.connectivity
  const score = connectivity?.score

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold text-white">Process Asset Connectivity</h3>
        <p className="text-xs text-white/40 mt-0.5">
          Full upstream/downstream connectivity map with relationship types, flow metadata, and criticality scores.
        </p>
      </div>

      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <Select label="Asset" value={selectedAsset} onChange={setSelectedAsset} options={ASSET_IDS} />
        </div>
        <Btn onClick={() => fetchConn()} loading={connLoading}>
          <Link2 className="h-4 w-4" strokeWidth={1.75} />
          Analyse Connectivity
        </Btn>
      </div>

      {connLoading && <Spinner text="Querying process topology…" />}

      {conn && score && (
        <div className="space-y-3">
          {/* Score KPIs */}
          <div className="grid grid-cols-4 gap-3">
            <KpiCard label="Connectivity Score" value={score.score} color="#4f8ef7"
              sub="weighted importance" />
            <KpiCard label="Downstream" value={conn.downstream_count ?? 0}
              sub="direct connections" color="#34d399" />
            <KpiCard label="Upstream" value={conn.upstream_count ?? 0}
              sub="direct connections" color="#a78bfa" />
            <KpiCard label="Criticality" value={score.criticality ?? '?'}
              color={score.criticality >= 5 ? '#ef4444' : score.criticality >= 4 ? '#f87171' : '#fbbf24'} />
          </div>

          {/* Score breakdown */}
          {score.components && (
            <Card>
              <SectionLabel>Score Components</SectionLabel>
              <ResponsiveContainer width="100%" height={120}>
                <BarChart data={Object.entries(score.components).map(([k, v]) => ({
                  name: k.replace(/_/g, ' '), value: v as number
                }))}>
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis hide />
                  <Tooltip contentStyle={{ background: '#0d1220', border: '1px solid rgba(79,142,247,0.3)', borderRadius: 8, color: '#e8eeff', fontSize: 11 }} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]} fill="#4f8ef7" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          )}

          <div className="grid grid-cols-2 gap-3">
            {/* Downstream */}
            {(conn.downstream_nodes ?? []).length > 0 && (
              <Card>
                <SectionLabel>Downstream Connections</SectionLabel>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {(conn.downstream_nodes as Record<string, unknown>[]).map((n, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-white/5 last:border-0">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
                      <span className="font-mono text-emerald-400 w-16 flex-shrink-0">{String(n.asset_id)}</span>
                      <span className="text-white/60 flex-1 truncate">{String(n.name)}</span>
                      <span className="text-white/30 text-[10px] flex-shrink-0">{String(n.rel_type)}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Upstream */}
            {(conn.upstream_nodes ?? []).length > 0 && (
              <Card>
                <SectionLabel>Upstream Connections</SectionLabel>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {(conn.upstream_nodes as Record<string, unknown>[]).map((n, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs py-1 border-b border-white/5 last:border-0">
                      <span className="w-2 h-2 rounded-full bg-purple-400 flex-shrink-0" />
                      <span className="font-mono text-purple-400 w-16 flex-shrink-0">{String(n.asset_id)}</span>
                      <span className="text-white/60 flex-1 truncate">{String(n.name)}</span>
                      <span className="text-white/30 text-[10px] flex-shrink-0">{String(n.rel_type)}</span>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>

          {score.is_esd_target && (
            <div className="rounded-xl border border-red-500/30 bg-red-500/08 p-3 text-sm text-red-400">
              ⚠ <b>ESD Target:</b> This asset is directly controlled by the Emergency Shutdown System.
              Any downtime here triggers a plant-wide ESD response.
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Sub-tab: Downtime Propagation ──────────────────────────────────────────
function DowntimePanel() {
  const [asset, setAsset]   = useState(ASSET_IDS[2])
  const [hours, setHours]   = useState('24')

  const { data: result, mutate: propagate, isPending } = useMutation({
    mutationFn: () => propagateDowntime({
      asset_id: asset,
      downtime_hours: parseFloat(hours) || 24,
    }),
  })

  const { data: matrix, isLoading: matrixLoading } = useQuery({
    queryKey: ['propagation-matrix'],
    queryFn: getPropagationMatrix,
    staleTime: 5 * 60 * 1000,
  })

  const affected = (result?.affected_assets ?? []) as Record<string, unknown>[]

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold text-white">Dynamic Downtime Propagation</h3>
        <p className="text-xs text-white/40 mt-0.5">
          Propagates downtime through the process topology using coupling coefficients,
          criticality amplifiers, and hop-decay modelling.
        </p>
      </div>

      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <Select label="Source Asset" value={asset} onChange={setAsset} options={ASSET_IDS} />
        </div>
        <div className="w-32">
          <label className="block text-[11px] font-semibold uppercase tracking-widest text-white/50 mb-1.5">
            Downtime (hrs)
          </label>
          <input
            type="number" value={hours} onChange={e => setHours(e.target.value)}
            className="moc-input-glass w-full rounded-xl px-3 py-2 text-sm text-white focus:outline-none transition-colors"
          />
        </div>
        <Btn onClick={() => propagate()} loading={isPending}>📡 Propagate</Btn>
      </div>

      {isPending && <Spinner text="Propagating downtime through process topology…" />}

      {result && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <KpiCard label="Source Downtime" value={`${result.source_downtime}h`} color="#4f8ef7" />
            <KpiCard label="Assets Affected" value={result.total_affected} color="#f87171" />
            <KpiCard label="Total Propagated" value={`${result.total_propagated_hours}h`} color="#fbbf24"
              sub="across all downstream" />
          </div>

          {result.summary && (
            <div className="moc-glass-card rounded-xl border-[#4f8ef7]/25 p-3 text-sm text-white/80 leading-relaxed">
              📡 {result.summary}
            </div>
          )}

          {affected.length > 0 && (
            <>
              {/* Bar chart of propagated hours */}
              <Card>
                <SectionLabel>Propagated Downtime by Asset</SectionLabel>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={affected.slice(0, 10).map(a => ({
                    name: String(a.asset_id),
                    hours: Number(a.propagated_hours),
                    risk: String(a.risk_level),
                  }))}>
                    <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#0d1220', border: '1px solid rgba(79,142,247,0.3)', borderRadius: 8, color: '#e8eeff', fontSize: 11 }}
                      formatter={(v: unknown) => [`${v}h`, 'Propagated']}
                    />
                    <Bar dataKey="hours" radius={[4, 4, 0, 0]}>
                      {affected.slice(0, 10).map((a, i) => (
                        <Cell key={i} fill={RISK_COLORS[String(a.risk_level)] ?? '#64748b'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Card>

              {/* Detailed table */}
              <Card>
                <SectionLabel>Affected Assets Detail</SectionLabel>
                <div className="space-y-1.5 max-h-64 overflow-y-auto">
                  {affected.map((a, i) => (
                    <div key={i} className="grid grid-cols-12 gap-2 text-xs py-1.5 border-b border-white/5 last:border-0 items-center">
                      <span className="col-span-2 font-mono text-[#4f8ef7]">{String(a.asset_id)}</span>
                      <span className="col-span-3 text-white/60 truncate">{String(a.asset_name)}</span>
                      <span className="col-span-1 text-center text-white/40">{String(a.hop_distance)}h</span>
                      <span className="col-span-2 font-bold text-amber-400">{Number(a.propagated_hours).toFixed(1)}h</span>
                      <span className="col-span-2 text-white/30 text-[10px]">
                        {Number(a.confidence_low).toFixed(1)}–{Number(a.confidence_high).toFixed(1)}h
                      </span>
                      <span className="col-span-2">
                        <RiskBadge rating={String(a.risk_level)} />
                      </span>
                    </div>
                  ))}
                </div>
              </Card>
            </>
          )}
        </div>
      )}

      {/* Propagation Matrix */}
      <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      <div>
        <h4 className="font-semibold text-white/80 text-sm mb-1">Propagation Risk Matrix</h4>
        <p className="text-xs text-white/40 mb-3">
          Top assets by total downstream downtime impact (24h source scenario).
        </p>
        {matrixLoading && <Spinner text="Computing propagation matrix…" />}
        {matrix?.matrix && (
          <div className="space-y-1.5">
            {(matrix.matrix as Record<string, unknown>[]).slice(0, 8).map((row, i) => {
              const pct = Math.min(100, (Number(row.total_propagated_hours) / 200) * 100)
              return (
                <div key={i} className="flex items-center gap-3 text-xs">
                  <span className="font-mono text-[#4f8ef7] w-16 flex-shrink-0">{String(row.source_asset_id)}</span>
                  <div className="flex-1 h-2 rounded-full bg-white/8">
                    <div className="h-full rounded-full bg-gradient-to-r from-[#4f8ef7] to-[#f87171]"
                      style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-amber-400 w-14 text-right">{Number(row.total_propagated_hours).toFixed(0)}h total</span>
                  <span className="text-white/30 w-8 text-right">{Number(row.total_affected)} assets</span>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-tab: Agent ─────────────────────────────────────────────────────────
const AGENT_PROMPTS = [
  { label: 'R-201 offline 48h', msg: 'What would happen if R-201 goes offline for 48 hours? Which assets are most affected?' },
  { label: 'SV-204 risk profile', msg: 'Analyse the complete risk profile of SV-204 including connectivity, hazards, and historical MoCs.' },
  { label: 'Compare instrumentation MoCs', msg: 'Compare the risk profiles of all instrumentation MoCs (MoC-002 and MoC-005).' },
  { label: 'CTL-205 impact', msg: 'If CTL-205 fails, what is the propagated downtime across the FCC unit?' },
  { label: 'Highest connectivity asset', msg: 'Which asset in the FCC unit has the highest connectivity score and why is it critical?' },
]

function AgentPanel() {
  const [query, setQuery] = useState('')

  const { data: result, mutate: runAgentQuery, isPending } = useMutation({
    mutationFn: () => runAgent({ query, max_iterations: 6 }),
  })

  const send = (q: string) => {
    setQuery(q)
    runAgent({ query: q, max_iterations: 6 })
  }

  const { mutate: runWithQuery } = useMutation({
    mutationFn: (q: string) => runAgent({ query: q, max_iterations: 6 }),
    onSuccess: (data) => {
      // handled by result above — use separate mutation for quick prompts
    },
  })

  return (
    <div className="space-y-4">
      <div>
        <h3 className="font-bold text-white">Agent-Based Reasoning</h3>
        <p className="text-xs text-white/40 mt-0.5">
          Multi-step agent that orchestrates graph queries, vector search, and downtime propagation
          using OpenAI function calling before generating a grounded answer.
        </p>
      </div>

      {/* Quick prompts */}
      <div className="flex flex-wrap gap-2">
        {AGENT_PROMPTS.map(p => (
          <button key={p.label}
            onClick={() => { setQuery(p.msg); runAgentQuery() }}
            className="px-3 py-1.5 rounded-full text-xs font-medium bg-[#a78bfa]/10 border border-[#a78bfa]/25 text-[#c4b5fd] hover:bg-[#a78bfa]/20 transition-all">
            {p.label}
          </button>
        ))}
      </div>

      <div className="space-y-2">
        <Textarea
          label="Agent Query"
          value={query}
          onChange={setQuery}
          rows={3}
          placeholder="Ask a complex multi-step question about the FCC Unit…"
        />
        <Btn onClick={() => query.trim() && runAgentQuery()} loading={isPending}>
          🤖 Run Agent
        </Btn>
      </div>

      {isPending && (
        <div className="moc-glass-card rounded-xl border-[#a78bfa]/25 p-4">
          <div className="flex items-center gap-3 text-sm text-white/60">
            <span className="w-5 h-5 border-2 border-[#a78bfa]/30 border-t-[#a78bfa] rounded-full animate-spin flex-shrink-0" />
            <span>Agent reasoning… calling tools and querying knowledge graph</span>
          </div>
        </div>
      )}

      {result && (
        <div className="space-y-3">
          {/* Response */}
          <Card>
            <SectionLabel>Agent Response</SectionLabel>
            <p className="text-sm text-white/85 leading-relaxed whitespace-pre-wrap">{result.response}</p>
          </Card>

          {/* Tool calls */}
          {(result.tool_calls_made ?? []).length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-semibold text-[#a78bfa] hover:text-purple-300 transition-colors list-none flex items-center gap-2">
                <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
                🔧 Tool Calls ({result.tool_calls_made.length}) — {result.iterations} iteration{result.iterations !== 1 ? 's' : ''}
              </summary>
              <div className="mt-3 space-y-2">
                {(result.tool_calls_made as Record<string, unknown>[]).map((tc, i) => (
                  <div key={i} className="moc-glass-card rounded-xl p-3">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="text-[10px] font-bold text-[#a78bfa] bg-[#a78bfa]/15 px-2 py-0.5 rounded-full">
                        {String(tc.tool)}
                      </span>
                      <span className="text-[10px] text-white/30">
                        {JSON.stringify(tc.args).slice(0, 80)}
                      </span>
                    </div>
                    <div className="text-[10px] text-white/40 font-mono truncate">
                      → {JSON.stringify(tc.result).slice(0, 120)}…
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main tab ───────────────────────────────────────────────────────────────
const SUB_TABS: { icon: LucideIcon; label: string }[] = [
  { icon: Link2, label: 'Connectivity' },
  { icon: Radio, label: 'Downtime Propagation' },
  { icon: Sparkles, label: 'Agent Reasoning' },
]

export default function ProcessIntelligence() {
  const [sub, setSub] = useState(0)
  const panels = [<TopologyPanel />, <DowntimePanel />, <AgentPanel />]

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-white">Process Intelligence</h2>
        <p className="text-sm text-white/50 mt-1">
          Advanced connectivity modelling · Dynamic downtime propagation · Agent-based reasoning
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1">
        {SUB_TABS.map((t, i) => {
          const Icon = t.icon
          return (
          <button key={i} onClick={() => setSub(i)}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              sub === i
                ? 'bg-[#a78bfa]/18 border border-[#a78bfa]/30 text-[#c4b5fd]'
                : 'bg-white/[0.03] border border-white/8 text-white/50 hover:text-white/80 hover:bg-white/[0.06]'
            }`}>
            <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
            {t.label}
          </button>
          )
        })}
      </div>

      <AnimatePresence mode="wait">
        <motion.div key={sub} initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.15 }}>
          {panels[sub]}
        </motion.div>
      </AnimatePresence>
    </div>
  )
}
