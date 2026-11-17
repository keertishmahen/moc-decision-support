/**
 * Change Case — one engineering change, three questions:
 *   1. What happens if we make it?   2. Who should make the decision?   3. Why trust the recommendation?
 *
 * The backend's agents reuse the platform's existing analyses; a verifier checks them; a person
 * records the review. Nothing is decided here and nothing is stored on the server.
 */
import React, { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowRight, BookOpen, FileJson, Printer, Workflow, X } from 'lucide-react'
import { Btn, CIBar, Card, ErrorBox, FlagTile, KpiCard, RiskBadge, SectionLabel, Select, Spinner, Textarea } from '../components/ui'
import { ASSET_IDS, CHANGE_TYPES } from '../constants'
import { navigate, pathForTab, TAB_PATHS } from '../navigation'
import { useStore } from '../store'
import { cssVar } from '../theme/palette'
import { AllocationBanner } from '../allocation/components'
import { getCaseAgents, streamCase, type CaseRecord, type HumanReview } from '../case/api'
import {
  ActivityFeed, AgentPanel, CheckpointList, ReviewForm, WhyPanel, WhyToggle, downloadJson, emptyReview, printLight,
} from '../case/components'

const ALLOCATION_TAB = TAB_PATHS.indexOf('/app/allocation')

/** MoC-002 is the reference case in the decision-allocation thesis and the brief. */
const EXAMPLE = {
  moc_id: 'MoC-002',
  change_type: 'Instrumentation',
  asset_id: 'FV-103',
  description: 'Replace FV-103 with smart control valve to improve temperature regulation and enable remote monitoring',
}

const REVIEW_KEY = (runId: string) => `moc-case-review:${runId}`

function loadReview(runId: string): HumanReview {
  try {
    const raw = localStorage.getItem(REVIEW_KEY(runId))
    return raw ? { ...emptyReview(), ...JSON.parse(raw) } : emptyReview()
  } catch {
    return emptyReview()
  }
}

function saveReview(runId: string, review: HumanReview) {
  try {
    localStorage.setItem(REVIEW_KEY(runId), JSON.stringify(review))
  } catch { /* storage unavailable: the review still lives in memory and in the export */ }
}

const money = (n: number | null | undefined) => (n == null ? 'n/a' : `$${Math.round(n).toLocaleString()}`)

export default function ChangeCase() {
  const {
    currentChange, setCurrentChange, caseRecord, setActiveTab, setAllocationIntent, caseRun,
  } = useStore()
  const [exampleMoc, setExampleMoc] = useState<string | null>(null)
  const [review, setReview] = useState<HumanReview>(() => (caseRecord ? loadReview(caseRecord.run_id) : emptyReview()))
  const [now, setNow] = useState(() => Date.now())

  const registry = useQuery({ queryKey: ['case-agents'], queryFn: getCaseAgents, staleTime: Infinity })
  const running = caseRun.phase === 'running'

  // Relative times in the activity feed and the elapsed counter.
  useEffect(() => {
    const id = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(id)
  }, [])

  // A new case starts with its own (possibly saved) review.
  useEffect(() => {
    if (caseRecord) setReview(loadReview(caseRecord.run_id))
  }, [caseRecord?.run_id]) // eslint-disable-line react-hooks/exhaustive-deps

  const edit = (patch: Partial<typeof currentChange>) => {
    setCurrentChange(patch)
    setExampleMoc(null)            // an edited change is no longer the recorded example
  }

  const loadExample = () => {
    setCurrentChange({ changeType: EXAMPLE.change_type, assetId: EXAMPLE.asset_id, description: EXAMPLE.description })
    setExampleMoc(EXAMPLE.moc_id)
  }

  /** Runs through the store, so progress keeps arriving if the user switches tabs. */
  const assess = async () => {
    const reg = registry.data
    if (!reg || running) return
    const names = Object.fromEntries([reg.supervisor, ...reg.agents].map(a => [a.id, a.name]))
    const store = useStore.getState()
    store.startCaseRun(reg.stages.flat())
    try {
      const record = await streamCase(
        {
          change_type: currentChange.changeType,
          asset_id: currentChange.assetId,
          description: currentChange.description.trim(),
          moc_id: exampleMoc,
        },
        e => useStore.getState().applyCaseEvent(e, names),
        () => useStore.getState().caseRunFallback(),
      )
      useStore.getState().finishCaseRun(record)
    } catch (err) {
      useStore.getState().failCaseRun(err)
    }
  }

  const updateReview = (r: HumanReview) => {
    setReview(r)
    if (caseRecord) saveReview(caseRecord.run_id, r)
  }

  const toggleCheckpoint = (id: string) =>
    updateReview({ ...review, checked: review.checked.includes(id) ? review.checked.filter(x => x !== id) : [...review.checked, id] })

  const exportCase = () => {
    if (!caseRecord) return
    downloadJson(`change-case-${caseRecord.request.moc_id ?? caseRecord.request.asset_id}-${caseRecord.run_id}.json`, {
      notice: 'Advice record, not decision authority. The allocation recommends who should decide; the organisation\'s approver decides.',
      exported_at: new Date().toISOString(),
      case: caseRecord,
      human_review: review,
    })
  }

  const openAllocation = () => {
    if (!caseRecord) return
    if (!caseRecord.request.moc_id) {
      setCurrentChange({
        changeType: caseRecord.request.change_type, assetId: caseRecord.request.asset_id,
        description: caseRecord.request.description,
      })
      setAllocationIntent('proposed')
    }
    setActiveTab(ALLOCATION_TAB)
    navigate(pathForTab(ALLOCATION_TAB))
  }

  const tooShort = currentChange.description.trim().length < 5
  const c = caseRecord
  const why = c?.why_trust
  const names = Object.fromEntries((why?.contributions ?? []).map(x => [x.agent, x.name]))
  const agentsOk = why ? why.contributions.filter(x => x.status === 'ok').length : 0
  const elapsed = caseRun.startedAt ? Math.max(0, Math.round((now - caseRun.startedAt) / 1000)) : 0

  return (
    <div className="moc-case-grid grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-5">
      {/* ── Main column, top: the change ── */}
      <div className="min-w-0 space-y-5 xl:col-start-1 xl:row-start-1">
        <div>
          <h2 className="text-lg font-bold text-white">Change Case</h2>
          <p className="text-sm text-white/50 mt-1">
            Describe one engineering change. Specialist agents reuse the platform&apos;s graph, risk, review, cost and allocation
            analyses; a verification agent checks their claims; you review the result. Three questions are answered: what
            happens, who should decide, and why the recommendation can be trusted.
          </p>
        </div>

        <Card className="no-print space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Select label="Change type" value={currentChange.changeType} onChange={v => edit({ changeType: v })} options={CHANGE_TYPES} />
            <Select label="Asset" value={currentChange.assetId} onChange={v => edit({ assetId: v })} options={ASSET_IDS} />
          </div>
          <Textarea label="Describe the proposed change" rows={3} value={currentChange.description}
            onChange={v => edit({ description: v })}
            placeholder="e.g. Replace FV-103 with a smart control valve to improve temperature regulation…" />
          <div className="flex flex-wrap items-center gap-3">
            <Btn onClick={assess} loading={running} disabled={tooShort || !registry.data}>
              <Workflow className="h-4 w-4" strokeWidth={1.75} />
              Assess change
            </Btn>
            <Btn variant="ghost" onClick={loadExample} disabled={running}>
              <BookOpen className="h-4 w-4" strokeWidth={1.75} />
              Load example (MoC-002)
            </Btn>
            {exampleMoc && (
              <span className="inline-flex items-center gap-1.5 rounded-full border border-accent/40 bg-accent/10 px-2.5 py-1 text-[11px] text-accent-soft">
                Example {exampleMoc}: uses its recorded characterisation
                <button type="button" onClick={() => setExampleMoc(null)} aria-label="Treat as a new change" className="text-white/50 hover:text-white">
                  <X className="h-3 w-3" strokeWidth={2} />
                </button>
              </span>
            )}
            {tooShort && <span className="text-xs text-white/40">Add a short description to start.</span>}
          </div>
        </Card>

        <ErrorBox error={registry.error} title="Could not load the agent line-up" />
        {caseRun.phase === 'error' && caseRun.error && <ErrorBox error={new Error(caseRun.error)} title="The assessment could not run" />}
        {running && (
          <div role="status" className="no-print rounded-xl border border-accent/30 bg-accent/10 px-4 py-3 text-sm text-white/75">
            The agents are working on this change ({elapsed} s). A full case usually takes 20 to 60 s; follow each agent on the right.
          </div>
        )}
      </div>

      {/* ── Side column: live agents and activity ── */}
      <aside className="no-print moc-glass-card rounded-2xl p-4 space-y-5 self-start xl:sticky xl:top-20 xl:max-h-[calc(100vh-6rem)] xl:overflow-y-auto xl:col-start-2 xl:row-start-1 xl:row-span-2">
        {registry.data ? (
          <AgentPanel registry={registry.data} run={caseRun} />
        ) : registry.isLoading ? <Spinner text="Loading the agents…" /> : null}
        <div className="h-px bg-white/10" />
        <ActivityFeed entries={caseRun.activity} now={now} />
        {registry.data && (
          <details className="group">
            <summary className="cursor-pointer list-none text-[11px] font-semibold uppercase tracking-widest text-white/45 hover:text-white/70">
              How the agents work together
            </summary>
            <div className="mt-2 space-y-1.5 text-xs text-white/60">
              {registry.data.patterns.map(p => (
                <p key={p.id}><b className="text-white/80">{p.name}.</b> {p.use}</p>
              ))}
            </div>
          </details>
        )}
      </aside>

      {/* ── Main column, below: the case ── */}
      <div className="min-w-0 xl:col-start-1 xl:row-start-2">
      {c && why && !running && (
        <div className="space-y-6">
          <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className="text-xs text-white/40">Case {c.run_id}{c.request.moc_id ? ` · example ${c.request.moc_id}` : ''}</div>
              <h3 className="font-bold text-white">
                <span className="font-mono text-accent mr-2">{c.request.asset_id}</span>{c.request.change_type}
              </h3>
              <p className="text-sm text-white/55 mt-0.5">{c.request.description}</p>
            </div>
            <div className="no-print flex gap-2">
              <Btn variant="ghost" onClick={exportCase}><FileJson className="h-4 w-4" strokeWidth={1.75} />Export JSON</Btn>
              <Btn variant="ghost" onClick={printLight}><Printer className="h-4 w-4" strokeWidth={1.75} />Print</Btn>
            </div>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
            <KpiCard label="Agents OK" value={`${agentsOk} / ${why.counts.agents}`} tone={agentsOk === why.counts.agents ? 'ok' : 'warn'} />
            <KpiCard label="Evidence items" value={why.counts.evidence} sub={`${Object.keys(why.evidence_by_source).length} source kinds`} />
            <KpiCard label="Verified claims" value={why.counts.verified} tone="ok" sub={`${why.counts.unverified} not verified`} />
            <KpiCard label="Conflicts" value={why.counts.conflicts} tone={why.counts.conflicts ? 'danger' : 'ok'} />
            <KpiCard label="Human checkpoints" value={why.checkpoints.length} tone="accent2" />
          </div>

          {/* ── 1 · What happens ── */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-white">1 · What happens if we make this change?</h3>
            <WhatHappens c={c} />
          </section>

          {/* ── 2 · Who decides ── */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-white">2 · Who should make the decision?</h3>
            {c.who_decides ? (
              <>
                <AllocationBanner result={c.who_decides.result} status={c.who_decides.characterisation_status} />
                <div className="flex flex-wrap items-center gap-4">
                  <WhyToggle why={why} focus={['allocation']} label="Why this allocation?" />
                  <button type="button" onClick={openAllocation}
                    className="no-print inline-flex items-center gap-1 text-xs font-semibold text-accent hover:text-accent-soft">
                    Review or adjust the eight axes in Decision Allocation <ArrowRight className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />
                  </button>
                </div>
              </>
            ) : (
              <p className="text-sm text-white/55">The Decision Allocation agent did not complete, so there is no allocation. See the gaps below.</p>
            )}
          </section>

          {/* ── 3 · Why trust it ── */}
          <section className="space-y-3">
            <h3 className="text-base font-bold text-white">3 · Why should we trust the recommendation?</h3>
            <WhyPanel why={why} />
          </section>

          {/* ── Human review ── */}
          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Card className="space-y-3">
              <SectionLabel>Human checkpoints · tick when done</SectionLabel>
              <CheckpointList checkpoints={why.checkpoints} names={names} checked={review.checked} onToggle={toggleCheckpoint} />
            </Card>
            <Card className="space-y-3">
              <SectionLabel>Human review</SectionLabel>
              <ReviewForm review={review} onChange={updateReview} />
            </Card>
          </section>

          <div className="text-[11px] text-white/30">
            Run {c.trace.run_id} · {new Date(c.trace.started_at).toLocaleString()} · {(c.trace.duration_ms / 1000).toFixed(1)} s
            {c.trace.language_model ? ` · language model ${c.trace.language_model}` : ''}
            {c.trace.allocation_model_version ? ` · allocation model v${c.trace.allocation_model_version}` : ''}
          </div>
        </div>
      )}
      </div>
    </div>
  )
}

function WhatHappens({ c }: { c: CaseRecord }) {
  const w = c.what_happens
  const why = c.why_trust
  const reach = w.reach
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Card className="space-y-2">
          <SectionLabel>Equipment and dependencies</SectionLabel>
          {w.asset ? (
            <div className="text-sm text-white/75">
              <span className="font-mono text-accent">{w.asset.asset_id}</span> · {w.asset.equipment_type ?? 'type not recorded'}
              {w.asset.criticality != null && <> · criticality {w.asset.criticality}</>}
              {w.areas?.length ? <> · {w.areas.join(', ')}</> : null}
              {w.esd_target && <span style={{ color: cssVar('warn') }}> · ESD target</span>}
            </div>
          ) : <p className="text-sm text-white/50">The asset could not be read from the knowledge graph.</p>}
          {reach && (
            <ul className="text-sm text-white/65 space-y-1">
              <li><b className="text-white/85">{reach.asset_count}</b> assets reachable through process and control links{reach.areas.length ? `, across ${reach.areas.join(', ')}` : ''}.</li>
              {reach.direct.length > 0 && <li>Directly affected: <span className="font-mono text-white/80">{reach.direct.join(', ')}</span></li>}
              {reach.critical_assets.length > 0 && <li>Critical assets reached: <span className="font-mono text-white/80">{reach.critical_assets.join(', ')}</span></li>}
            </ul>
          )}
          {w.propagation.total_propagated_hours != null && (
            <p className="text-sm text-white/65">
              A {w.propagation.source_downtime ?? 24}-hour outage here would propagate about{' '}
              <b className="text-white/85">{w.propagation.total_propagated_hours.toFixed(1)} h</b> of downtime to {w.propagation.total_affected ?? 0} other assets.
            </p>
          )}
          <WhyToggle why={why} focus={['impact']} label="Why this impact?" />
        </Card>

        <Card className="space-y-2">
          <div className="flex items-center justify-between gap-2">
            <SectionLabel>Risks</SectionLabel>
            {w.risk.overall_rating && <RiskBadge rating={w.risk.overall_rating} />}
          </div>
          {w.risk.risks?.length ? (
            <ul className="space-y-1.5">
              {w.risk.risks.slice(0, 5).map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-white/70"><RiskBadge rating={r.severity} /><span>{r.description}</span></li>
              ))}
            </ul>
          ) : <p className="text-sm text-white/50">No risk analysis is available.</p>}
          {w.risk.mitigations?.length ? (
            <div className="text-xs text-white/55"><b className="text-white/70">Mitigations:</b> {w.risk.mitigations.slice(0, 4).map(m => m.replace(/[.;\s]+$/, '')).join('; ')}.</div>
          ) : null}
          <WhyToggle why={why} focus={['risk']} label="Why these risks?" />
        </Card>

        <Card className="space-y-2">
          <SectionLabel>Review requirements</SectionLabel>
          <div className="grid grid-cols-2 gap-2">
            <FlagTile compact label="HAZOP" value={w.review.hazop_required ?? w.risk.hazop_triggered} />
            <FlagTile compact label="PSSR" value={w.review.pssr_required ?? w.risk.pssr_required} />
          </div>
          {w.review.approvers?.length ? <div className="text-xs text-white/60"><b className="text-white/75">Approvers:</b> {w.review.approvers.join(', ')}</div> : null}
          {w.review.documents?.length ? <div className="text-xs text-white/60"><b className="text-white/75">Documents:</b> {w.review.documents.join(', ')}</div> : null}
          {w.review.pid_tags?.length ? <div className="text-xs text-white/60"><b className="text-white/75">P&amp;IDs:</b> <span className="font-mono">{w.review.pid_tags.join(', ')}</span></div> : null}
          <WhyToggle why={why} focus={['review']} label="Why these review needs?" />
        </Card>

        <Card className="space-y-3">
          <SectionLabel>Cost and downtime</SectionLabel>
          {w.cost.cost_estimate != null && w.cost.cost_ci ? (
            <CIBar label="Cost" estimate={Math.round(w.cost.cost_estimate)} low={w.cost.cost_ci[0]} high={w.cost.cost_ci[1]} prefix="$" />
          ) : <p className="text-sm text-white/50">No cost estimate is available.</p>}
          {w.cost.downtime_estimate != null && w.cost.downtime_ci && (
            <CIBar label="Downtime" estimate={w.cost.downtime_estimate} low={w.cost.downtime_ci[0]} high={w.cost.downtime_ci[1]} suffix=" h" />
          )}
          {w.cost.cost_estimate != null && (
            <div className="text-[11px] text-white/40">
              Estimate {money(w.cost.cost_estimate)} using category {w.cost.asset_category ?? 'n/a'} and risk level {w.cost.risk_level_used ?? 'n/a'}.
            </div>
          )}
          <WhyToggle why={why} focus={['cost']} label="Why this estimate?" />
        </Card>
      </div>

      {w.similar_changes.length > 0 && (
        <Card className="space-y-2">
          <SectionLabel>Similar past changes</SectionLabel>
          <ul className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-1">
            {w.similar_changes.map(s => (
              <li key={s.moc_id} className="flex items-baseline justify-between gap-2 text-sm border-b border-white/5 py-1">
                <span className="text-white/70"><span className="font-mono text-accent mr-2">{s.moc_id}</span>{s.title}</span>
                {s.similarity != null && <span className="text-[11px] text-white/40">{Math.round(s.similarity * 100)}% similar</span>}
              </li>
            ))}
          </ul>
          <WhyToggle why={why} focus={['retrieval']} label="Why these matches?" />
        </Card>
      )}
    </div>
  )
}
