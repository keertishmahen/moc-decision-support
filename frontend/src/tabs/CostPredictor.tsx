import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { predictCost } from '../api'
import { Card, KpiCard, SectionLabel, Btn, Select, Textarea, Gauge, CIBar } from '../components/ui'
import { CHANGE_TYPES, ASSET_IDS, ASSET_CATS, RISK_LEVELS } from '../constants'

export default function CostPredictor() {
  const [ct, setCt]     = useState(CHANGE_TYPES[0])
  const [aid, setAid]   = useState(ASSET_IDS[0])
  const [acat, setAcat] = useState(ASSET_CATS[0])
  const [rl, setRl]     = useState(RISK_LEVELS[2])
  const [desc, setDesc] = useState('')

  const { mutate, data: r, isPending } = useMutation({
    mutationFn: () => predictCost({ change_type: ct, asset_id: aid, asset_category: acat, risk_level: rl, description: desc }),
  })

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-white">Cost & Downtime Prediction</h2>
        <p className="text-sm text-white/50 mt-1">ML model trained on historical MoC data, augmented with live knowledge graph features.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Select label="Change Type" value={ct} onChange={setCt} options={CHANGE_TYPES} />
            <Select label="Asset ID" value={aid} onChange={setAid} options={ASSET_IDS} />
            <Select label="Asset Category" value={acat} onChange={setAcat} options={ASSET_CATS} />
            <Select label="Risk Level" value={rl} onChange={setRl} options={RISK_LEVELS} />
          </div>
          <Textarea label="Change description" value={desc} onChange={setDesc} rows={3}
            placeholder="e.g. Replace reflux pump P-502 due to bearing failure…" />
          <Btn onClick={() => desc.trim() && mutate()} loading={isPending}>📊 Predict Cost & Downtime</Btn>
        </div>

        <Card className="text-sm text-white/60 space-y-1.5">
          <SectionLabel>Model Features</SectionLabel>
          {['Change type encoding','Asset category encoding','Risk level encoding',
            'Graph dependency count (Neo4j)','Associated hazard count (Neo4j)',
            'Historical MoC count on asset'].map(f => (
            <div key={f} className="flex items-start gap-2">
              <span className="text-[#4f8ef7] mt-0.5">▸</span>{f}
            </div>
          ))}
        </Card>
      </div>

      {r && (
        <div className="space-y-4">
          <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

          <div className="grid grid-cols-4 gap-3">
            <KpiCard label="Estimated Cost" value={`$${r.cost_estimate.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              sub={`$${r.cost_ci[0].toLocaleString(undefined, { maximumFractionDigits: 0 })} – $${r.cost_ci[1].toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
              color="#4f8ef7" />
            <KpiCard label="Estimated Downtime" value={`${r.downtime_estimate.toFixed(1)}h`}
              sub={`${r.downtime_ci[0].toFixed(1)} – ${r.downtime_ci[1].toFixed(1)} hrs`}
              color="#a78bfa" />
            <KpiCard label="Graph Dependencies" value={r.features?.n_dependencies ?? 0} sub="from Neo4j" color="#34d399" />
            <KpiCard label="Model" value={<span className="text-sm font-semibold text-amber-400">{r.models_used?.includes('ML') ? 'ML' : 'Heuristic'}</span>} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="flex flex-col items-center gap-2 moc-glass-card rounded-2xl p-4">
              <Gauge value={r.cost_estimate} max={r.cost_ci[1] * 1.1} label="Estimated Cost ($)" prefix="$" color="#4f8ef7" />
            </div>
            <div className="flex flex-col items-center gap-2 moc-glass-card rounded-2xl p-4">
              <Gauge value={r.downtime_estimate} max={r.downtime_ci[1] * 1.25} label="Downtime (hrs)" suffix="h" color="#a78bfa" />
            </div>
            <Card className="space-y-4 justify-center flex flex-col">
              <CIBar estimate={r.cost_estimate} low={r.cost_ci[0]} high={r.cost_ci[1]} label="Cost Confidence Interval" prefix="$" />
              <CIBar estimate={r.downtime_estimate} low={r.downtime_ci[0]} high={r.downtime_ci[1]} label="Downtime Confidence Interval" suffix="h" />
            </Card>
          </div>

          <Card>
            <SectionLabel>AI Explanation</SectionLabel>
            <p className="text-sm text-white/80 leading-relaxed">{r.explanation}</p>
          </Card>

          <details className="group">
            <summary className="cursor-pointer text-sm font-semibold text-[#4f8ef7] hover:text-blue-300 transition-colors list-none flex items-center gap-2">
              <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
              🔬 Feature Vector
            </summary>
            <div className="mt-3 grid grid-cols-3 gap-3">
              {Object.entries(r.features ?? {}).map(([k, v]) => (
                <div key={k} className="moc-glass-card rounded-xl p-3">
                  <div className="text-[11px] text-white/40 mb-1">{k}</div>
                  <div className="text-base font-bold font-mono text-[#4f8ef7]">{String(v)}</div>
                </div>
              ))}
            </div>
          </details>
        </div>
      )}
    </div>
  )
}
