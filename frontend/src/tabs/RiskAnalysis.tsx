import React from 'react'
import { useMutation } from '@tanstack/react-query'
import { analyseRisk } from '../api'
import { ArrowRight, Brain, Circle, CircleCheck, CornerDownRight, Microscope } from 'lucide-react'
import { Card, KpiCard, RiskBadge, SectionLabel, Btn, Select, Textarea, Gauge, ErrorBox, FlagTile } from '../components/ui'
import { chartStyle, cssVar, severityColor, severityToken, usePalette } from '../theme/palette'
import { CHANGE_TYPES, ASSET_IDS } from '../constants'
import { useStore } from '../store'
import { navigate, pathForTab, TAB_PATHS } from '../navigation'

const yesNo = (v: unknown): boolean | null => (v === 'Yes' ? true : v === 'No' ? false : null)
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, Tooltip, ResponsiveContainer } from 'recharts'

const ALLOCATION_TAB = TAB_PATHS.indexOf('/app/allocation')
const RISK_SCORE: Record<string, number> = { Low: 22, Medium: 50, High: 76, Critical: 95 }

export default function RiskAnalysis() {
  const { currentChange, setCurrentChange, setActiveTab, setAllocationIntent } = useStore()
  const palette = usePalette()
  const chart = chartStyle(palette)
  const ct = currentChange.changeType
  const aid = currentChange.assetId
  const desc = currentChange.description
  const setCt = (v: string) => setCurrentChange({ changeType: v })
  const setAid = (v: string) => setCurrentChange({ assetId: v })
  const setDesc = (v: string) => setCurrentChange({ description: v })

  const { mutate, data: r, isPending, error } = useMutation({
    mutationFn: () => analyseRisk({ change_type: ct, asset_id: aid, description: desc }),
    onSuccess: d => setCurrentChange({ hazopRequired: yesNo(d?.hazop_triggered), pssrRequired: yesNo(d?.pssr_required) }),
  })

  const continueToAllocation = () => {
    setAllocationIntent('proposed')
    setActiveTab(ALLOCATION_TAB)
    navigate(pathForTab(ALLOCATION_TAB))
  }

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
      <Btn onClick={() => desc.trim() && mutate()} loading={isPending}>
        <Microscope className="h-4 w-4" strokeWidth={1.75} aria-hidden />
        Analyse Risks
      </Btn>

      <ErrorBox error={error} title="Risk analysis failed" />

      {r && (
        <div className="space-y-4">
          <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

          {r?.llm_status === 'unavailable' && (
            <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
              The AI service is unavailable right now. Hazards and affected assets below come from the knowledge graph; no overall rating was assigned.
            </div>
          )}

          <div className="moc-glass-card rounded-xl border-accent/25 p-4 flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-white/70">
              Next: who should decide this change? The HAZOP and PSSR findings carry over.
            </p>
            <Btn variant="ghost" onClick={continueToAllocation}>
              Continue to Decision Allocation
              <ArrowRight className="h-4 w-4" strokeWidth={1.75} aria-hidden />
            </Btn>
          </div>

          {/* KPI row */}
          <div className="grid grid-cols-4 gap-3">
            <KpiCard label="Overall Risk" value={<RiskBadge rating={r.overall_rating ?? 'Unknown'} />} />
            <KpiCard label="Direct Assets" value={direct.length} sub="1 hop" tone="ok" />
            <KpiCard label="Indirect Assets" value={indirect.length} sub="2–3 hops" tone="warn" />
            <KpiCard label="Hazards Found" value={hazards.length} sub="from graph" tone="danger" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Left: gauges + risks */}
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2">
                <div className="moc-glass-card rounded-2xl p-3 flex flex-col items-center">
                  <Gauge value={RISK_SCORE[r.overall_rating ?? ''] ?? 0}
                    label="Risk Score" tone={severityToken(r.overall_rating)} />
                </div>
                <FlagTile label="HAZOP" value={r.hazop_triggered} compact />
                <FlagTile label="PSSR" value={r.pssr_required} compact />
              </div>

              {r.reasoning && (
                <div className="moc-glass-card rounded-xl border-accent/25 p-3 text-sm text-white/80 leading-relaxed flex gap-2.5">
                  <Brain className="h-4 w-4 text-accent flex-shrink-0 mt-0.5" strokeWidth={1.75} aria-hidden />
                  <span>{r.reasoning}</span>
                </div>
              )}

              <Card>
                <SectionLabel>Top Risks</SectionLabel>
                {risks.map((risk: Record<string, unknown>, i: number) => {
                  const sev = String(risk.severity ?? 'Medium')
                  return (
                    <div key={i} className="text-sm py-1.5 border-b border-white/5 last:border-0 flex items-start gap-2"
                      style={{ color: cssVar(severityToken(sev)) }}>
                      <Circle className="h-2.5 w-2.5 mt-1.5 flex-shrink-0 fill-current" strokeWidth={0} aria-label={`${sev} severity`} />
                      <span>{String(risk.description ?? '')}</span>
                    </div>
                  )
                })}
              </Card>

              <Card>
                <SectionLabel>Mitigations</SectionLabel>
                {mits.map((m: string, i: number) => (
                  <div key={i} className="text-sm text-white/80 py-1.5 border-b border-white/5 last:border-0 flex items-start gap-2"><CircleCheck className="h-4 w-4 text-ok flex-shrink-0 mt-0.5" strokeWidth={1.75} aria-hidden /><span>{m}</span></div>
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
                        <Cell fill={palette.accent} />
                        <Cell fill={palette.accent2} />
                      </Pie>
                      <Tooltip contentStyle={chart.tooltip} itemStyle={chart.tooltipItem} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="flex gap-4 justify-center text-xs text-white/50">
                    <span><span className="inline-block w-2 h-2 rounded-full bg-accent mr-1" />Direct: {direct.length}</span>
                    <span><span className="inline-block w-2 h-2 rounded-full bg-accent2 mr-1" />Indirect: {indirect.length}</span>
                  </div>
                </Card>
              )}

              {direct.length > 0 && (
                <Card>
                  <SectionLabel>Direct Impact (1 hop)</SectionLabel>
                  {direct.slice(0, 6).map((a: Record<string, unknown>) => (
                    <div key={String(a.node_id)} className="text-sm text-ok py-1 border-b border-white/5 last:border-0 flex items-center gap-1.5">
                      <CornerDownRight className="h-3.5 w-3.5 flex-shrink-0" strokeWidth={1.75} aria-hidden />
                      <span className="font-mono">{String(a.node_id)}</span> {String(a.node_name ?? '')}
                    </div>
                  ))}
                </Card>
              )}

              {Object.keys(sevCounts).length > 0 && (
                <Card>
                  <SectionLabel>Hazard Severity</SectionLabel>
                  <ResponsiveContainer width="100%" height={120}>
                    <BarChart data={Object.entries(sevCounts).map(([k, v]) => ({ name: k, count: v }))}>
                      <XAxis dataKey="name" tick={chart.tick} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={chart.tooltip} itemStyle={chart.tooltipItem} cursor={chart.cursor} />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {Object.keys(sevCounts).map((k, i) => <Cell key={i} fill={severityColor(palette, k)} />)}
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
