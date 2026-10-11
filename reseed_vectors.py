"""Reseed ChromaDB with enriched MoC embedding text. Run: python reseed_vectors.py"""
import warnings, logging
warnings.filterwarnings("ignore")
logging.getLogger("neo4j").setLevel(logging.CRITICAL)

from core.vector_store import VectorStore
from core.neo4j_client import Neo4jClient

store = VectorStore()
store.reset()
print("Vector store reset.")

neo4j = Neo4jClient()
raw = neo4j.get_all_mocs_for_training()
print(f"Found {len(raw)} MoCs in Neo4j.")

mocs = []
for r in raw:
    # Use asset_pid_ref as fallback for pid_ref
    pid = r.get("pid_ref") or r.get("asset_pid_ref", "")

    mocs.append({
        # Core identity
        "moc_id":             r.get("moc_id", ""),
        "title":              r.get("title", ""),
        "change_type":        r.get("change_type", ""),
        "asset_id":           r.get("asset_id", ""),
        "asset_name":         r.get("asset_name", ""),
        "asset_category":     r.get("asset_category", ""),   # equipment_type from Neo4j
        "description":        r.get("description", ""),
        # Risk
        "risk_level":         r.get("risk_level", ""),
        "overall_risk_score": r.get("overall_risk_score", ""),
        "hazop_required":     r.get("hazop_required", False),
        "pssr_required":      r.get("pssr_required", False),
        # Hazard
        "hazard_description": r.get("hazard_text") or r.get("hazard_description", ""),
        # Parameter change (from MoC properties)
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
        # P&ID reference (from Asset.pid_reference or PIDDocument)
        "pid_ref":            pid,
        "pid_reference":      pid,
        # Area
        "area":               r.get("area", ""),
    })

store.add_mocs(mocs)
print(f"Vector store now has {store.count()} records.")

# Print sample embedding text for verification
print("\n--- Sample embedding texts ---")
from core.vector_store import _moc_to_text
for m in mocs[:3]:
    print(f"\n{m['moc_id']}:")
    print(_moc_to_text(m)[:300])
    print("...")

neo4j.close()
