import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { analyseRisk } from '../api'
import { Card, KpiCard, RiskBadge, SectionLabel, Btn, Select, Textarea, Gauge } from '../components/ui'
import { CHANGE_TYPES, ASSET_IDS } from '../constants'
import { RadialBarChart, RadialBar, PieChart, Pie, Cell, BarChart, Bar, XAxis, Tooltip, ResponsiveContainer } from 'recharts'

const SEV_COLOR: Record<string, string> = { High: '#f87171', Critical: '#ef4444', Medium: '#fbbf24', Low: '#34d399' }
const RISK_SCORE: Record<string, number> = { Low: 22, Medium: 50, High: 76, Critical: 95 }

export default function RiskAnalysis() {
  const [ct, setCt]   = useState(CHANGE_TYPES[0])
  const [aid, setAid] = useState(ASSET_IDS[0])
  const [desc, setDesc] = useState('')

  const { mutate, data: r, isPending } = useMutation({
    mutationFn: () => analyseRisk({ change_type: ct, asset_id: aid, description: desc }),
  })

  const direct   = r?.direct_assets   ?? []
  const indirect = r?.indirect_assets ?? []
  const hazards  = r?.hazards         ?? []
  const risks    = r?.risks           ?? []
  const mits     = r?.mitigations     ?? []

  const sevCounts = hazards.reduce((acc: Record<string, number>, h: Record<string, unknown>) => {
    const s = String(h.severity ?? 'Unknown')
    acc[s] = (acc[s] ?? 0) + 1
    return acc
  }, {})

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-white">Risk & Impact Assessment</h2>
        <p className="text-sm text-white/50 mt-1">Graph-traversal risk analysis — traces asset dependencies up to 3 hops across the FCC unit.</p>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <Select label="Change Type" value={ct} onChange={setCt} options={CHANGE_TYPES} />
        <Select label="Asset ID" value={aid} onChange={setAid} options={ASSET_IDS} />
      </div>
      <Textarea label="Describe the proposed change" value={desc} onChange={setDesc} rows={3}
        placeholder="e.g. Upgrade catalyst slide valve SV-204 actuator to advanced feedback control…" />
      <Btn onClick={() => desc.trim() && mutate()} loading={isPending}>🔬 Analyse Risks</Btn>

      {r && (
        <div className="space-y-4">
          <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

          {/* KPI row */}
          <div className="grid grid-cols-4 gap-3">
            <KpiCard label="Overall Risk" value={<RiskBadge rating={r.overall_rating ?? 'Unknown'} />} />
            <KpiCard label="Direct Assets" value={direct.length} sub="1 hop" color="#34d399" />
            <KpiCard label="Indirect Assets" value={indirect.length} sub="2–3 hops" color="#fbbf24" />
            <KpiCard label="Hazards Found" value={hazards.length} sub="from graph" color="#f87171" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left: gauges + risks */}
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                <div className="moc-glass-card rounded-2xl p-3 flex flex-col items-center">
                  <Gauge value={RISK_SCORE[r.overall_rating ?? ''] ?? 0}
                    label="Risk Score" color="#4f8ef7" />
                </div>
                <div className="moc-glass-card rounded-2xl p-3 flex flex-col items-center justify-center gap-1"
                  style={{ borderColor: r.hazop_triggered === 'Yes' ? '#fbbf2440' : '#34d39940' }}>
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-white/50">HAZOP</div>
                  <div className="text-lg font-bold" style={{ color: r.hazop_triggered === 'Yes' ? '#fbbf24' : '#34d399' }}>
                    {r.hazop_triggered === 'Yes' ? '⚠ Yes' : '✓ No'}
                  </div>
                </div>
                <div className="moc-glass-card rounded-2xl p-3 flex flex-col items-center justify-center gap-1"
                  style={{ borderColor: r.pssr_required === 'Yes' ? '#fbbf2440' : '#34d39940' }}>
                  <div className="text-[10px] font-semibold uppercase tracking-widest text-white/50">PSSR</div>
                  <div className="text-lg font-bold" style={{ color: r.pssr_required === 'Yes' ? '#fbbf24' : '#34d399' }}>
                    {r.pssr_required === 'Yes' ? '⚠ Yes' : '✓ No'}
                  </div>
                </div>
              </div>

              {r.reasoning && (
                <div className="moc-glass-card rounded-xl border-[#4f8ef7]/25 p-3 text-sm text-white/80 leading-relaxed">
                  🧠 {r.reasoning}
                </div>
              )}

              <Card>
                <SectionLabel>Top Risks</SectionLabel>
                {risks.map((risk: Record<string, unknown>, i: number) => {
                  const sev = String(risk.severity ?? 'Medium')
                  return (
                    <div key={i} className="text-sm py-1.5 border-b border-white/5 last:border-0"
                      style={{ color: SEV_COLOR[sev] ?? '#94a3b8' }}>
                      ● {String(risk.description ?? '')}
                    </div>
                  )
                })}
              </Card>

              <Card>
                <SectionLabel>Mitigations</SectionLabel>
                {mits.map((m: string, i: number) => (
                  <div key={i} className="text-sm text-white/80 py-1.5 border-b border-white/5 last:border-0">✅ {m}</div>
                ))}
              </Card>
            </div>

            {/* Right: charts + impact */}
            <div className="space-y-3">
              {(direct.length + indirect.length) > 0 && (
                <Card>
                  <SectionLabel>Impact Distribution</SectionLabel>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={[
                        { name: 'Direct (1 hop)', value: Math.max(direct.length, 1) },
                        { name: 'Indirect (2-3 hops)', value: Math.max(indirect.length, 1) },
                      ]} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">
                        <Cell fill="#4f8ef7" />
                        <Cell fill="#a78bfa" />
                      </Pie>
                      <Tooltip contentStyle={{ background: '#0d1220', border: '1px solid rgba(79,142,247,0.3)', borderRadius: 8, color: '#e8eeff', fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex gap-4 justify-center text-xs text-white/50">
                    <span><span className="inline-block w-2 h-2 rounded-full bg-[#4f8ef7] mr-1" />Direct: {direct.length}</span>
                    <span><span className="inline-block w-2 h-2 rounded-full bg-[#a78bfa] mr-1" />Indirect: {indirect.length}</span>
                  </div>
                </Card>
              )}

              {direct.length > 0 && (
                <Card>
                  <SectionLabel>Direct Impact (1 hop)</SectionLabel>
                  {direct.slice(0, 6).map((a: Record<string, unknown>) => (
                    <div key={String(a.node_id)} className="text-sm text-emerald-400 py-1 border-b border-white/5 last:border-0">
                      ↳ <span className="font-mono">{String(a.node_id)}</span> {String(a.node_name ?? '')}
                    </div>
                  ))}
                </Card>
              )}

              {Object.keys(sevCounts).length > 0 && (
                <Card>
                  <SectionLabel>Hazard Severity</SectionLabel>
                  <ResponsiveContainer width="100%" height={120}>
                    <BarChart data={Object.entries(sevCounts).map(([k, v]) => ({ name: k, count: v }))}>
                      <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={{ background: '#0d1220', border: '1px solid rgba(79,142,247,0.3)', borderRadius: 8, color: '#e8eeff', fontSize: 12 }} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {Object.keys(sevCounts).map((k, i) => <Cell key={i} fill={SEV_COLOR[k] ?? '#64748b'} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </Card>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
