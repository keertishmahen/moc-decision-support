import React, { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { prefillForm } from '../api'
import { Card, KpiCard, RiskBadge, SectionLabel, Btn, Select, Textarea } from '../components/ui'
import { CHANGE_TYPES, ASSET_IDS } from '../constants'

export default function SmartForm() {
  const [ct, setCt]   = useState(CHANGE_TYPES[0])
  const [aid, setAid] = useState(ASSET_IDS[0])
  const [desc, setDesc] = useState('')

  const { mutate, data, isPending } = useMutation({
    mutationFn: () => prefillForm({ change_type: ct, asset_id: aid, description: desc }),
  })

  const s = data?.suggestions
  const similar = data?.similar_mocs ?? []

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-white tracking-tight">Smart Guided MoC Form</h2>
        <p className="text-sm text-white/50 mt-1">AI auto-prefills form fields using historical MoCs from the knowledge graph + semantic vector search.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Select label="Change Type" value={ct} onChange={setCt} options={CHANGE_TYPES} />
            <Select label="Asset ID" value={aid} onChange={setAid} options={ASSET_IDS} />
          </div>
          <Textarea label="Describe the proposed change" value={desc} onChange={setDesc} rows={4}
            placeholder="e.g. Replace feed pump P-101 due to excessive vibration and bearing wear…" />
          <Btn onClick={() => desc.trim() && mutate()} loading={isPending}>
            <Search className="h-4 w-4" strokeWidth={1.75} />
            Get AI Suggestions
          </Btn>
        </Card>

        <Card className="text-sm text-white/60 space-y-2">
          <SectionLabel>How it works</SectionLabel>
          <p><b className="text-white/80">1.</b> Description embedded via OpenAI, matched against 10 historical MoCs in ChromaDB.</p>
          <p><b className="text-white/80">2.</b> Neo4j graph traversed for same asset/change type — hazards, approvers, P&IDs retrieved.</p>
          <p><b className="text-white/80">3.</b> GPT-4o synthesises both sources into structured form suggestions.</p>
        </Card>
      </div>

      {s && (
        <div className="space-y-4">
          <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

          <div className="flex items-center gap-3">
            <h3 className="font-bold text-white">AI Suggestions</h3>
            <RiskBadge rating={s.risk_level ?? 'Unknown'} />
          </div>

          <div className="grid grid-cols-3 gap-3">
            <KpiCard label="Risk Level" value={<RiskBadge rating={s.risk_level ?? 'Unknown'} />} />
            <div className="moc-glass-card rounded-2xl p-4 flex flex-col items-center justify-center gap-1"
              style={{ borderColor: s.hazop_required === 'Yes' ? '#fbbf2440' : '#34d39940' }}>
              <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50">HAZOP Required</div>
              <div className="text-xl font-bold" style={{ color: s.hazop_required === 'Yes' ? '#fbbf24' : '#34d399' }}>
                {s.hazop_required === 'Yes' ? '⚠ Yes' : '✓ No'}
              </div>
            </div>
            <div className="moc-glass-card rounded-2xl p-4 flex flex-col items-center justify-center gap-1"
              style={{ borderColor: s.pssr_required === 'Yes' ? '#fbbf2440' : '#34d39940' }}>
              <div className="text-[11px] font-semibold uppercase tracking-widest text-white/50">PSSR Required</div>
              <div className="text-xl font-bold" style={{ color: s.pssr_required === 'Yes' ? '#fbbf24' : '#34d399' }}>
                {s.pssr_required === 'Yes' ? '⚠ Yes' : '✓ No'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Card>
              <SectionLabel>Recommended Approvers</SectionLabel>
              {(s.approvers ?? []).map((a: string) => (
                <div key={a} className="text-sm text-white/80 py-1 border-b border-white/5 last:border-0">👤 {a}</div>
              ))}
            </Card>
            <Card>
              <SectionLabel>P&ID Tags to Review</SectionLabel>
              {(s.pid_tags ?? []).map((t: string) => (
                <div key={t} className="text-sm font-mono text-white/80 py-1 border-b border-white/5 last:border-0">🔧 {t}</div>
              ))}
              {s.scope && <p className="text-xs text-white/50 mt-2"><b>Scope:</b> {s.scope}</p>}
            </Card>
          </div>

          {s.justification && (
            <div className="moc-glass-card rounded-xl border-[#4f8ef7]/25 p-4 text-sm text-white/80 leading-relaxed">
              💡 <b>AI Justification:</b> {s.justification}
            </div>
          )}

          {similar.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-semibold text-[#4f8ef7] hover:text-blue-300 transition-colors list-none flex items-center gap-2">
                <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
                📚 Similar Historical MoCs ({similar.length})
              </summary>
              <div className="mt-3 space-y-2">
                {similar.slice(0, 5).map((m: Record<string, unknown>) => {
                  const meta = (m.metadata ?? {}) as Record<string, unknown>
                  const sim  = Number(m.similarity ?? 0)
                  const title = String(meta.title ?? m.title ?? m.moc_id ?? '?')
                  const risk  = String(meta.risk_level ?? m.risk_level ?? '?')
                  const cost  = meta.cost ?? m.cost
                  return (
                    <div key={String(m.moc_id)} className="flex items-start gap-3 p-3 rounded-xl border border-white/8 bg-white/[0.02]">
                      <div className="w-2 h-2 rounded-full bg-[#4f8ef7] mt-1.5 flex-shrink-0 shadow-[0_0_6px_#4f8ef7]" />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-semibold text-white">{String(m.moc_id)} — {title.slice(0, 55)}</div>
                        <div className="flex items-center gap-3 mt-1.5">
                          <RiskBadge rating={risk} />
                          <span className="text-xs text-white/40">Cost: ${String(cost)}</span>
                          <div className="flex-1 h-1 rounded-full bg-white/8">
                            <div className="h-full rounded-full bg-[#4f8ef7]" style={{ width: `${sim * 100}%` }} />
                          </div>
                          <span className="text-xs text-[#4f8ef7]">{sim.toFixed(2)}</span>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
