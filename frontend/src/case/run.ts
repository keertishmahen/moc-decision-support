/**
 * Live state of a Change Case run: each agent's status and the activity feed.
 * Pure functions over streamed progress events; the store (src/store.ts) holds the state so a
 * run keeps going when the user switches tabs.
 */
import type { Token } from '../theme/palette'
import type { AgentStatus, CaseEvent, CaseRecord } from './api'

export type LiveStatus = AgentStatus | 'waiting' | 'running'

export interface LiveAgent { status: LiveStatus; durationMs?: number; summary?: string }

export interface ActivityEntry { id: number; text: string; tone: Token; at: number }

export interface CaseRun {
  phase: 'idle' | 'running' | 'done' | 'error'
  startedAt: number | null
  agents: Record<string, LiveAgent>
  activity: ActivityEntry[]
  error: string | null
}

/** "Risk Assessment Agent" -> "Risk Assessment" for the compact panel. */
export const shortName = (name: string) => name.replace(/ Agent$/, '')

const seconds = (ms: number) => `${(ms / 1000).toFixed(1)} s`

let nextId = 1
const entry = (text: string, tone: Token): ActivityEntry => ({ id: nextId++, text, tone, at: Date.now() })
const log = (run: CaseRun, text: string, tone: Token): CaseRun => ({ ...run, activity: [entry(text, tone), ...run.activity].slice(0, 60) })

export const idleRun = (): CaseRun => ({
  phase: 'idle', startedAt: null, agents: {}, error: null,
  activity: [entry('Ready. Describe a change or load the example.', 'slate')],
})

export function startRun(agentIds: string[]): CaseRun {
  return {
    phase: 'running', startedAt: Date.now(), error: null,
    agents: Object.fromEntries(agentIds.map(id => [id, { status: 'waiting' as LiveStatus }])),
    activity: [entry('Initializing agent pipeline…', 'accent')],
  }
}

const FINISHED: Record<AgentStatus, { label: string; tone: Token }> = {
  ok: { label: 'Complete', tone: 'ok' },
  degraded: { label: 'Partial result', tone: 'warn' },
  failed: { label: 'Failed', tone: 'danger' },
  skipped: { label: 'Skipped', tone: 'slate' },
}

/** Apply one streamed progress event. `names` maps agent id -> display name. */
export function applyEvent(run: CaseRun, e: CaseEvent, names: Record<string, string>): CaseRun {
  const setAgent = (r: CaseRun, id: string, patch: LiveAgent) => ({ ...r, agents: { ...r.agents, [id]: patch } })
  switch (e.type) {
    case 'run_started':
      return log(run, `Plan: ${e.stages.flat().length} agents in ${e.stages.length} stages`, 'slate')
    case 'stage_started':
      return log(run, `Stage ${e.stage}: ${e.agents.map(a => shortName(names[a] ?? a)).join(' and ')}`, 'slate')
    case 'agent_started':
      return log(setAgent(run, e.agent, { status: 'running' }), `${shortName(e.name)} — Analyzing…`, 'accent')
    case 'agent_finished': {
      const f = FINISHED[e.status]
      return log(setAgent(run, e.agent, { status: e.status, durationMs: e.duration_ms, summary: e.summary }),
        `${shortName(e.name)} — ${f.label} · ${seconds(e.duration_ms)}`, f.tone)
    }
    case 'agent_skipped':
      return log(setAgent(run, e.agent, { status: 'skipped', summary: `Skipped: ${e.reason}` }),
        `${shortName(e.name)} — Skipped (${e.reason})`, 'slate')
    case 'run_finished': {
      const c = e.counts.conflicts
      return log(run, `Verification — ${c} ${c === 1 ? 'conflict' : 'conflicts'}, ${e.checkpoints} human checkpoints`,
        c ? 'danger' : 'ok')
    }
  }
}

export function fallbackRun(run: CaseRun): CaseRun {
  return log(run, 'Live progress unavailable here; waiting for the full case…', 'warn')
}

/** Settle the run from the finished case (also fills in agents if progress was not streamed). */
export function finishRun(run: CaseRun, record: CaseRecord): CaseRun {
  const agents = { ...run.agents }
  for (const c of record.why_trust.contributions) {
    if (c.agent !== 'supervisor') agents[c.agent] = { status: c.status, durationMs: c.duration_ms, summary: c.summary }
  }
  return log({ ...run, phase: 'done', agents }, `Case ready · ${seconds(record.trace.duration_ms)}`, 'ok')
}

export function failRun(run: CaseRun, error: unknown): CaseRun {
  const agents = Object.fromEntries(Object.entries(run.agents).map(([id, a]) =>
    [id, a.status === 'running' || a.status === 'waiting' ? { status: 'skipped' as LiveStatus } : a]))
  const message = error instanceof Error ? error.message : String(error)
  return log({ ...run, phase: 'error', agents, error: message }, `Assessment failed: ${message}`, 'danger')
}

/** "now", "12 s", "3 min" */
export function ago(at: number, now: number): string {
  const s = Math.max(0, Math.round((now - at) / 1000))
  if (s < 5) return 'now'
  if (s < 60) return `${s} s`
  return `${Math.round(s / 60)} min`
}
