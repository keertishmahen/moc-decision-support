"""
core/rag_pipeline.py
Hybrid RAG: ChromaDB vector search + Neo4j graph traversal → LLM.
Uses OpenAI SDK directly (no langchain) to avoid import-time hangs.
"""

from core.config import (
    OPENAI_API_KEY, OPENAI_MODEL, TOP_K_SIMILAR
)
from core.vector_store import VectorStore
from core.neo4j_client import Neo4jClient


def get_llm():
    """Return a simple callable wrapper around the OpenAI chat completions API."""
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    class _LLM:
        def invoke(self, messages: list) -> str:
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                temperature=0.1,
            )
            return resp.choices[0].message.content

    return _LLM()


def _build_messages(system: str, history: str, human_input: str) -> list:
    """Build OpenAI messages list from system prompt, history, and user input."""
    messages = [{"role": "system", "content": system}]
    if history:
        for line in history.strip().split("\n"):
            if line.startswith("User: "):
                messages.append({"role": "user", "content": line[6:]})
            elif line.startswith("MoCBot: "):
                messages.append({"role": "assistant", "content": line[8:]})
    messages.append({"role": "user", "content": human_input})
    return messages


class HybridRetriever:
    def __init__(self):
        self.vector_store = VectorStore()
        self.neo4j = Neo4jClient()

    def retrieve(self, query_text: str, asset_id: str = None,
                 change_type: str = None, moc_id: str = None,
                 top_k: int = TOP_K_SIMILAR) -> dict:
        context = {
            "vector_hits": [], "impact_chain": [], "hazards": [],
            "similar_mocs": [], "lessons": [], "incidents": [],
            "risk_assessment": [], "work_orders": [], "parameters": [],
            "connectivity": None, "enriched_chain": [], "propagation": None,
        }

        # Vector similarity — always run, gives semantically relevant MoCs
        if query_text:
            context["vector_hits"] = self.vector_store.search(query_text, top_k=top_k)

        # Direct MoC lookup
        if moc_id:
            detail = self.neo4j.get_moc_full_detail(moc_id)
            if detail:
                context["moc_detail"] = detail
            context["work_orders"] = self.neo4j.get_work_orders_for_moc(moc_id)
            context["parameters"]  = self.neo4j.get_parameter_changes(moc_id)

        # Collect MoC IDs from the explicit param and top-3 vector hits
        moc_ids = []
        if moc_id:
            moc_ids.append(moc_id)
        for hit in context["vector_hits"][:3]:
            hit_id = hit.get("moc_id")
            if hit_id and hit_id not in moc_ids:
                moc_ids.append(hit_id)

        # Enrich every retrieved MoC (skip the one already loaded above)
        top_hit_details = []
        if moc_id and context.get("moc_detail"):
            top_hit_details.append({
                "moc_detail": context["moc_detail"],
                "work_orders": context.get("work_orders") or [],
            })
        for hit_id in moc_ids:
            if moc_id and hit_id == moc_id:
                continue
            detail = self.neo4j.get_moc_full_detail(hit_id)
            if detail:
                top_hit_details.append({
                    "moc_detail": detail,
                    "work_orders": self.neo4j.get_work_orders_for_moc(hit_id),
                })
        context["top_hit_details"] = top_hit_details
        if not context.get("moc_detail") and top_hit_details:
            context["moc_detail"] = top_hit_details[0]["moc_detail"]
            context["work_orders"] = top_hit_details[0]["work_orders"]

        resolved_asset = asset_id
        if not resolved_asset and context.get("moc_detail"):
            resolved_asset = context["moc_detail"].get("asset_id") or None
            if resolved_asset in ("", "none", "None"):
                resolved_asset = None

        # Asset-based graph retrieval — use enriched chain for all relationship types
        if resolved_asset:
            # Use enriched chain (covers FEEDS, CONNECTS, CIRCULATES_TO, etc.)
            enriched = self.neo4j.get_enriched_impact_chain(resolved_asset, depth=4) or []
            context["enriched_chain"] = enriched
            # Keep legacy impact_chain for backward compat (format_context uses it)
            context["impact_chain"] = [
                {
                    "node_id":      n.get("node_id"),
                    "node_name":    n.get("node_name"),
                    "node_type":    n.get("node_type"),
                    "hop_distance": n.get("hop_distance"),
                }
                for n in enriched
            ]
            context["hazards"]   = self.neo4j.get_hazards_for_asset(resolved_asset)
            context["incidents"] = self.neo4j.get_historical_incidents(resolved_asset)
            # Full connectivity map (upstream + downstream with rel types)
            context["connectivity"] = self.neo4j.get_full_connectivity_map(resolved_asset)

        if resolved_asset and change_type:
            context["similar_mocs"] = self.neo4j.get_similar_mocs(change_type, resolved_asset, top_k)
            context["lessons"]      = self.neo4j.get_lessons_learned(change_type, resolved_asset)

        try:
            context["graph"] = self.neo4j.get_retrieved_subgraph(
                moc_ids, asset_id=resolved_asset
            )
        except Exception:
            context["graph"] = {"nodes": [], "links": []}

        return context

    def format_context_for_prompt(self, context: dict) -> str:
        sections = []

        # Direct MoC detail — most specific, always first
        if context.get("moc_detail"):
            d = context["moc_detail"]
            lines = [
                f"MoC ID: {d.get('moc_id')} | Title: {d.get('title')}",
                f"Change Type: {d.get('change_type')} | Asset: {d.get('asset_name')} ({d.get('asset_id')})",
                f"Description: {d.get('description')}",
                f"Risk: {d.get('risk_category')} (score {d.get('risk_score')}) | Approver: {d.get('final_approver_role')}",
                f"Cost: ${d.get('actual_cost') or 0:,} | Manhours: {d.get('actual_manhours')}",
                f"HAZOP: {d.get('hazop_required')} | PSSR: {d.get('pssr_required')}",
            ]
            if d.get("hazards"):
                lines.append(f"Hazards: {'; '.join(str(h) for h in d['hazards'][:3])}")
            if d.get("incident_occurred"):
                lines.append(f"Incident: {d.get('incident_description')} → {d.get('incident_outcome')}")
            if d.get("lesson"):
                lines.append(f"Lesson: {d.get('lesson')}")
            if d.get("recommendation"):
                lines.append(f"Recommendation: {d.get('recommendation')}")
            if d.get("param_name"):
                lines.append(f"Parameter changed: {d.get('param_name')} from {d.get('param_old')} to {d.get('param_new')} {d.get('param_unit','')} (threshold: {d.get('param_threshold')})")
            if d.get("hazop_outcome"):
                lines.append(f"HAZOP outcome: {d.get('hazop_outcome')}")
            if d.get("pssr_outcome"):
                lines.append(f"PSSR outcome: {d.get('pssr_outcome')}")
            sections.append("DIRECT MoC RECORD:\n" + "\n".join(f"  {l}" for l in lines))

        # Additional top-hit details (hits 2 and 3) for multi-MoC queries
        for extra in context.get("top_hit_details", [])[1:]:
            d = extra.get("moc_detail")
            if not d:
                continue
            lines = [
                f"MoC ID: {d.get('moc_id')} | Title: {d.get('title')}",
                f"Change Type: {d.get('change_type')} | Asset: {d.get('asset_name')} ({d.get('asset_id')})",
                f"Description: {d.get('description')}",
                f"Risk: {d.get('risk_category')} (score {d.get('risk_score')}) | Approver: {d.get('final_approver_role')}",
                f"Cost: ${d.get('actual_cost') or 0:,} | Manhours: {d.get('actual_manhours')}",
                f"HAZOP: {d.get('hazop_required')} | PSSR: {d.get('pssr_required')}",
            ]
            if d.get("hazards"):
                lines.append(f"Hazards: {'; '.join(str(h) for h in d['hazards'][:3])}")
            if d.get("incident_occurred"):
                lines.append(f"Incident: {d.get('incident_description')} → {d.get('incident_outcome')}")
            if d.get("lesson"):
                lines.append(f"Lesson: {d.get('lesson')}")
            if d.get("param_name"):
                lines.append(f"Parameter changed: {d.get('param_name')} from {d.get('param_old')} to {d.get('param_new')} (threshold: {d.get('param_threshold')})")
            sections.append("DIRECT MoC RECORD:\n" + "\n".join(f"  {l}" for l in lines))

        # Work orders
        if context.get("work_orders"):
            wo_lines = []
            for wo in context["work_orders"][:4]:
                wo_lines.append(
                    f"  {wo.get('wo_id')}: {wo.get('title')} | "
                    f"{wo.get('actual_hrs')}h actual | ${wo.get('actual_cost') or 0:,} | "
                    f"Delay: {wo.get('delay_reason','none')}"
                )
            sections.append("WORK ORDERS:\n" + "\n".join(wo_lines))

        # Parameter changes
        if context.get("parameters"):
            for p in context["parameters"][:2]:
                sections.append(
                    f"PARAMETER CHANGE: {p.get('name')} "
                    f"{p.get('old_value')} → {p.get('new_value')} {p.get('unit','')} "
                    f"(threshold: {p.get('threshold')}, margin: {p.get('margin')})"
                )

        # Vector hits — semantically similar MoCs
        if context.get("vector_hits"):
            hits_text = "\n".join(
                f"  [{i+1}] sim={h['similarity']:.2f} | {h['moc_id']}: {h['text'][:180]}"
                for i, h in enumerate(context["vector_hits"][:3])
            )
            sections.append(f"SEMANTICALLY SIMILAR MoCs:\n{hits_text}")

        # Graph impact chain — enriched version with relationship types
        if context.get("enriched_chain"):
            chain = context["enriched_chain"]
            direct   = [n for n in chain if n.get("hop_distance") == 1]
            indirect = [n for n in chain if (n.get("hop_distance") or 0) > 1]

            def _rank(n):
                crit = int(n.get("criticality") or 1)
                hops = int(n.get("hop_distance") or 1)
                return crit / hops

            direct_sorted   = sorted(direct,   key=_rank, reverse=True)
            indirect_sorted = sorted(indirect, key=_rank, reverse=True)

            chain_lines = []
            if direct_sorted:
                chain_lines.append("  DIRECT (1 hop, ranked by criticality):")
                for n in direct_sorted[:8]:
                    rel = " → ".join(n.get("relationship_chain") or [])
                    chain_lines.append(
                        f"    ↳ {n['node_id']} ({n['node_name']}) | "
                        f"crit={n.get('criticality')} | via: {rel} | "
                        f"area={n.get('area') or 'n/a'}"
                    )
            if indirect_sorted:
                chain_lines.append("  INDIRECT (2+ hops):")
                for n in indirect_sorted[:6]:
                    rel = " → ".join(n.get("relationship_chain") or [])
                    chain_lines.append(
                        f"    ↳↳ {n['node_id']} ({n['node_name']}) | "
                        f"crit={n.get('criticality')} | {n.get('hop_distance')} hops | via: {rel}"
                    )
            if chain_lines:
                sections.append("ENRICHED ASSET IMPACT CHAIN:\n" + "\n".join(chain_lines))

        elif context.get("impact_chain"):
            # Fallback to legacy format
            chain = context["impact_chain"]
            direct   = [n for n in chain if n.get("hop_distance") == 1]
            indirect = [n for n in chain if n.get("hop_distance", 0) > 1]
            chain_text = ""
            if direct:
                chain_text += "  Direct: " + ", ".join(
                    f"{n['node_name']} ({n['node_id']})" for n in direct[:6]) + "\n"
            if indirect:
                chain_text += "  Indirect: " + ", ".join(
                    f"{n['node_name']} ({n['hop_distance']}h)" for n in indirect[:6])
            sections.append(f"ASSET IMPACT CHAIN:\n{chain_text}")

        # Full connectivity map (upstream + downstream)
        if context.get("connectivity"):
            conn = context["connectivity"]
            downstream = [n for n in (conn.get("downstream_nodes") or []) if n and n.get("asset_id")]
            upstream   = [n for n in (conn.get("upstream_nodes") or []) if n and n.get("asset_id")]
            conn_lines = []
            if upstream:
                conn_lines.append("  UPSTREAM (feeds into this asset):")
                for n in sorted(upstream, key=lambda x: -(x.get("criticality") or 0)):
                    conn_lines.append(
                        f"    ↑ {n['asset_id']} ({n['name']}) | "
                        f"rel={n.get('rel_type')} | flow={n.get('flow_type') or 'n/a'} | "
                        f"crit={n.get('criticality')}"
                    )
            if downstream:
                conn_lines.append("  DOWNSTREAM (this asset feeds into):")
                for n in sorted(downstream, key=lambda x: -(x.get("criticality") or 0)):
                    conn_lines.append(
                        f"    ↳ {n['asset_id']} ({n['name']}) | "
                        f"rel={n.get('rel_type')} | flow={n.get('flow_type') or 'n/a'} | "
                        f"crit={n.get('criticality')}"
                    )
            if conn_lines:
                sections.append(
                    f"PROCESS CONNECTIVITY MAP ({conn.get('asset_id')}):\n"
                    + "\n".join(conn_lines)
                )

        # Hazards with failure modes
        if context.get("hazards"):
            haz_lines = []
            for h in context["hazards"][:4]:
                fm = ", ".join(h.get("failure_modes", [])[:2]) if h.get("failure_modes") else ""
                haz_lines.append(
                    f"  [{h.get('severity','?')} score={h.get('risk_score','?')}] "
                    f"{h.get('description','')} "
                    + (f"| Failure modes: {fm}" if fm else "")
                )
            sections.append("HAZARDS:\n" + "\n".join(haz_lines))

        # Historical incidents
        if context.get("incidents"):
            inc_lines = [
                f"  {i.get('moc_id')}: {i.get('description')} → {i.get('outcome')}"
                for i in context["incidents"][:3]
            ]
            sections.append("HISTORICAL INCIDENTS:\n" + "\n".join(inc_lines))

        # Lessons learned
        if context.get("lessons"):
            ll_lines = []
            for ll in context["lessons"][:3]:
                ll_lines.append(f"  - {ll.get('summary','')}")
                if ll.get("recommendation"):
                    ll_lines.append(f"    Recommendation: {ll.get('recommendation')}")
            sections.append("LESSONS LEARNED:\n" + "\n".join(ll_lines))

        # Similar MoCs from graph
        if context.get("similar_mocs"):
            sm_lines = [
                f"  {m.get('moc_id')}: {m.get('title')} | "
                f"Cost: ${m.get('cost') or 0:,} | Risk: {m.get('risk_level')} | "
                f"Outcome: {m.get('outcome','?')}"
                for m in context["similar_mocs"][:3]
            ]
            sections.append("SIMILAR HISTORICAL MoCs (graph):\n" + "\n".join(sm_lines))

        return "\n\n".join(sections) if sections else "No relevant context found in knowledge base."


class RAGPipeline:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.llm       = get_llm()

    def run(self, query: str, prompt_template: str, asset_id: str = None,
            change_type: str = None, moc_id: str = None,
            extra_vars: dict = None) -> str:
        context   = self.retriever.retrieve(query, asset_id, change_type, moc_id)
        formatted = self.retriever.format_context_for_prompt(context)
        # Simple template substitution replacing {context}, {query}, etc.
        variables = {
            "context":     formatted,
            "query":       query,
            "change_type": change_type or "unknown",
            "asset_id":    asset_id or "unknown",
        }
        if extra_vars:
            variables.update(extra_vars)
        filled = prompt_template
        for k, v in variables.items():
            filled = filled.replace("{" + k + "}", str(v))
        messages = [{"role": "user", "content": filled}]
        return self.llm.invoke(messages)

    def get_raw_context(self, query: str, asset_id: str = None,
                        change_type: str = None, moc_id: str = None):
        return self.retriever.retrieve(query, asset_id, change_type, moc_id)
