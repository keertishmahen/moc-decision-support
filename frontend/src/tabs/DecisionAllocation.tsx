import React, { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { Download, Scale } from 'lucide-react'
import { Btn, Card, ErrorBox, SectionLabel, Select, Spinner, Textarea } from '../components/ui'
import { ASSET_IDS, CHANGE_TYPES } from '../constants'
import { useStore } from '../store'
import {
  assessChangeAllocation, assessMocAllocation, getAllocationCases, getAllocationEnumeration,
  getAllocationMocs, getAllocationModel, scoreAllocation,
  type AllocationAssessment, type AllocationResult, type AxisSelection,
} from '../allocation/api'
import {
  AllocationBanner, AxisField, Explanation, FactorMatrix, ImpactSummary, ModelCard,
  ReferenceCasesTable, ScoreTile,
} from '../allocation/components'

type Mode = 'moc' | 'proposed'
const HAZOP_OPTIONS = ['Not known', 'Required', 'Not required']
const toFlag = (v: string): boolean | null => (v === 'Required' ? true : v === 'Not required' ? false : null)
const fromFlag = (v: boolean | null) => (v === null ? 'Not known' : v ? 'Required' : 'Not required')

export default function DecisionAllocation() {
  const { currentChange, setCurrentChange, allocationIntent, setAllocationIntent } = useStore()
  const [mode, setMode] = useState<Mode>(allocationIntent === 'proposed' ? 'proposed' : 'moc')
  const [mocId, setMocId] = useState('MoC-002')
  const [assessment, setAssessment] = useState<AllocationAssessment | null>(null)
  const [selection, setSelection] = useState<AxisSelection | null>(null)
  const [result, setResult] = useState<AllocationResult | null>(null)

  const model = useQuery({ queryKey: ['allocation-model'], queryFn: getAllocationModel, staleTime: Infinity })
  const mocs = useQuery({ queryKey: ['allocation-mocs'], queryFn: getAllocationMocs, staleTime: 5 * 60_000 })
  const cases = useQuery({ queryKey: ['allocation-cases'], queryFn: getAllocationCases, staleTime: 5 * 60_000 })
  const enumeration = useQuery({ queryKey: ['allocation-enumeration'], queryFn: getAllocationEnumeration, staleTime: Infinity })

  const accept = (a: AllocationAssessment) => {
    setAssessment(a)
    setSelection(a.selection)
    setResult(a.result)
  }

  const assess = useMutation({
    mutationFn: (target: { mode: Mode; mocId: string }) =>
      target.mode === 'moc'
        ? assessMocAllocation(target.mocId)
        : assessChangeAllocation({
            change_type: currentChange.changeType,
            asset_id: currentChange.assetId,
            description: currentChange.description,
            hazop_required: currentChange.hazopRequired,
            pssr_required: currentChange.pssrRequired,
          }),
    onSuccess: accept,
  })

  const rescore = useMutation({ mutationFn: scoreAllocation, onSuccess: setResult })

  // Arriving from another tab assesses the change in hand; otherwise open on the thesis'
  // discriminating case (MoC-002) so the screen is never empty.
  useEffect(() => {
    if (allocationIntent === 'proposed') {
      setAllocationIntent(null)
      assess.mutate({ mode: 'proposed', mocId })
    } else {
      assess.mutate({ mode: 'moc', mocId: 'MoC-002' })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const setAxis = (axisId: string, categoryId: string) => {
    if (!selection) return
    const next = { ...selection, [axisId]: categoryId }
    setSelection(next)
    rescore.mutate(next)
  }

  const openMoc = (id: string) => {
    setMode('moc')
    setMocId(id)
    assess.mutate({ mode: 'moc', mocId: id })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const mocOptions = useMemo(() => {
    const rows = mocs.data?.mocs ?? []
    return rows.length ? rows.map(m => m.moc_id) : Array.from({ length: 10 }, (_, i) => `MoC-${String(i + 1).padStart(3, '0')}`)
  }, [mocs.data])

  const edited = !!(assessment && selection && Object.keys(selection).some(k => selection[k] !== assessment.selection[k]))
  const status = edited ? 'edited by you' : (assessment?.characterisation_status ?? 'suggested')

  const exportJson = () => {
    if (!assessment || !selection || !result) return
    const payload = { subject: assessment.subject, selection, status, result, exported_at: new Date().toISOString() }
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `decision-allocation-${assessment.subject.moc_id ?? 'proposed-change'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const axisById = useMemo(
    () => Object.fromEntries((assessment?.axes ?? []).map(a => [a.axis_id, a])),
    [assessment],
  )

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-bold text-white">Human–AI Decision Allocation</h2>
        <p className="text-sm text-white/50 mt-1">
          Who should decide this change? Eight characteristics are scored for risk, complexity, uncertainty and impact,
          and mapped to AI-led, AI-supported or human-led control. The platform suggests; you confirm; the scoring is deterministic.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2 space-y-3">
          <div className="flex gap-2" role="tablist" aria-label="What to assess">
            {(['moc', 'proposed'] as const).map(m => (
              <button key={m} type="button" role="tab" aria-selected={mode === m} onClick={() => setMode(m)}
                className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition-colors ${mode === m ? 'bg-[#4f8ef7]/20 text-white border border-[#4f8ef7]/50' : 'border border-white/10 text-white/50 hover:text-white/80'}`}>
                {m === 'moc' ? 'Existing MoC record' : 'Proposed change'}
              </button>
            ))}
          </div>

          {mode === 'moc' ? (
            <Select label="MoC record" value={mocId} onChange={setMocId} options={mocOptions} />
          ) : (
            <>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <Select label="Change Type" value={currentChange.changeType} onChange={v => setCurrentChange({ changeType: v })} options={CHANGE_TYPES} />
                <Select label="Asset ID" value={currentChange.assetId} onChange={v => setCurrentChange({ assetId: v })} options={ASSET_IDS} />
                <Select label="HAZOP" value={fromFlag(currentChange.hazopRequired)} onChange={v => setCurrentChange({ hazopRequired: toFlag(v) })} options={HAZOP_OPTIONS} />
              </div>
              <Textarea label="Describe the proposed change" value={currentChange.description} rows={3}
                onChange={v => setCurrentChange({ description: v })}
                placeholder="e.g. Temporary bypass of feed pump P-101 while the seal is replaced…" />
            </>
          )}

          <div className="flex flex-wrap items-center gap-3">
            <Btn onClick={() => assess.mutate({ mode, mocId })} loading={assess.isPending}>
              <Scale className="h-4 w-4" strokeWidth={1.75} />
              Assess and allocate
            </Btn>
            <Btn variant="ghost" onClick={exportJson} disabled={!result}>
              <Download className="h-4 w-4" strokeWidth={1.75} />
              Export
            </Btn>
            {mode === 'proposed' && !currentChange.description.trim() && (
              <span className="text-xs text-white/40">A description improves the suggestions.</span>
            )}
          </div>
        </Card>

        <Card className="text-sm text-white/60 space-y-2">
          <SectionLabel>How it works</SectionLabel>
          <p><b className="text-white/80">1.</b> The knowledge graph supplies the impact assessment: target asset, dependencies, HAZOP/PSSR, risk assessment.</p>
          <p><b className="text-white/80">2.</b> Each of the eight axes gets a suggested value with its evidence. Change any of them.</p>
          <p><b className="text-white/80">3.</b> A fixed model scores the change and reads Risk, Complexity and Uncertainty against Impact. No AI is involved in the scoring.</p>
        </Card>
      </div>

      <ErrorBox error={assess.error} title="Assessment failed" />
      <ErrorBox error={model.error} title="Could not load the allocation model" />
      {assess.isPending && !assessment && <Spinner text="Reading the knowledge graph…" />}

      {assessment && selection && result && model.data && (
        <div className="space-y-4">
          <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

          <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h3 className="font-bold text-white">
              {assessment.subject.moc_id ? <span className="font-mono text-[#4f8ef7] mr-2">{assessment.subject.moc_id}</span> : null}
              {assessment.subject.title}
            </h3>
            {assessment.subject.case_id && <span className="text-xs text-white/40">thesis case {assessment.subject.case_id}</span>}
          </div>
          {assessment.subject.description && <p className="text-sm text-white/55 -mt-2">{assessment.subject.description}</p>}

          {assessment.graph_status !== 'ok' && (
            <div role="status" className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
              The knowledge graph is unavailable, so there is no impact assessment or suggestion evidence. Scoring still works.
            </div>
          )}

          <AllocationBanner result={result} status={status} />

          {assessment.impact_assessment && <ImpactSummary impact={assessment.impact_assessment} />}

          <div>
            <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
              <SectionLabel>Characterisation · eight axes</SectionLabel>
              {edited && (
                <button type="button" className="text-xs text-[#4f8ef7] hover:text-blue-300"
                  onClick={() => { setSelection(assessment.selection); setResult(assessment.result) }}>
                  Reset all
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
              {model.data.axes.map(a => (
                <AxisField key={a.id} model={a} axis={axisById[a.id]} value={selection[a.id]} onChange={v => setAxis(a.id, v)} />
              ))}
            </div>
            <ErrorBox error={rescore.error} title="Scoring failed" />
          </div>

          <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
            {result.dimensions.map(d => <ScoreTile key={d.id} dim={d} />)}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {result.factors.map(f => <FactorMatrix key={f.dimension_id} factor={f} matrix={model.data.factor_matrix} />)}
          </div>

          <Explanation result={result} />
        </div>
      )}

      <div className="h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

      {cases.isLoading && <Spinner text="Loading reference cases…" />}
      <ErrorBox error={cases.error} title="Could not load the reference cases" />
      {cases.data && <ReferenceCasesTable cases={cases.data} onOpen={openMoc} />}

      {model.data && <ModelCard model={model.data} enumeration={enumeration.data} />}
    </div>
  )
}
