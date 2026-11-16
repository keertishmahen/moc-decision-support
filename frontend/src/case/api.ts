/**
 * Change Case — typed client for /api/case/* and the provenance shared with /api/allocation/*.
 *
 * The agent line-up, patterns and source kinds come from GET /api/case/agents; nothing about
 * them is restated here beyond display names and icons.
 */
import { API_ORIGIN, api } from '../api'
import type { AllocationAssessment } from '../allocation/api'

export type SourceKind =
  | 'ontology' | 'knowledge_graph' | 'engineering_record' | 'document' | 'computational_model'
  | 'ml_model' | 'llm_interpretation' | 'user_input' | 'assumption'
export type Basis = 'deterministic' | 'rule' | 'ml' | 'llm' | 'retrieval'
export type Verification = 'verified' | 'unverified' | 'conflict' | 'not_applicable'
export type AgentStatus = 'ok' | 'degraded' | 'failed' | 'skipped'
export type CheckpointKind = 'verification' | 'approval'

export interface Evidence {
  id: string; source: SourceKind; reference: string; label: string; detail: string
}

export interface Finding {
  id: string; statement: string; agent: string; basis: Basis; evidence: string[]
  confidence: string | null; verification: Verification; note: string
}

export interface Gap { kind: 'assumption' | 'uncertainty' | 'missing'; agent: string; text: string }

export interface Checkpoint {
  id: string; kind: CheckpointKind; what: string; why: string; role: string; raised_by: string
}

export interface Contribution {
  agent: string; name: string; role: string; pattern: string; stage: number; basis: Basis
  components: string[]; sources: SourceKind[]; status: AgentStatus; duration_ms: number
  summary: string; findings: Finding[]; gaps: Gap[]; error: string
}

/** The "why trust it" part of a case, and the `provenance` on allocation responses. */
export interface Provenance {
  contributions: Contribution[]
  evidence: Evidence[]
  evidence_by_source: Partial<Record<SourceKind, Evidence[]>>
  findings: Finding[]
  conflicts: Finding[]
  assumptions: Gap[]
  uncertainties: Gap[]
  missing: Gap[]
  checkpoints: Checkpoint[]
  counts: { agents: number; evidence: number; findings: number; verified: number; unverified: number; conflicts: number }
}

export interface AgentSpec {
  id: string; name: string; role: string; pattern: string; stage: number; basis: Basis
  components: string[]; sources: SourceKind[]; needs: string[]; reads: string[]
}

export interface AgentRegistry {
  patterns: { id: string; name: string; use: string }[]
  supervisor: AgentSpec
  agents: AgentSpec[]
  stages: string[][]
  source_kinds: { id: SourceKind; label: string }[]
}

export interface ReachAsset {
  asset_id: string; equipment_type: string | null; criticality: number | null; hops: number; area: string | null
}

export interface WhatHappens {
  asset: { asset_id: string; name?: string | null; equipment_type: string | null; criticality: number | null } | null
  areas: string[] | null
  esd_target: boolean | null
  reach: { assets: ReachAsset[]; asset_count: number; areas: string[]; critical_assets: string[]; direct: string[] } | null
  propagation: { source_downtime: number | null; total_affected: number | null; total_propagated_hours: number | null; summary: string | null }
  risk: {
    overall_rating: string | null; risks: { severity: string; description: string }[] | null
    mitigations: string[] | null; hazop_triggered: string | null; pssr_required: string | null
    reasoning: string | null; directly_affected: string[] | null; indirectly_affected: string[] | null
    llm_status: string | null
  }
  review: {
    approvers: string[] | null; documents: string[] | null; hazop_required: string | null
    pssr_required: string | null; pid_tags: string[] | null; risk_level: string | null; llm_status: string | null
  }
  cost: {
    cost_estimate: number | null; cost_ci: [number, number] | null; downtime_estimate: number | null
    downtime_ci: [number, number] | null; explanation: string | null; asset_category: string | null
    risk_level_used: string | null; llm_status: string | null
  }
  similar_changes: { moc_id: string; similarity: number | null; title: string | null }[]
}

export interface CaseRequest {
  change_type: string; asset_id: string; description: string; moc_id?: string | null
}

export interface CaseRecord {
  run_id: string
  request: CaseRequest
  what_happens: WhatHappens
  who_decides: (AllocationAssessment & { provenance?: Provenance }) | null
  why_trust: Provenance
  trace: {
    run_id: string; started_at: string; duration_ms: number
    stages: { stage: number; agents: string[] }[]
    agents: { agent: string; status: AgentStatus; duration_ms: number }[]
    language_model?: string; allocation_model_version?: string
  }
}

/** What a reviewer records against a case. Kept in this browser only and exported with the case. */
export interface HumanReview {
  reviewer: string
  role: string
  decision: '' | 'accept' | 'accept_with_changes' | 'reject' | 'escalate'
  notes: string
  checked: string[]          // checkpoint ids the reviewer has dealt with
  recorded_at: string | null
}

/** Progress events streamed by POST /api/case/assess/stream (one JSON object per line). */
export type CaseEvent =
  | { type: 'run_started'; run_id: string; stages: string[][] }
  | { type: 'stage_started'; stage: number; agents: string[] }
  | { type: 'agent_started'; agent: string; name: string; stage: number }
  | { type: 'agent_finished'; agent: string; name: string; status: AgentStatus; duration_ms: number; summary: string }
  | { type: 'agent_skipped'; agent: string; name: string; reason: string }
  | { type: 'run_finished'; duration_ms: number; counts: Provenance['counts']; checkpoints: number }

type StreamLine = CaseEvent | { type: 'case'; case: CaseRecord } | { type: 'error'; status: number; detail: string }

export const getCaseAgents = () => api.get<AgentRegistry>('/case/agents').then(r => r.data)

export const assessCase = (body: CaseRequest) =>
  api.post<CaseRecord>('/case/assess', body, { timeout: 300_000 }).then(r => r.data)

/** Raised for an answer from the server (bad input, failed run): not worth retrying without streaming. */
class CaseServerError extends Error {}

/**
 * Run a case with live progress. Each progress event goes to `onEvent`; the promise resolves
 * with the case record. If streaming is unavailable before any event arrives (network, a
 * buffering proxy), it falls back to the plain endpoint and calls `onFallback`.
 */
export async function streamCase(
  body: CaseRequest, onEvent: (e: CaseEvent) => void, onFallback: () => void,
): Promise<CaseRecord> {
  let received = false
  try {
    const res = await fetch(`${API_ORIGIN}/api/case/assess/stream`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
    if (!res.ok) {
      const data = await res.json().catch(() => null)
      const detail = data?.detail
      throw new CaseServerError(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : `Request failed (${res.status})`)
    }
    if (!res.body) throw new Error('Streaming is not supported here')
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    for (;;) {
      const { value, done } = await reader.read()
      if (value) buffer += decoder.decode(value, { stream: true })
      let nl = buffer.indexOf('\n')
      while (nl >= 0) {
        const line = buffer.slice(0, nl).trim()
        buffer = buffer.slice(nl + 1)
        nl = buffer.indexOf('\n')
        if (!line) continue
        const msg = JSON.parse(line) as StreamLine
        received = true
        if (msg.type === 'case') return msg.case
        if (msg.type === 'error') throw new CaseServerError(msg.detail)
        onEvent(msg)
      }
      if (done) break
    }
    throw new Error('The progress stream ended before the case was ready')
  } catch (err) {
    if (err instanceof CaseServerError || received) throw err
    onFallback()
    return assessCase(body)
  }
}
