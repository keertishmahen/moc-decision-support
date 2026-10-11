import React, { useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const NODE_COLORS: Record<string, string> = {
  MoC: '#4f8ef7', Asset: '#34d399', Hazard: '#f87171',
  WorkOrder: '#fbbf24', Personnel: '#a78bfa', RiskAssessment: '#fb923c',
  LessonsLearned: '#38bdf8', HAZOP: '#e879f9', PSSR: '#4ade80',
  Query: '#94a3b8', default: '#64748b',
}

interface GraphNode { id: string; label: string; type: string; detail: string }
interface GraphLink { source: string; target: string; label: string }

function expandMocDetail(
  d: Record<string, unknown>,
  addNode: (id: string, label: string, type: string, detail?: string) => void,
  addLink: (s: string, t: string, label: string) => void,
) {
  const mid = String(d.moc_id ?? '')
  if (!mid) return
  addNode(mid, mid, 'MoC',
    `${String(d.title ?? '').slice(0, 40)}\nRisk: ${d.risk_category} (${d.risk_score})\n$${Number(d.actual_cost ?? 0).toLocaleString()}`)
  addLink('QUERY', mid, 'RETRIEVES')

  const aid = String(d.asset_id ?? '')
  if (aid && aid !== 'None' && aid !== 'none') {
    addNode(aid, aid, 'Asset', String(d.asset_name ?? ''))
    addLink(mid, aid, 'TARGETS')
  }

  const approver = String(d.final_approver_role ?? '')
  if (approver) {
    addNode(`${mid}_P_${approver}`, approver, 'Personnel', 'Approver')
    addLink(mid, `${mid}_P_${approver}`, 'APPROVED_BY')
  }

  const hazards = (d.hazards as string[] | undefined) ?? []
  hazards.slice(0, 3).forEach((hz, i) => {
    const hid = `${mid}_HZ_${i}`
    addNode(hid, `Hazard ${i + 1}`, 'Hazard', String(hz).slice(0, 50))
    addLink(mid, hid, 'IDENTIFIES')
  })
  if (d.hazop_outcome) {
    addNode(`${mid}_HAZOP`, 'HAZOP', 'HAZOP', String(d.hazop_outcome).slice(0, 50))
    addLink(mid, `${mid}_HAZOP`, 'REQUIRES_HAZOP')
  }
  if (d.pssr_outcome) {
    addNode(`${mid}_PSSR`, 'PSSR', 'PSSR', String(d.pssr_outcome).slice(0, 50))
    addLink(mid, `${mid}_PSSR`, 'REQUIRES_PSSR')
  }
  if (d.lesson) {
    addNode(`${mid}_LL`, 'Lesson', 'LessonsLearned', String(d.lesson).slice(0, 60))
    addLink(mid, `${mid}_LL`, 'CAPTURED_LESSON')
  }
  if (d.risk_category || d.risk_score) {
    addNode(`${mid}_RA`, 'Risk', 'RiskAssessment', `${d.risk_category ?? ''} (${d.risk_score ?? '?'})`)
    addLink(mid, `${mid}_RA`, 'REQUIRES')
  }
}

function buildGraph(ctx: Record<string, unknown>, query: string) {
  const nodes: GraphNode[] = []
  const links: GraphLink[] = []
  const seen = new Set<string>()

  const addNode = (id: string, label: string, type: string, detail = '') => {
    if (!id || seen.has(id)) return
    seen.add(id)
    nodes.push({ id, label, type, detail })
  }
  const addLink = (s: string, t: string, label: string) => {
    if (seen.has(s) && seen.has(t)) links.push({ source: s, target: t, label })
  }

  addNode('QUERY', 'Query', 'Query', query.slice(0, 60))

  const backend = ctx.graph as { nodes?: Record<string, unknown>[]; links?: Record<string, unknown>[] } | undefined
  const backendNodes = backend?.nodes ?? []
  const backendLinks = backend?.links ?? []

  if (backendNodes.length) {
    backendNodes.forEach(n => {
      const id = String(n.id ?? '')
      if (!id) return
      addNode(id, String(n.label ?? id), String(n.type ?? 'default'), String(n.detail ?? ''))
    })
    backendLinks.forEach(lk => {
      addLink(String(lk.source ?? ''), String(lk.target ?? ''), String(lk.label ?? ''))
    })
    backendNodes
      .filter(n => String(n.type) === 'MoC')
      .forEach(n => addLink('QUERY', String(n.id), 'RETRIEVES'))
  } else {
    const details = (ctx.top_hit_details as Array<{ moc_detail?: Record<string, unknown>; work_orders?: Record<string, unknown>[] }> | undefined) ?? []
    if (details.length) {
      details.forEach(entry => {
        if (entry.moc_detail) expandMocDetail(entry.moc_detail, addNode, addLink)
        const mid = String(entry.moc_detail?.moc_id ?? '')
        ;(entry.work_orders ?? []).slice(0, 3).forEach(wo => {
          const wid = String(wo.wo_id ?? '')
          if (!wid) return
          addNode(wid, wid, 'WorkOrder', `${String(wo.title ?? '').slice(0, 35)}\n${wo.actual_hrs}h | $${Number(wo.actual_cost ?? 0).toLocaleString()}`)
          if (mid) addLink(mid, wid, 'GENERATES')
        })
      })
    } else if (ctx.moc_detail) {
      expandMocDetail(ctx.moc_detail as Record<string, unknown>, addNode, addLink)
      const d = ctx.moc_detail as Record<string, unknown>
      const wos = (ctx.work_orders as Record<string, unknown>[] | undefined) ?? []
      wos.slice(0, 3).forEach(wo => {
        const wid = String(wo.wo_id ?? '')
        if (!wid) return
        addNode(wid, wid, 'WorkOrder', `${String(wo.title ?? '').slice(0, 35)}\n${wo.actual_hrs}h | $${Number(wo.actual_cost ?? 0).toLocaleString()}`)
        addLink(String(d.moc_id ?? ''), wid, 'GENERATES')
      })
    }
  }

  const chain = (ctx.impact_chain as Record<string, unknown>[] | undefined) ?? []
  const originAsset = String((ctx.moc_detail as Record<string, unknown> | undefined)?.asset_id ?? '')
  chain.slice(0, 5).forEach(n => {
    const nid = String(n.node_id ?? '')
    if (!nid) return
    addNode(nid, nid, 'Asset', `${n.node_name} (${n.hop_distance} hop)`)
    if (originAsset && seen.has(originAsset)) addLink(originAsset, nid, 'IMPACTS')
  })

  const hits = (ctx.vector_hits as Record<string, unknown>[] | undefined) ?? []
  hits.slice(0, 3).forEach(h => {
    const vid = String(h.moc_id ?? '')
    if (!vid) return
    if (!seen.has(vid)) {
      addNode(vid, vid, 'MoC', `sim=${Number(h.similarity ?? 0).toFixed(2)}`)
      addLink('QUERY', vid, 'SIMILAR')
    }
  })

  return { nodes, links }
}

export default function KnowledgeGraph({ context, query }: { context: Record<string, unknown>; query: string }) {
  const { nodes, links } = useMemo(() => buildGraph(context, query), [context, query])

  const legendTypes = useMemo(() => {
    const present = new Set(nodes.map(n => n.type))
    return Object.entries(NODE_COLORS).filter(([k]) => k !== 'default' && present.has(k))
  }, [nodes])

  const nodeCanvasObject = useCallback((node: unknown, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const n = node as GraphNode & { x: number; y: number }
    const color = NODE_COLORS[n.type] ?? NODE_COLORS.default
    const r = n.type === 'Query' ? 10 : n.type === 'MoC' ? 8 : 6
    ctx.beginPath()
    ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = color + '33'
    ctx.fill()
    ctx.strokeStyle = color
    ctx.lineWidth = 1.5
    ctx.stroke()
    const label = n.label
    const fontSize = Math.max(10 / globalScale, 8)
    ctx.font = `${fontSize}px Inter`
    ctx.fillStyle = '#e8eeff'
    ctx.textAlign = 'center'
    ctx.fillText(label, n.x, n.y + r + fontSize + 1)
  }, [])

  if (nodes.length === 0) return null

  return (
    <div className="graph-canvas rounded-xl overflow-hidden border border-white/10 bg-[#080c14]">
      <ForceGraph2D
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        graphData={{ nodes: nodes as any[], links: links as any[] }}
        nodeId="id"
        linkSource="source"
        linkTarget="target"
        nodeCanvasObject={nodeCanvasObject}
        nodeCanvasObjectMode={() => 'replace'}
        linkColor={() => 'rgba(79,142,247,0.3)'}
        linkWidth={1}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        backgroundColor="transparent"
        width={520}
        height={420}
        cooldownTicks={80}
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        nodeLabel={(n: any) => {
          const node = n as GraphNode
          return `<div style="background:#0d1220;border:1px solid rgba(79,142,247,0.3);border-radius:8px;padding:6px 10px;font-size:11px;color:#e8eeff;max-width:200px">
            <b>${node.label}</b><br/><i style="color:#94a3b8">${node.type}</i><br/>${node.detail.replace(/\n/g,'<br/>')}
          </div>`
        }}
      />
      <div className="flex flex-wrap gap-x-3 gap-y-1 px-3 pb-2 pt-1">
        {legendTypes.map(([type, color]) => (
          <span key={type} className="flex items-center gap-1 text-[10px] text-white/40">
            <span className="w-2 h-2 rounded-full inline-block" style={{ background: color }} />
            {type}
          </span>
        ))}
      </div>
    </div>
  )
}
