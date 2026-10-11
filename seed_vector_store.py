"""
seed_vector_store.py
Seeds ChromaDB from Neo4j MoC data.
Run: python seed_vector_store.py
"""
from core.neo4j_client import Neo4jClient
from core.vector_store import VectorStore


def seed():
    neo4j = Neo4jClient()
    store = VectorStore()
    
    # Fetch data BEFORE reset — preserve existing collection if Neo4j fails
    try:
        raw = neo4j.get_all_mocs_for_training()
    except Exception as e:
        raise RuntimeError(f"Neo4j connection failed before seeding: {e}") from e
    
    print(f"Found {len(raw)} MoCs in Neo4j.")
    
    # Only reset after successful data fetch
    store.reset()
    print(f"Vector store reset. Building enriched embeddings...")
    
    mocs = []
    for r in raw:
        pid = r.get("pid_ref") or r.get("asset_pid_ref", "")
        
        # Enrichment field summary for logging
        n_stages = len([s for s in (r.get("approval_stages") or []) if s.get("stage_name")])
        n_fms = len([f for f in (r.get("failure_modes") or []) if f.get("mode")])
        n_wos = len([w for w in (r.get("work_orders") or []) if w.get("wo_id")])
        n_roles = len([x for x in (r.get("approver_roles") or []) if x])
        print(f"  {r.get('moc_id')}: stages={n_stages} failure_modes={n_fms} work_orders={n_wos} approvers={n_roles}")
        
        mocs.append({
            # Core identity
            "moc_id":             r.get("moc_id", ""),
            "title":              r.get("title", ""),
            "change_type":        r.get("change_type", ""),
            "asset_id":           r.get("asset_id", ""),
            "asset_name":         r.get("asset_name", ""),
            "asset_category":     r.get("asset_category", ""),
            "description":        r.get("description", ""),
            # Risk
            "risk_level":         r.get("risk_level", ""),
            "overall_risk_score": r.get("overall_risk_score", ""),
            "hazop_required":     r.get("hazop_required", False),
            "pssr_required":      r.get("pssr_required", False),
            # Hazard
            "hazard_description": r.get("hazard_text") or r.get("hazard_description", ""),
            # Parameter change
            "parameter_name":     r.get("parameter_name", ""),
            "old_value":          r.get("old_value", ""),
            "new_value":          r.get("new_value", ""),
            "threshold_limit":    r.get("threshold_limit", ""),
            # Outcomes
            "lessons_learned":    (r.get("lesson_detail") or r.get("lessons_learned", ""))[:400],
            "incident_occurred":  r.get("incident_occurred", False),
            "rework_required":    r.get("rework_required", False),
            # Cost / time
            "actual_cost":        r.get("cost", 0),
            "actual_downtime":    r.get("downtime", 0),
            # P&ID reference
            "pid_ref":            pid,
            "pid_reference":      pid,
            # Area
            "area":               r.get("area", ""),
            # ── NEW enriched fields ────────────────────────────────────────
            "approval_stages":      r.get("approval_stages", []),
            "failure_modes":        r.get("failure_modes", []),
            "work_orders":          r.get("work_orders", []),
            "approver_roles":       r.get("approver_roles", []),
            "approver_departments": r.get("approver_departments", []),
        })
    
    added = store.add_mocs(mocs)
    print(f"Vector store now has {store.count()} records ({added} added).")
    neo4j.close()
    return added


if __name__ == "__main__":
    seed()
