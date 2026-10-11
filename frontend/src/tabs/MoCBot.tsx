import React, { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Bot, MessageSquare, Network, Send, Trash2, Zap } from 'lucide-react'
import { sendChat, resetChat, getGraphContext, propagateDowntime, runAgent } from '../api'
import { useStore } from '../store'
import { Btn, Input, RiskBadge, SectionLabel, Card, Spinner } from '../components/ui'
import KnowledgeGraph from '../components/KnowledgeGraph'
import MarkdownMessage from '../components/MarkdownMessage'
import { motion, AnimatePresence } from 'framer-motion'

// ── Quick prompts split by category ───────────────────────────────────────
const QUICK_PROMPTS_STANDARD = [
  { label: 'MoC-010 details',  msg: 'What changed in MoC-010 and what were the key lessons?' },
  { label: 'HAZOP list',       msg: 'Which MoCs required HAZOP and why?' },
  { label: 'SV-204 risks',     msg: 'What are the risks and mitigations for modifying SV-204?' },
  { label: 'All incidents',    msg: 'Which MoCs had incidents or near misses?' },
  { label: 'MoC-005 cost',     msg: 'What was the actual cost of MoC-005?' },
  { label: 'Approval chain',   msg: 'Who approved MoC-003 and what were the approval stages?' },
]

const QUICK_PROMPTS_CONNECTIVITY = [
  { label: 'SV-204 network',   msg: 'What is the effect on downstream and upstream processes if we replace SV-204 actuator? Which assets are most and least affected?' },
  { label: 'R-201 offline',    msg: 'What would happen to the process network if R-201 goes offline for 48 hours?' },
  { label: 'CTL-205 impact',   msg: 'If CTL-205 fails, what is the propagated downtime across the FCC unit?' },
  { label: 'RG-401 topology',  msg: 'Show me the full connectivity of the regenerator RG-401 — upstream and downstream.' },
]

const QUICK_PROMPTS_AGENT = [
  { label: 'Compare instr. MoCs', msg: 'Compare the risk profiles of all instrumentation MoCs (MoC-002 and MoC-005).' },
  { label: 'Highest risk asset',  msg: 'Which asset in the FCC unit has the highest connectivity score and why is it the most critical?' },
  { label: 'Feed section impact', msg: 'Analyse the complete impact chain if P-101 feed pump fails — trace all downstream effects.' },
]

// ── Propagation result panel ───────────────────────────────────────────────
function PropagationPanel({ assetId, hours }: { assetId: string; hours: number }) {
  const { data, mutate, isPending } = useMutation({
    mutationFn: () => propagateDowntime({ asset_id: assetId, downtime_hours: hours }),
  })

  useEffect(() => { mutate() }, [assetId, hours])

  if (isPending) return <Spinner text="Computing propagation…" />
  if (!data) return null

  const affected = (data.affected_assets ?? []) as Record<string, unknown>[]
  const RISK_COLORS: Record<string, string> = {
    Critical: '#ef4444', High: '#f87171', Medium: '#fbbf24', Low: '#34d399',
  }

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-3 gap-2 text-center">
        <div className="moc-glass-card rounded-xl p-2">
          <div className="text-[10px] text-white/40 uppercase tracking-widest">Source</div>
          <div className="text-sm font-bold text-[#4f8ef7]">{data.source_downtime}h</div>
        </div>
        <div className="moc-glass-card rounded-xl p-2">
          <div className="text-[10px] text-white/40 uppercase tracking-widest">Affected</div>
          <div className="text-sm font-bold text-red-400">{data.total_affected}</div>
        </div>
        <div className="moc-glass-card rounded-xl p-2">
          <div className="text-[10px] text-white/40 uppercase tracking-widest">Total hrs</div>
          <div className="text-sm font-bold text-amber-400">{data.total_propagated_hours}h</div>
        </div>
      </div>
      <div className="space-y-1 max-h-40 overflow-y-auto">
        {affected.slice(0, 8).map((a, i) => {
          const color = RISK_COLORS[String(a.risk_level)] ?? '#64748b'
          const pct = Math.min(100, (Number(a.propagated_hours) / (data.source_downtime as number)) * 100)
          return (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <span className="font-mono text-[#4f8ef7] w-14 flex-shrink-0">{String(a.asset_id)}</span>
              <div className="flex-1 h-1.5 rounded-full bg-white/8">
                <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
              </div>
              <span className="w-10 text-right font-semibold" style={{ color }}>{Number(a.propagated_hours).toFixed(1)}h</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Agent tool call log ────────────────────────────────────────────────────
function AgentToolLog({ toolCalls }: { toolCalls: Record<string, unknown>[] }) {
  if (!toolCalls?.length) return null
  return (
    <details className="group mt-2">
      <summary className="cursor-pointer text-[10px] text-[#a78bfa]/60 hover:text-[#a78bfa] list-none flex items-center gap-1 transition-colors">
        <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
        🔧 {toolCalls.length} tool call{toolCalls.length !== 1 ? 's' : ''} made
      </summary>
      <div className="mt-1.5 space-y-1">
        {toolCalls.map((tc, i) => (
          <div key={i} className="rounded-lg border border-white/5 bg-white/[0.02] px-2.5 py-1.5 text-[10px]">
            <span className="text-[#a78bfa] font-semibold">{String(tc.tool)}</span>
            <span className="text-white/30 ml-2">{JSON.stringify(tc.args).slice(0, 60)}</span>
          </div>
        ))}
      </div>
    </details>
  )
}

// ── Main MoCBot component ──────────────────────────────────────────────────
export default function MoCBot() {
  const { messages, addMessage, clearMessages, graphContext, lastQuery, setGraphContext } = useStore()
  const [input, setInput]           = useState('')
  const [agentMode, setAgentMode]   = useState(false)
  const [promptTab, setPromptTab]   = useState<'standard' | 'connectivity' | 'agent'>('standard')
  const [propAsset, setPropAsset]   = useState<string | null>(null)
  const [propHours, setPropHours]   = useState(26)
  const [agentToolCalls, setAgentToolCalls] = useState<Record<string, unknown>[]>([])
  const [graphError, setGraphError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  const loadGraph = (msg: string, assetId?: string, mocId?: string) => {
    setGraphError(null)
    getGraphContext({ query: msg, asset_id: assetId, moc_id: mocId })
      .then(ctx => setGraphContext(ctx, msg))
      .catch((err: unknown) => {
        const text = err instanceof Error ? err.message : 'Graph context failed'
        setGraphError(text)
      })
  }

  // Standard chat mutation
  const chatMut = useMutation({
    mutationFn: (msg: string) => sendChat({ message: msg }),
    onSuccess: (data, msg) => {
      addMessage({ role: 'assistant', content: data.response, intent: data.intent })
      setAgentToolCalls([])
      const aid = data.asset_id_used !== 'none' ? data.asset_id_used : undefined
      const mid = data.moc_id_used   !== 'none' ? data.moc_id_used   : undefined
      // Auto-trigger propagation panel if an asset was identified
      if (aid) { setPropAsset(aid); setPropHours(26) }
      loadGraph(msg, aid, mid)
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Request failed. Please try again.'
      addMessage({ role: 'assistant', content: `⚠️ Error: ${msg}`, intent: 'error' })
    },
  })

  // Agent mutation
  const agentMut = useMutation({
    mutationFn: (msg: string) => runAgent({ query: msg, max_iterations: 6 }),
    onSuccess: (data, msg) => {
      addMessage({ role: 'assistant', content: data.response, intent: 'agent' })
      setAgentToolCalls(data.tool_calls_made ?? [])
      const calls = (data.tool_calls_made ?? []) as Record<string, unknown>[]
      let moc: string | undefined
      let asset: string | undefined
      for (const tc of calls) {
        const args = (tc.args ?? {}) as Record<string, unknown>
        if (!moc && typeof args.moc_id === 'string' && args.moc_id !== 'none') moc = args.moc_id
        if (!asset && typeof args.asset_id === 'string' && args.asset_id !== 'none') asset = args.asset_id
      }
      const mocQ = msg.match(/MoC-\d+/i)
      if (!moc && mocQ) moc = mocQ[0]
      loadGraph(msg, asset, moc)
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Agent request failed.'
      addMessage({ role: 'assistant', content: `⚠️ Error: ${msg}`, intent: 'error' })
    },
  })

  const resetMut = useMutation({
    mutationFn: resetChat,
    onSuccess: () => { clearMessages(); setAgentToolCalls([]) },
  })

  const isPending = chatMut.isPending || agentMut.isPending

  const send = (msg: string) => {
    if (!msg.trim() || isPending) return
    addMessage({ role: 'user', content: msg })
    setInput('')
    if (agentMode) {
      agentMut.mutate(msg)
    } else {
      chatMut.mutate(msg)
    }
  }

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isPending])

  const promptSets = {
    standard:     QUICK_PROMPTS_STANDARD,
    connectivity: QUICK_PROMPTS_CONNECTIVITY,
    agent:        QUICK_PROMPTS_AGENT,
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 h-full">

      {/* ── Chat column ── */}
      <div className="lg:col-span-3 flex flex-col gap-3">

        {/* Header + mode toggle */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">MoCBot</h2>
            <p className="text-xs text-white/40">
              {agentMode
                ? '🤖 Agent mode — multi-step reasoning with tool calling'
                : 'Grounded answers from Neo4j + ChromaDB · No hallucination'}
            </p>
          </div>
          <button
            onClick={() => setAgentMode(v => !v)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
              agentMode
                ? 'bg-[#a78bfa]/20 border-[#a78bfa]/40 text-[#c4b5fd]'
                : 'bg-white/5 border-white/10 text-white/50 hover:text-white/80'
            }`}>
            <span className={`w-2 h-2 rounded-full ${agentMode ? 'bg-[#a78bfa] shadow-[0_0_6px_#a78bfa]' : 'bg-white/20'}`} />
            {agentMode ? 'Agent ON' : 'Agent OFF'}
          </button>
        </div>

        {/* Prompt category tabs */}
        <div className="flex gap-1">
          {(['standard', 'connectivity', 'agent'] as const).map(tab => (
            <button key={tab} onClick={() => setPromptTab(tab)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-medium transition-all ${
                promptTab === tab
                  ? 'bg-[#4f8ef7]/20 border border-[#4f8ef7]/30 text-[#93c5fd]'
                  : 'bg-white/[0.03] border border-white/8 text-white/40 hover:text-white/70'
              }`}>
              {tab === 'standard' ? (
                <><MessageSquare className="h-3.5 w-3.5" strokeWidth={1.75} /> General</>
              ) : tab === 'connectivity' ? (
                <><Network className="h-3.5 w-3.5" strokeWidth={1.75} /> Network</>
              ) : (
                <><Bot className="h-3.5 w-3.5" strokeWidth={1.75} /> Agent</>
              )}
            </button>
          ))}
        </div>

        {/* Quick prompts */}
        <div className="flex flex-wrap gap-2">
          {promptSets[promptTab].map(p => (
            <button key={p.label}
              onClick={() => {
                if (promptTab === 'agent') setAgentMode(true)
                send(p.msg)
              }}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all ${
                promptTab === 'agent'
                  ? 'bg-[#a78bfa]/10 border border-[#a78bfa]/25 text-[#c4b5fd] hover:bg-[#a78bfa]/20'
                  : promptTab === 'connectivity'
                  ? 'bg-emerald-500/10 border border-emerald-500/25 text-emerald-400 hover:bg-emerald-500/20'
                  : 'bg-[#4f8ef7]/10 border border-[#4f8ef7]/25 text-[#93c5fd] hover:bg-[#4f8ef7]/20'
              }`}>
              {p.label}
            </button>
          ))}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-3 min-h-[300px] max-h-[460px] pr-1">
          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}
                className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                  m.role === 'user'
                    ? 'bg-[#4f8ef7]/20 text-[#4f8ef7]'
                    : m.intent === 'agent'
                    ? 'bg-[#a78bfa]/30 text-[#a78bfa]'
                    : 'bg-[#a78bfa]/20 text-[#a78bfa]'}`}>
                  {m.role === 'user' ? 'U' : m.intent === 'agent' ? (
                    <Bot className="h-3.5 w-3.5" strokeWidth={1.75} />
                  ) : (
                    <Zap className="h-3.5 w-3.5" strokeWidth={1.75} />
                  )}
                </div>
                <div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  m.role === 'user'
                    ? 'bg-[#4f8ef7]/15 border border-[#4f8ef7]/20 text-white'
                    : m.intent === 'agent'
                    ? 'bg-[#a78bfa]/08 border border-[#a78bfa]/20 text-white/90'
                    : 'bg-white/[0.045] border border-white/10 text-white/90'}`}>
                  {m.role === 'assistant'
                    ? <MarkdownMessage content={m.content} />
                    : m.content
                  }
                  {/* Show agent tool calls on last assistant message */}
                  {m.role === 'assistant' && i === messages.length - 1 && agentToolCalls.length > 0 && (
                    <AgentToolLog toolCalls={agentToolCalls} />
                  )}
                  {m.intent && !['general', 'agent'].includes(m.intent) && (
                    <div className="mt-1.5 text-[10px] text-white/30 font-mono">intent: {m.intent}</div>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {isPending && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                agentMode ? 'bg-[#a78bfa]/30 text-[#a78bfa]' : 'bg-[#a78bfa]/20 text-[#a78bfa]'}`}>
                {agentMode ? <Bot className="h-3.5 w-3.5" strokeWidth={1.75} /> : <Zap className="h-3.5 w-3.5" strokeWidth={1.75} />}
              </div>
              <div className="moc-glass-card rounded-2xl px-4 py-3 flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/20 border-t-[#a78bfa] rounded-full animate-spin" />
                <span className="text-sm text-white/50">
                  {agentMode ? 'Agent reasoning — calling tools…' : 'Querying knowledge graph…'}
                </span>
              </div>
            </motion.div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <Input value={input} onChange={setInput}
            placeholder={agentMode
              ? 'Ask a complex multi-step question…'
              : 'Ask about MoC history, risks, HAZOP, approvals, process network…'}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send(input)} />
          <Btn onClick={() => send(input)} loading={isPending} disabled={!input.trim()}
            className={agentMode ? 'from-[#a78bfa] to-[#7c6af7]' : ''}>
            {agentMode ? <Bot className="h-4 w-4" strokeWidth={1.75} /> : <Send className="h-4 w-4" strokeWidth={1.75} />}
            Send
          </Btn>
          <Btn variant="ghost" onClick={() => resetMut.mutate()} loading={resetMut.isPending} aria-label="Clear chat">
            <Trash2 className="h-4 w-4" strokeWidth={1.75} />
          </Btn>
        </div>
      </div>

      {/* ── Right panel ── */}
      <div className="lg:col-span-2 space-y-3 overflow-y-auto max-h-[700px]">

        {/* Knowledge Graph */}
        <div>
          <h3 className="font-bold text-white text-sm">Knowledge Graph</h3>
          <p className="text-xs text-white/40">Live graph of retrieved nodes and relationships</p>
        </div>

        {graphError && (
          <p className="text-xs text-red-400/80">Graph unavailable: {graphError}</p>
        )}

        {graphContext ? (
          <>
            <KnowledgeGraph context={graphContext} query={lastQuery} />

            {/* Retrieved MoC */}
            {(graphContext.moc_detail as Record<string, unknown> | undefined) && (() => {
              const d = graphContext.moc_detail as Record<string, unknown>
              return (
                <Card>
                  <SectionLabel>Retrieved MoC</SectionLabel>
                  <div className="text-sm font-semibold text-white">{String(d.moc_id)} — {String(d.title ?? '').slice(0, 45)}</div>
                  <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-white/50">
                    <span>Asset: <span className="text-emerald-400 font-mono">{String(d.asset_id)}</span></span>
                    <RiskBadge rating={String(d.risk_category ?? 'Unknown')} />
                    <span>Score: <span className="text-red-400">{String(d.risk_score ?? '?')}</span></span>
                    <span>Cost: <span className="text-[#4f8ef7]">${Number(d.actual_cost ?? 0).toLocaleString()}</span></span>
                  </div>
                </Card>
              )
            })()}

            {/* Enriched impact chain */}
            {((graphContext.enriched_chain as unknown[]) ?? (graphContext.impact_chain as unknown[]) ?? []).length > 0 && (
              <Card>
                <SectionLabel>Process Impact Chain</SectionLabel>
                {(((graphContext.enriched_chain as Record<string, unknown>[]) ??
                   (graphContext.impact_chain as Record<string, unknown>[])) ?? []).slice(0, 8).map((n, i) => {
                  const hop   = Number(n.hop_distance ?? 1)
                  const crit  = Number(n.criticality ?? 3)
                  const color = hop === 1
                    ? crit >= 5 ? '#ef4444' : '#34d399'
                    : '#a78bfa'
                  const rels  = (n.relationship_chain as string[] | undefined) ?? []
                  return (
                    <div key={i} className="text-xs py-1.5 border-b border-white/5 last:border-0">
                      <div className="flex items-center gap-1.5" style={{ color }}>
                        {'↳'.repeat(hop)}
                        <span className="font-mono font-semibold">{String(n.node_id)}</span>
                        <span className="text-white/40">{String(n.node_name ?? '')}</span>
                        <span className="ml-auto text-[10px] text-white/30">crit={crit}</span>
                      </div>
                      {rels.length > 0 && (
                        <div className="text-[10px] text-white/25 pl-4 mt-0.5">
                          via {rels.join(' → ')}
                        </div>
                      )}
                    </div>
                  )
                })}
              </Card>
            )}

            {/* Downtime propagation — auto-shown when asset identified */}
            {propAsset && (
              <Card>
                <div className="flex items-center justify-between mb-2">
                  <SectionLabel>Downtime Propagation</SectionLabel>
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-white/40">Source hrs:</span>
                    <input type="number" value={propHours}
                      onChange={e => setPropHours(Number(e.target.value))}
                      className="w-12 bg-white/5 border border-white/10 rounded px-1.5 py-0.5 text-[11px] text-white text-center focus:outline-none focus:border-[#4f8ef7]" />
                  </div>
                </div>
                <div className="text-[11px] text-white/40 mb-2">
                  From <span className="text-emerald-400 font-mono">{propAsset}</span>
                </div>
                <PropagationPanel assetId={propAsset} hours={propHours} />
              </Card>
            )}

            {/* Vector hits */}
            {((graphContext.vector_hits as unknown[]) ?? []).length > 0 && (
              <Card>
                <SectionLabel>Vector Similarity</SectionLabel>
                {((graphContext.vector_hits as Record<string, unknown>[]) ?? []).slice(0, 4).map(h => {
                  const sim = Number(h.similarity ?? 0)
                  return (
                    <div key={String(h.moc_id)} className="flex items-center gap-2 py-1.5 border-b border-white/5 last:border-0">
                      <span className="text-xs font-mono text-[#4f8ef7] w-16">{String(h.moc_id)}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-white/8">
                        <div className="h-full rounded-full" style={{ width: `${sim * 100}%`, background: 'linear-gradient(90deg,#4f8ef7,#a78bfa)' }} />
                      </div>
                      <span className="text-xs text-white/40 w-10 text-right">{sim.toFixed(3)}</span>
                    </div>
                  )
                })}
              </Card>
            )}

            {/* Connectivity map — shown when connectivity data available */}
            {(graphContext.connectivity as Record<string, unknown> | undefined) && (() => {
              const c = graphContext.connectivity as Record<string, unknown>
              const down = ((c.downstream_nodes as Record<string, unknown>[]) ?? []).filter(n => n.asset_id)
              const up   = ((c.upstream_nodes   as Record<string, unknown>[]) ?? []).filter(n => n.asset_id)
              if (!down.length && !up.length) return null
              return (
                <Card>
                  <SectionLabel>Process Connectivity</SectionLabel>
                  {up.length > 0 && (
                    <div className="mb-2">
                      <div className="text-[10px] text-white/40 mb-1">↑ Upstream (feeds in)</div>
                      {up.slice(0, 4).map((n, i) => (
                        <div key={i} className="flex items-center gap-2 text-[11px] py-0.5">
                          <span className="font-mono text-purple-400 w-14">{String(n.asset_id)}</span>
                          <span className="text-white/50 flex-1 truncate">{String(n.name)}</span>
                          <span className="text-white/25 text-[10px]">{String(n.rel_type)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                  {down.length > 0 && (
                    <div>
                      <div className="text-[10px] text-white/40 mb-1">↓ Downstream (feeds out)</div>
                      {down.slice(0, 4).map((n, i) => (
                        <div key={i} className="flex items-center gap-2 text-[11px] py-0.5">
                          <span className="font-mono text-emerald-400 w-14">{String(n.asset_id)}</span>
                          <span className="text-white/50 flex-1 truncate">{String(n.name)}</span>
                          <span className="text-white/25 text-[10px]">{String(n.rel_type)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              )
            })()}

          </>
        ) : (
          <div className="moc-glass-card rounded-2xl border-dashed border-[#4f8ef7]/25 p-8 text-center">
            <div className="text-3xl mb-3">🕸️</div>
            <div className="text-sm font-semibold text-white/50">Knowledge Graph</div>
            <div className="text-xs text-white/30 mt-2 leading-relaxed">
              Send a message and the graph will show retrieved nodes, relationships, and process connectivity.
            </div>
            <div className="mt-4 space-y-1.5 text-left">
              {[
                '🔗 Process connectivity map',
                '📡 Downtime propagation',
                '🤖 Agent tool call log',
                '📊 Vector similarity scores',
              ].map(f => (
                <div key={f} className="text-[11px] text-white/30 flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full bg-[#4f8ef7]/40" />
                  {f}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
