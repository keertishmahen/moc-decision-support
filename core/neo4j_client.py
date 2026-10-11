"""
core/neo4j_client.py
Neo4j driver aligned to the ACTUAL graph schema (verified 2026-05-05).

Real property names:
  MoC:            moc_id, name, title, description, change_type, date_initiated,
                  actual_cost, estimated_cost, actual_manhours, estimated_manhours,
                  hazop_required, hazop_reason, pssr_required, final_approver_role,
                  incident_occurred, lessons_learned, old_value, new_value,
                  parameter_name, criticality_rating, shutdown_required,
                  action_type, approval_date
  Asset:          asset_id, name, equipment_type, criticality
  WorkOrder:      wo_id, name, title, work_type, priority, status,
                  actual_duration, planned_duration, actual_cost, estimated_cost,
                  delay_reason, failure_mode, equipment_status, date_issued
  Hazard:         hazard_id, name, description, category, source
  RiskAssessment: risk_id, name, risk_category, overall_score, likelihood,
                  risk_people, risk_asset, risk_community, risk_environment,
                  assessor_role, assessment_date
  LessonsLearned: ll_id, name, text          ← 'text' not 'lesson'
  Personnel:      person_id, role, department
  Incident:       incident_id, name, description, outcome
  HAZOP:          hazop_id, name, required, reason
  PSSR:           pssr_id, name, required, reason
  Parameter:      param_id, name, parameter_name, old_value, new_value, threshold

Real relationships (verified from live DB):
  TARGETS, BELONGS_TO, PART_OF, UPSTREAM_OF, DEPENDS_ON,
  IMPACTS, CONTROLS_FLOW_TO, FEEDS, CONNECTS, SHUTS_DOWN,
  IDENTIFIES, REQUIRES, EVALUATES, SCORED_AS, APPROVED_BY,
  GENERATES, EXECUTED_ON, PERFORMED_BY, RESULTS_IN,
  RELATED_TO, GENERATED_LESSON,          ← replaces CAPTURED_LESSON
  REQUIRES_HAZOP, REQUIRES_PSSR,
  CHANGES_PARAMETER, HAS_PARAMETER,      ← replaces MODIFIES_PARAMETER
  MANIFESTS_AS, INCLUDES_ACTIVITY,
  REFERENCES_PID, LOCATED_IN
"""

import threading

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

from core.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE

_driver = None
_driver_lock = threading.Lock()

_TRANSIENT_MARKERS = (
    "defunct",
    "routing information",
    "connection reset",
    "connection refused",
    "broken pipe",
    "timed out",
    "failed to read",
)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (ServiceUnavailable, SessionExpired, TransientError, OSError)):
        return True
    msg = str(exc).lower()
    return any(marker in msg for marker in _TRANSIENT_MARKERS)


def _create_driver():
    # neo4j+s:// forbids custom ssl_context. On Windows, self-signed MITM/proxy
    # chains often break verification — fall back to neo4j+ssc when needed.
    uri = NEO4J_URI
    kwargs = {
        "auth": (NEO4J_USER, NEO4J_PASSWORD),
        "max_connection_lifetime": 300,
        "keep_alive": True,
        "connection_acquisition_timeout": 30,
    }
    return GraphDatabase.driver(uri, **kwargs)


def _create_driver_ssc():
    uri = NEO4J_URI
    if uri.startswith("neo4j+s://"):
        uri = "neo4j+ssc://" + uri[len("neo4j+s://") :]
    elif uri.startswith("bolt+s://"):
        uri = "bolt+ssc://" + uri[len("bolt+s://") :]
    return GraphDatabase.driver(
        uri,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
        max_connection_lifetime=300,
        keep_alive=True,
        connection_acquisition_timeout=30,
    )


def _get_shared_driver():
    global _driver
    if _driver is not None:
        return _driver
    with _driver_lock:
        if _driver is None:
            try:
                _driver = _create_driver()
                _driver.verify_connectivity()
            except Exception:
                try:
                    if _driver is not None:
                        _driver.close()
                except Exception:
                    pass
                _driver = _create_driver_ssc()
                _driver.verify_connectivity()
        return _driver


def _reset_shared_driver():
    global _driver
    with _driver_lock:
        if _driver is not None:
            try:
                _driver.close()
            except Exception:
                pass
            _driver = None


def _session_kwargs() -> dict:
    db = (NEO4J_DATABASE or "").strip()
    # Aura Free uses the server default; explicit database="neo4j" often fails routing.
    if db and db.lower() != "neo4j":
        return {"database": db}
    return {}


def verify_neo4j_connectivity() -> None:
    """Health-check helper using the same shared driver path as chat."""
    driver = _get_shared_driver()
    driver.verify_connectivity()
    with driver.session(**_session_kwargs()) as session:
        session.run("RETURN 1").consume()


class Neo4jClient:
    def __init__(self):
        self.driver = _get_shared_driver()

    def close(self):
        # Shared driver lifecycle is process-wide; callers must not close it.
        pass

    def _run(self, query: str, params: dict = None):
        last_exc = None
        for attempt in range(2):
            try:
                with self.driver.session(**_session_kwargs()) as session:
                    result = session.run(query, params or {})
                    return [dict(r) for r in result]
            except Exception as exc:
                last_exc = exc
                if attempt == 0 and _is_transient(exc):
                    _reset_shared_driver()
                    self.driver = _get_shared_driver()
                    continue
                raise
        raise last_exc

    # ── Smart Forms ────────────────────────────────────────────────────────

    def get_similar_mocs(self, change_type: str, asset_id: str, top_k: int = 5):
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        WHERE m.change_type CONTAINS $change_type OR a.asset_id = $asset_id
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (ra:RiskAssessment)-[:EVALUATES]->(h)
        OPTIONAL MATCH (m)-[:RESULTS_IN]->(o:ImplementationOutcome)
        WITH m, a, ra, o, h
        ORDER BY m.date_initiated DESC
        WITH m, a,
             coalesce(ra.risk_category, 'Unknown') AS risk_level,
             m.actual_cost AS cost, m.actual_manhours AS downtime,
             m.final_approver_role AS approver_role,
             collect(DISTINCT h.description)[0] AS hazard,
             o.description AS outcome
        RETURN m.moc_id AS moc_id, m.title AS title, m.description AS description,
               m.change_type AS change_type, risk_level, cost, downtime,
               m.hazop_required AS hazop_required, m.pssr_required AS pssr_required,
               approver_role, a.asset_id AS asset_id, a.name AS asset_name,
               hazard, outcome
        LIMIT $top_k
        """
        return self._run(query, {"change_type": change_type,
                                  "asset_id": asset_id, "top_k": top_k})

    def get_common_approvers(self, change_type: str):
        query = """
        MATCH (m:MoC)-[:APPROVED_BY]->(p:Personnel)
        WHERE m.change_type CONTAINS $change_type
        RETURN p.role AS approver, p.department AS department, count(*) AS freq
        ORDER BY freq DESC LIMIT 5
        """
        return self._run(query, {"change_type": change_type})

    def get_approval_stages(self, moc_id: str):
        """ApprovalStage nodes exist but WENT_THROUGH not in new schema — return approver info."""
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:APPROVED_BY]->(p:Personnel)
        RETURN 'Final Approval' AS stage, p.role AS role, 'Completed' AS status,
               toString(m.approval_date) AS timestamp
        """
        return self._run(query, {"moc_id": moc_id})

    def get_pid_for_moc(self, moc_id: str):
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:REFERENCES_PID]->(p:PIDDocument)
        RETURN p.pid_ref AS pid_ref, p.version AS version
        """
        return self._run(query, {"moc_id": moc_id})

    def get_pid_entities_for_asset(self, asset_id: str):
        query = """
        MATCH (a:Asset {asset_id: $asset_id})
        OPTIONAL MATCH (m:MoC)-[:TARGETS]->(a)
        OPTIONAL MATCH (m)-[:REFERENCES_PID]->(p:PIDDocument)
        RETURN a.asset_id AS asset_id, a.name AS asset_name,
               collect(DISTINCT p.pid_ref) AS pid_refs
        """
        return self._run(query, {"asset_id": asset_id})

    # ── Risk Engine ────────────────────────────────────────────────────────

    def get_impact_chain(self, asset_id: str, depth: int = 3):
        query = """
        MATCH path = (a:Asset {asset_id: $asset_id})
                     -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO*1..3]->
                     (b:Asset)
        RETURN DISTINCT b.asset_id AS node_id, b.name AS node_name,
               b.equipment_type AS node_type, length(path) AS hop_distance
        ORDER BY hop_distance
        """
        return self._run(query, {"asset_id": asset_id})

    def get_hazards_for_asset(self, asset_id: str):
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset {asset_id: $asset_id})
        MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (h)-[:MANIFESTS_AS]->(fm:FailureMode)
        OPTIONAL MATCH (ra:RiskAssessment)-[:EVALUATES]->(h)
        RETURN h.hazard_id AS hazard_id, h.description AS description,
               h.category AS category, h.source AS source,
               ra.risk_category AS severity, ra.overall_score AS risk_score,
               collect(DISTINCT fm.mode) AS failure_modes
        """
        return self._run(query, {"asset_id": asset_id})

    def get_historical_incidents(self, asset_id: str):
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset {asset_id: $asset_id})
        MATCH (i:Incident)-[:RELATED_TO]->(m)
        RETURN i.incident_id AS incident_id, i.description AS description,
               i.outcome AS outcome, m.moc_id AS moc_id, m.title AS moc_title,
               m.lessons_learned AS lessons
        ORDER BY m.date_initiated DESC LIMIT 5
        """
        return self._run(query, {"asset_id": asset_id})

    def get_risk_assessment(self, moc_id: str):
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:REQUIRES]->(ra:RiskAssessment)
        OPTIONAL MATCH (ra)-[:SCORED_AS]->(rs:RiskScore)
        RETURN ra.risk_id AS risk_id, ra.risk_category AS category,
               ra.overall_score AS score, ra.likelihood AS likelihood,
               ra.risk_people AS people, ra.risk_asset AS asset,
               ra.risk_community AS community, ra.risk_environment AS environment,
               ra.assessor_role AS assessor,
               rs.overall AS rs_overall, rs.category AS rs_category
        """
        return self._run(query, {"moc_id": moc_id})

    def get_hazop_pssr(self, moc_id: str):
        """HAZOP/PSSR nodes in new schema have: hazop_id/pssr_id, name, required, reason."""
        query = """
        MATCH (m:MoC {moc_id: $moc_id})
        OPTIONAL MATCH (m)-[:REQUIRES_HAZOP]->(h:HAZOP)
        OPTIONAL MATCH (m)-[:REQUIRES_PSSR]->(p:PSSR)
        RETURN h.hazop_id AS hazop_id,
               h.reason AS hazop_justification,
               h.required AS hazop_required_flag,
               CASE WHEN h IS NOT NULL THEN 'HAZOP required: ' + coalesce(h.reason, 'Yes') ELSE null END AS hazop_outcome,
               p.pssr_id AS pssr_id,
               p.reason AS pssr_justification,
               p.required AS pssr_required_flag,
               CASE WHEN p IS NOT NULL THEN 'PSSR required: ' + coalesce(p.reason, 'Yes') ELSE null END AS pssr_outcome,
               m.hazop_required AS hazop_required, m.pssr_required AS pssr_required,
               m.hazop_reason AS hazop_reason
        """
        return self._run(query, {"moc_id": moc_id})

    def get_shuts_down_assets(self, asset_id: str):
        query = """
        MATCH (a:Asset {asset_id: $asset_id})-[:SHUTS_DOWN]->(b:Asset)
        RETURN b.asset_id AS asset_id, b.name AS name, b.equipment_type AS type
        """
        return self._run(query, {"asset_id": asset_id})

    def get_parameter_changes(self, moc_id: str):
        """Use CHANGES_PARAMETER (new schema) — falls back to HAS_PARAMETER via asset."""
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:CHANGES_PARAMETER]->(p:Parameter)
        RETURN p.parameter_name AS name, p.old_value AS old_value,
               p.new_value AS new_value, p.threshold AS threshold,
               null AS unit, null AS margin, null AS description
        """
        return self._run(query, {"moc_id": moc_id})

    # ── Cost Predictor ─────────────────────────────────────────────────────

    def get_feature_vector(self, asset_id: str, change_type: str):
        query = """
        MATCH (a:Asset {asset_id: $asset_id})
        OPTIONAL MATCH (a)-[:UPSTREAM_OF|DEPENDS_ON|IMPACTS*1..3]->(dep:Asset)
        OPTIONAL MATCH (m:MoC)-[:TARGETS]->(a)
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (m)-[:GENERATES]->(wo:WorkOrder)
        RETURN count(DISTINCT dep) AS n_dependencies,
               count(DISTINCT h)   AS n_hazards,
               count(DISTINCT m)   AS n_mocs,
               count(DISTINCT wo)  AS n_work_orders,
               CASE WHEN any(x IN collect(DISTINCT m.shutdown_required) WHERE x = true) THEN 1 ELSE 0 END AS shutdown_required,
               CASE WHEN any(x IN collect(DISTINCT m.hazop_required) WHERE x = true) THEN 1 ELSE 0 END AS hazop_required,
               CASE WHEN any(x IN collect(DISTINCT m.pssr_required) WHERE x = true) THEN 1 ELSE 0 END AS pssr_required
        """
        result = self._run(query, {"asset_id": asset_id})
        return result[0] if result else {
            "n_dependencies": 0, "n_hazards": 0, "n_mocs": 0,
            "n_work_orders": 1, "shutdown_required": 0,
            "hazop_required": 0, "pssr_required": 1,
        }

    def get_all_mocs_for_training(self):
        """
        Fetch all MoC data for vector embedding.
        PIDDocument nodes and REFERENCES_PID relationships confirmed to exist.
        Includes aggregated ApprovalStage, FailureMode, WorkOrder, and Personnel data.
        """
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (ra:RiskAssessment)-[:EVALUATES]->(h)
        OPTIONAL MATCH (m)-[:RESULTS_IN]->(o:ImplementationOutcome)
        OPTIONAL MATCH (m)-[:GENERATED_LESSON]->(ll:LessonsLearned)
        OPTIONAL MATCH (m)-[:REFERENCES_PID]->(pid:PIDDocument)
        OPTIONAL MATCH (i:Incident)-[:RELATED_TO]->(m)
        OPTIONAL MATCH (m)-[:LOCATED_IN]->(ar:Area)
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(hz:Hazard)-[:MANIFESTS_AS]->(fm:FailureMode)
        OPTIONAL MATCH (m)-[:GENERATES]->(wo:WorkOrder)
        OPTIONAL MATCH (m)-[:APPROVED_BY]->(p:Personnel)
        WITH m, a,
             coalesce(max(ra.risk_category), 'Medium') AS risk_level,
             max(ra.overall_score) AS overall_risk_score,
             max(o.description) AS outcome_description,
             max(ll.text) AS lesson_detail,
             collect(DISTINCT h.description)[0] AS hazard_text,
             count(DISTINCT h) AS n_hazards,
             max(pid.pid_ref) AS pid_ref,
             max(i.description) AS incident_description,
             collect(DISTINCT ar.name)[0] AS area_name,
             collect(DISTINCT {mode: fm.mode, consequence: fm.consequence}) AS failure_modes,
             collect(DISTINCT {wo_id: wo.wo_id, planned_duration: wo.planned_duration, actual_duration: wo.actual_duration, estimated_cost: wo.estimated_cost, actual_cost: wo.actual_cost, delay_reason: wo.delay_reason, failure_mode: wo.failure_mode}) AS work_orders,
             collect(DISTINCT p.role) AS approver_roles,
             collect(DISTINCT p.department) AS approver_departments
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type, m.description AS description,
               a.equipment_type AS asset_category, a.asset_id AS asset_id,
               a.name AS asset_name,
               risk_level,
               overall_risk_score,
               m.actual_cost AS cost,
               m.actual_manhours AS downtime,
               m.lessons_learned AS lessons_learned,
               m.hazop_required AS hazop_required,
               m.pssr_required AS pssr_required,
               m.incident_occurred AS incident_occurred,
               m.threshold_limit AS threshold_limit,
               m.rework_required AS rework_required,
               hazard_text, lesson_detail, outcome_description, n_hazards,
               m.parameter_name AS parameter_name,
               m.old_value AS old_value,
               m.new_value AS new_value,
               coalesce(pid_ref, '') AS pid_ref,
               incident_description,
               area_name AS area,
               failure_modes,
               work_orders,
               approver_roles,
               approver_departments
        """
        return self._run(query)

    # ── NLP Chatbot ────────────────────────────────────────────────────────

    def get_moc_full_detail(self, moc_id: str):
        """Rich detail for a specific MoC — uses updated schema relationships."""
        query = """
        MATCH (m:MoC)
        WHERE m.moc_id = $moc_id OR m.id = $moc_id
        OPTIONAL MATCH (m)-[:TARGETS]->(a:Asset)
        OPTIONAL MATCH (m)-[:APPROVED_BY]->(p:Personnel)
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (m)-[:REQUIRES]->(ra:RiskAssessment)
        OPTIONAL MATCH (m)-[:RESULTS_IN]->(o:ImplementationOutcome)
        OPTIONAL MATCH (m)-[:GENERATED_LESSON]->(ll:LessonsLearned)
        OPTIONAL MATCH (i:Incident)-[:RELATED_TO]->(m)
        OPTIONAL MATCH (m)-[:REQUIRES_HAZOP]->(hazop:HAZOP)
        OPTIONAL MATCH (m)-[:REQUIRES_PSSR]->(pssr:PSSR)
        OPTIONAL MATCH (m)-[:CHANGES_PARAMETER]->(param:Parameter)
        WITH m, a, ra, o, ll, i, hazop, pssr, param,
             collect(DISTINCT p.role) AS approver_roles,
             collect(DISTINCT h.description) AS hazards
        RETURN coalesce(m.moc_id, m.id) AS moc_id, m.title AS title,
               m.description AS description, m.change_type AS change_type,
               m.date_initiated AS date_initiated,
               m.actual_cost AS actual_cost, m.estimated_cost AS estimated_cost,
               m.actual_manhours AS actual_manhours,
               m.estimated_manhours AS estimated_manhours,
               m.incident_occurred AS incident_occurred,
               m.lessons_learned AS lessons_learned,
               m.hazop_required AS hazop_required, m.pssr_required AS pssr_required,
               m.hazop_reason AS hazop_reason,
               m.final_approver_role AS final_approver_role,
               m.old_value AS old_value, m.new_value AS new_value,
               m.parameter_name AS parameter_name,
               m.criticality_rating AS criticality_rating,
               m.shutdown_required AS shutdown_required,
               coalesce(a.asset_id, a.id) AS asset_id, a.name AS asset_name,
               a.equipment_type AS equipment_type,
               approver_roles, hazards,
               ra.risk_category AS risk_category, ra.overall_score AS risk_score,
               ra.risk_people AS risk_people, ra.risk_asset AS risk_asset,
               ra.likelihood AS likelihood,
               o.result AS outcome_result, o.description AS outcome_description,
               ll.text AS lesson,
               null AS recommendation, null AS lesson_detail,
               i.description AS incident_description, i.outcome AS incident_outcome,
               CASE WHEN hazop IS NOT NULL
                    THEN coalesce(hazop.reason, 'HAZOP required') END AS hazop_outcome,
               hazop.reason AS hazop_justification,
               CASE WHEN pssr IS NOT NULL
                    THEN coalesce(pssr.reason, 'PSSR required') END AS pssr_outcome,
               param.parameter_name AS param_name,
               param.old_value AS param_old,
               param.new_value AS param_new,
               param.threshold AS param_threshold,
               null AS param_unit
        """
        result = self._run(query, {"moc_id": moc_id})
        return result[0] if result else None

    def get_moc_by_id(self, moc_id: str):
        return self.get_moc_full_detail(moc_id)

    _SUBGRAPH_REL_TYPES = (
        "TARGETS", "IDENTIFIES", "GENERATES", "APPROVED_BY", "REQUIRES",
        "REQUIRES_HAZOP", "REQUIRES_PSSR", "GENERATED_LESSON",
        "CHANGES_PARAMETER", "EXECUTED_ON",
    )
    _SUBGRAPH_LABEL_PRIORITY = (
        "MoC", "Asset", "Hazard", "WorkOrder", "Personnel", "RiskAssessment",
        "LessonsLearned", "HAZOP", "PSSR", "Parameter", "Incident",
        "ImplementationOutcome",
    )

    @staticmethod
    def _primary_label(labels) -> str:
        labels = list(labels or [])
        for preferred in Neo4jClient._SUBGRAPH_LABEL_PRIORITY:
            if preferred in labels:
                return preferred
        return labels[0] if labels else "Unknown"

    @staticmethod
    def _business_id(props: dict, labels) -> str:
        for key in (
            "moc_id", "asset_id", "wo_id", "hazard_id", "person_id",
            "rs_id", "risk_id", "ll_id", "hazop_id", "pssr_id",
            "param_id", "incident_id", "id",
        ):
            val = props.get(key)
            if val:
                return str(val)
        kind = Neo4jClient._primary_label(labels)
        return kind

    def get_retrieved_subgraph(self, moc_ids=None, asset_id: str = None,
                               max_nodes: int = 40) -> dict:
        """1-hop neighborhood around retrieved MoCs (and optional Asset)."""
        ids = []
        for mid in moc_ids or []:
            if mid and str(mid) not in ("none", "None"):
                ids.append(str(mid))
        ids = list(dict.fromkeys(ids))
        aid = str(asset_id or "").strip()
        if aid in ("none", "None"):
            aid = ""

        empty = {"nodes": [], "links": []}
        if not ids and not aid:
            return empty

        query = """
        MATCH (seed:MoC)
        WHERE coalesce(seed.moc_id, seed.id) IN $moc_ids
        OPTIONAL MATCH (seed)-[r]-(nbr)
        WHERE type(r) IN $rel_types
        RETURN seed, r, nbr
        UNION
        MATCH (seed:Asset)
        WHERE $asset_id <> '' AND (seed.asset_id = $asset_id OR seed.id = $asset_id)
        OPTIONAL MATCH (seed)-[r]-(nbr)
        WHERE type(r) IN $rel_types
        RETURN seed, r, nbr
        """
        rows = self._run(query, {
            "moc_ids": ids or [""],
            "asset_id": aid,
            "rel_types": list(self._SUBGRAPH_REL_TYPES),
        })

        nodes: dict = {}
        links = []
        seen_links = set()

        def add_node(node_obj):
            if node_obj is None:
                return None
            labels = list(getattr(node_obj, "labels", []) or [])
            props = dict(node_obj)
            nid = self._business_id(props, labels)
            ntype = self._primary_label(labels)
            detail = str(
                props.get("title")
                or props.get("name")
                or props.get("role")
                or props.get("text")
                or props.get("description")
                or ""
            )[:80]
            if nid not in nodes:
                nodes[nid] = {
                    "id": nid,
                    "label": nid,
                    "type": ntype,
                    "detail": detail,
                }
            return nid

        for row in rows:
            sid = add_node(row.get("seed"))
            nid = add_node(row.get("nbr"))
            rel = row.get("r")
            if sid and nid and rel is not None:
                rel_type = rel.type if hasattr(rel, "type") else str(rel)
                key = (sid, nid, rel_type)
                rev = (nid, sid, rel_type)
                if key not in seen_links and rev not in seen_links:
                    seen_links.add(key)
                    links.append({"source": sid, "target": nid, "label": rel_type})

        node_list = list(nodes.values())[:max_nodes]
        keep = {n["id"] for n in node_list}
        link_list = [lk for lk in links if lk["source"] in keep and lk["target"] in keep]
        return {"nodes": node_list, "links": link_list}

    def get_lessons_learned(self, change_type: str, asset_id: str = None):
        """Use GENERATED_LESSON (new schema). LessonsLearned.text replaces .lesson"""
        query = """
        MATCH (m:MoC)-[:GENERATED_LESSON]->(ll:LessonsLearned)
        WHERE m.change_type CONTAINS $change_type
        RETURN m.moc_id AS moc_id, ll.text AS summary,
               null AS detail, null AS recommendation,
               null AS captured_by, m.change_type AS change_type
        LIMIT 5
        """
        return self._run(query, {"change_type": change_type})

    def search_mocs_by_keyword(self, keyword: str, limit: int = 5):
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        WHERE toLower(m.title) CONTAINS toLower($keyword)
           OR toLower(m.description) CONTAINS toLower($keyword)
           OR toLower(a.asset_id) CONTAINS toLower($keyword)
           OR toLower(a.name) CONTAINS toLower($keyword)
           OR toLower(m.change_type) CONTAINS toLower($keyword)
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.description AS description, m.change_type AS change_type,
               m.actual_cost AS cost, a.asset_id AS asset_id, a.name AS asset_name
        LIMIT $limit
        """
        return self._run(query, {"keyword": keyword, "limit": limit})

    def get_work_orders_for_moc(self, moc_id: str):
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:GENERATES]->(wo:WorkOrder)
        OPTIONAL MATCH (wo)-[:EXECUTED_ON]->(a:Asset)
        OPTIONAL MATCH (wo)-[:PERFORMED_BY]->(d:Department)
        OPTIONAL MATCH (wo)-[:INCLUDES_ACTIVITY]->(act:MaintenanceActivity)
        RETURN wo.wo_id AS wo_id, wo.title AS title, wo.work_type AS work_type,
               wo.status AS status,
               wo.actual_duration AS actual_hrs,
               wo.planned_duration AS planned_hrs,
               wo.actual_cost AS actual_cost, wo.delay_reason AS delay_reason,
               wo.failure_mode AS failure_mode, wo.equipment_status AS equipment_status,
               a.asset_id AS asset_id, d.name AS department,
               act.title AS activity, act.safety_req AS safety_req
        ORDER BY wo.date_issued
        """
        return self._run(query, {"moc_id": moc_id})

    def get_mocs_by_area(self, area_name: str):
        query = """
        MATCH (m:MoC)-[:LOCATED_IN]->(ar:Area)
        WHERE toLower(ar.area_id) CONTAINS toLower($area_name)
           OR toLower(ar.name) CONTAINS toLower($area_name)
        MATCH (m)-[:TARGETS]->(a:Asset)
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type, m.actual_cost AS cost,
               ar.name AS area, a.asset_id AS asset_id
        ORDER BY m.date_initiated DESC
        """
        return self._run(query, {"area_name": area_name})

    def get_mocs_with_incidents(self):
        query = """
        MATCH (m:MoC)
        WHERE m.incident_occurred = true
           OR EXISTS { MATCH (:Incident)-[:RELATED_TO]->(m) }
        OPTIONAL MATCH (i:Incident)-[:RELATED_TO]->(m)
        OPTIONAL MATCH (m)-[:TARGETS]->(a:Asset)
        RETURN coalesce(m.moc_id, m.id) AS moc_id,
               coalesce(m.title, m.name) AS title,
               coalesce(i.description, m.incident_description, m.lessons_learned) AS incident,
               coalesce(i.outcome, CASE WHEN m.incident_occurred THEN 'incident' END) AS outcome,
               m.lessons_learned AS lessons,
               coalesce(a.asset_id, a.id) AS asset_id
        ORDER BY m.date_initiated DESC
        """
        return self._run(query)

    def get_all_assets(self):
        return self._run("""
        MATCH (a:Asset)
        OPTIONAL MATCH (a)-[:BELONGS_TO]->(ar:Area)
        RETURN a.asset_id AS id, a.name AS name,
               a.equipment_type AS type, a.criticality AS criticality,
               ar.name AS area
        ORDER BY a.asset_id
        """)

    def get_all_mocs(self):
        return self._run("""
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type, m.actual_cost AS cost,
               m.actual_manhours AS manhours, a.asset_id AS asset_id
        ORDER BY m.date_initiated
        """)

    def get_downstream_impacts(self, asset_id: str):
        query = """
        MATCH (src:Asset {asset_id: $asset_id})
        MATCH path = (src)-[:UPSTREAM_OF|IMPACTS|CONTROLS_FLOW_TO|FEEDS*1..4]->(b:Asset)
        RETURN DISTINCT b.asset_id AS asset_id, b.name AS name,
               b.equipment_type AS type, length(path) AS hops
        ORDER BY hops
        """
        return self._run(query, {"asset_id": asset_id})

    def get_approval_stages_full(self, moc_id: str) -> list:
        """Return all ApprovalStage records for a MoC, ordered by stage number.
        ApprovalStage nodes are linked via stage_id prefix pattern (AS-{num}-{order}).
        Returns [] for unknown moc_id (no exception raised)."""
        # Extract numeric part from moc_id (e.g. "MoC-003" → "003")
        import re
        m = re.search(r'(\d+)$', moc_id)
        if not m:
            return []
        num = m.group(1)
        prefix = f"AS-{num}-"
        query = """
        MATCH (s:ApprovalStage)
        WHERE s.stage_id STARTS WITH $prefix
        RETURN s.order AS stage_number, s.stage AS stage_name,
               s.role AS assigned_role, 'Completed' AS status,
               toString(s.timestamp) AS timestamp
        ORDER BY s.order
        """
        return self._run(query, {"prefix": prefix})

    def get_failure_modes(self, moc_id: str) -> list:
        """Return all FailureMode records linked through the MoC's hazards.
        Returns [] for unknown moc_id (no exception raised)."""
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:IDENTIFIES]->(h:Hazard)-[:MANIFESTS_AS]->(fm:FailureMode)
        RETURN fm.fm_id AS fm_id, fm.mode AS mode, fm.consequence AS consequence,
               fm.likelihood AS likelihood, fm.description AS description,
               h.description AS hazard_description
        """
        return self._run(query, {"moc_id": moc_id})

    def get_wo_analytics(self, moc_id: str) -> list:
        """Return WorkOrder analytics for a MoC with pre-computed overrun values.
        Returns [] for unknown moc_id (no exception raised)."""
        query = """
        MATCH (m:MoC {moc_id: $moc_id})-[:GENERATES]->(wo:WorkOrder)
        RETURN wo.wo_id AS wo_id, wo.title AS title, wo.work_type AS work_type,
               wo.status AS status, wo.planned_duration AS planned_duration,
               wo.actual_duration AS actual_duration,
               wo.estimated_cost AS estimated_cost, wo.actual_cost AS actual_cost,
               wo.delay_reason AS delay_reason, wo.failure_mode AS failure_mode,
               (wo.actual_duration - wo.planned_duration) AS duration_overrun,
               (wo.actual_cost - wo.estimated_cost) AS cost_overrun
        ORDER BY wo.wo_id
        """
        return self._run(query, {"moc_id": moc_id})

    # ── New query methods for 40-query coverage ────────────────────────────

    def get_mocs_by_pid(self, pid_ref: str):
        """Find MoCs that reference a specific P&ID document."""
        query = """
        MATCH (m:MoC)-[:REFERENCES_PID]->(p:PIDDocument)
        WHERE toLower(p.pid_ref) CONTAINS toLower($pid_ref)
        MATCH (m)-[:TARGETS]->(a:Asset)
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type, m.actual_cost AS cost,
               p.pid_ref AS pid_ref, p.version AS version,
               a.asset_id AS asset_id, a.name AS asset_name
        ORDER BY m.date_initiated DESC
        """
        return self._run(query, {"pid_ref": pid_ref})

    def get_mocs_by_risk_score(self, min_score: int = 0, max_score: int = 100):
        """Filter MoCs by risk score range."""
        query = """
        MATCH (m:MoC)-[:REQUIRES]->(ra:RiskAssessment)
        MATCH (m)-[:TARGETS]->(a:Asset)
        WHERE ra.overall_score >= $min_score AND ra.overall_score <= $max_score
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type,
               ra.risk_category AS risk_category,
               ra.overall_score AS risk_score,
               ra.risk_people AS risk_people,
               ra.risk_asset AS risk_asset,
               m.hazop_required AS hazop_required,
               a.asset_id AS asset_id, a.name AS asset_name
        ORDER BY ra.overall_score DESC
        """
        return self._run(query, {"min_score": min_score, "max_score": max_score})

    def get_dependency_path(self, from_asset: str, to_asset: str):
        """Find dependency path between two assets."""
        query = """
        MATCH path = (a:Asset {asset_id: $from_asset})
                     -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|FEEDS*1..6]->
                     (b:Asset {asset_id: $to_asset})
        RETURN [node IN nodes(path) | node.asset_id + ' (' + node.equipment_type + ')'] AS path_nodes,
               [rel IN relationships(path) | type(rel)] AS path_rels,
               length(path) AS hops
        ORDER BY hops LIMIT 3
        """
        return self._run(query, {"from_asset": from_asset, "to_asset": to_asset})

    def get_all_dependency_paths(self, asset_id: str):
        """Get all downstream paths from an asset with relationship types."""
        query = """
        MATCH path = (a:Asset {asset_id: $asset_id})
                     -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|FEEDS*1..4]->
                     (b:Asset)
        RETURN DISTINCT
               b.asset_id AS target_id, b.name AS target_name,
               b.equipment_type AS target_type,
               length(path) AS hops,
               [rel IN relationships(path) | type(rel)] AS relationship_types,
               [node IN nodes(path) | node.asset_id] AS path_nodes
        ORDER BY hops
        """
        return self._run(query, {"asset_id": asset_id})

    def get_parameter_threshold(self, asset_id: str):
        """Get parameter thresholds for an asset."""
        query = """
        MATCH (a:Asset {asset_id: $asset_id})-[:HAS_PARAMETER]->(p:Parameter)
        RETURN p.parameter_name AS name, p.old_value AS old_value,
               p.new_value AS new_value, p.threshold AS threshold,
               a.asset_id AS asset_id, a.name AS asset_name
        """
        return self._run(query, {"asset_id": asset_id})

    def get_mocs_with_rework(self):
        """Get MoCs that required rework."""
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        WHERE m.incident_occurred = true
        OPTIONAL MATCH (i:Incident)-[:RELATED_TO]->(m)
        OPTIONAL MATCH (m)-[:GENERATED_LESSON]->(ll:LessonsLearned)
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type,
               m.actual_cost AS actual_cost, m.estimated_cost AS estimated_cost,
               m.actual_manhours AS actual_manhours,
               m.estimated_manhours AS estimated_manhours,
               i.description AS incident, i.outcome AS outcome,
               ll.text AS lesson,
               a.asset_id AS asset_id
        ORDER BY m.date_initiated DESC
        """
        return self._run(query)

    def get_wo_planned_vs_actual(self, change_type: str = None):
        """Get work order planned vs actual duration/cost for analytics."""
        if change_type:
            query = """
            MATCH (m:MoC)-[:GENERATES]->(wo:WorkOrder)
            WHERE m.change_type CONTAINS $change_type
            RETURN m.moc_id AS moc_id, m.title AS moc_title,
                   wo.wo_id AS wo_id, wo.title AS wo_title,
                   wo.planned_duration AS planned_hrs,
                   wo.actual_duration AS actual_hrs,
                   wo.estimated_cost AS estimated_cost,
                   wo.actual_cost AS actual_cost,
                   wo.delay_reason AS delay_reason,
                   wo.failure_mode AS failure_mode
            ORDER BY m.date_initiated
            """
            return self._run(query, {"change_type": change_type})
        else:
            query = """
            MATCH (m:MoC)-[:GENERATES]->(wo:WorkOrder)
            RETURN m.moc_id AS moc_id, m.title AS moc_title,
                   wo.wo_id AS wo_id, wo.title AS wo_title,
                   wo.planned_duration AS planned_hrs,
                   wo.actual_duration AS actual_hrs,
                   wo.estimated_cost AS estimated_cost,
                   wo.actual_cost AS actual_cost,
                   wo.delay_reason AS delay_reason,
                   wo.failure_mode AS failure_mode
            ORDER BY m.date_initiated
            """
            return self._run(query)

    def get_mocs_by_concept(self, concept: str):
        """Full-text concept search across MoC title, description, hazard, parameter."""
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        OPTIONAL MATCH (m)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (m)-[:CHANGES_PARAMETER]->(p:Parameter)
        WHERE toLower(m.title) CONTAINS toLower($concept)
           OR toLower(m.description) CONTAINS toLower($concept)
           OR toLower(m.parameter_name) CONTAINS toLower($concept)
           OR toLower(h.description) CONTAINS toLower($concept)
           OR toLower(h.category) CONTAINS toLower($concept)
           OR toLower(p.parameter_name) CONTAINS toLower($concept)
           OR toLower(a.name) CONTAINS toLower($concept)
        WITH m, a
        ORDER BY m.date_initiated DESC
        RETURN DISTINCT m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type, m.actual_cost AS cost,
               a.asset_id AS asset_id, a.name AS asset_name,
               m.lessons_learned AS lessons
        """
        return self._run(query, {"concept": concept})

    def get_mocs_requiring_training(self):
        """Get MoCs that involved training or procedure updates."""
        query = """
        MATCH (m:MoC)-[:TARGETS]->(a:Asset)
        WHERE m.change_type CONTAINS 'Procedural'
           OR m.change_type CONTAINS 'Procedure'
           OR toLower(m.description) CONTAINS 'train'
           OR toLower(m.description) CONTAINS 'procedure'
           OR toLower(m.description) CONTAINS 'operator'
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type,
               m.final_approver_role AS approver,
               a.asset_id AS asset_id
        ORDER BY m.date_initiated DESC
        """
        return self._run(query)

    def get_mocs_in_area(self, area_keyword: str):
        """Get MoCs in a specific plant area by keyword."""
        query = """
        MATCH (m:MoC)-[:LOCATED_IN]->(ar:Area)
        WHERE toLower(ar.name) CONTAINS toLower($area_keyword)
           OR toLower(ar.area_id) CONTAINS toLower($area_keyword)
        MATCH (m)-[:TARGETS]->(a:Asset)
        OPTIONAL MATCH (m)-[:REQUIRES]->(ra:RiskAssessment)
        RETURN m.moc_id AS moc_id, m.title AS title,
               m.change_type AS change_type,
               ra.overall_score AS risk_score,
               ra.risk_category AS risk_category,
               ar.name AS area, a.asset_id AS asset_id
        ORDER BY ra.overall_score DESC
        """
        return self._run(query, {"area_keyword": area_keyword})

    # ── Enhancement 1: Stronger Process Asset Connectivity Modelling ───────

    def get_full_connectivity_map(self, asset_id: str):
        """
        Returns the complete connectivity map for an asset — all relationships
        in both directions with relationship type, flow type, and hop distance.
        Used for process topology analysis and impact propagation.
        """
        query = """
        MATCH (src:Asset {asset_id: $asset_id})
        OPTIONAL MATCH (src)-[r_out]->(downstream:Asset)
        WHERE type(r_out) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                               'DEPENDS_ON','IMPACTS','CONNECTS','CIRCULATES_TO']
        OPTIONAL MATCH (upstream:Asset)-[r_in]->(src)
        WHERE type(r_in) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                               'DEPENDS_ON','IMPACTS','CONNECTS','CIRCULATES_TO']
        WITH src,
             collect(DISTINCT {
                 asset_id:   downstream.asset_id,
                 name:       downstream.name,
                 type:       downstream.equipment_type,
                 criticality: downstream.criticality,
                 rel_type:   type(r_out),
                 flow_type:  r_out.flow_type,
                 direction:  'downstream'
             }) AS downstream_nodes,
             collect(DISTINCT {
                 asset_id:   upstream.asset_id,
                 name:       upstream.name,
                 type:       upstream.equipment_type,
                 criticality: upstream.criticality,
                 rel_type:   type(r_in),
                 flow_type:  r_in.flow_type,
                 direction:  'upstream'
             }) AS upstream_nodes
        RETURN src.asset_id AS asset_id,
               src.name AS name,
               src.equipment_type AS equipment_type,
               src.criticality AS criticality,
               downstream_nodes,
               upstream_nodes,
               size(downstream_nodes) AS downstream_count,
               size(upstream_nodes) AS upstream_count
        """
        result = self._run(query, {"asset_id": asset_id})
        if not result:
            return None
        row = result[0]
        # Filter out null entries from optional matches
        row["downstream_nodes"] = [
            n for n in (row.get("downstream_nodes") or [])
            if n and n.get("asset_id")
        ]
        row["upstream_nodes"] = [
            n for n in (row.get("upstream_nodes") or [])
            if n and n.get("asset_id")
        ]
        return row

    def get_process_flow_topology(self):
        """
        Returns the complete process flow topology of the FCC unit as a graph
        of nodes and directed edges with relationship metadata.
        Used for visualisation and propagation modelling.
        """
        query = """
        MATCH (a:Asset)-[r]->(b:Asset)
        WHERE type(r) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                           'DEPENDS_ON','IMPACTS','CONNECTS','CIRCULATES_TO',
                           'SHUTS_DOWN']
        RETURN a.asset_id AS source_id,
               a.name AS source_name,
               a.equipment_type AS source_type,
               a.criticality AS source_criticality,
               type(r) AS relationship,
               r.flow_type AS flow_type,
               r.description AS flow_description,
               b.asset_id AS target_id,
               b.name AS target_name,
               b.equipment_type AS target_type,
               b.criticality AS target_criticality
        ORDER BY a.criticality DESC, b.criticality DESC
        """
        return self._run(query)

    def get_asset_connectivity_score(self, asset_id: str) -> dict:
        """
        Computes a connectivity score for an asset based on:
        - Number of direct upstream/downstream connections
        - Number of MoCs targeting this asset
        - Number of hazards associated
        - Criticality rating
        - Whether it is a shutdown target (ESD)
        Returns a dict with score components and total score.
        """
        query = """
        MATCH (a:Asset {asset_id: $asset_id})
        OPTIONAL MATCH (a)-[r_out]->(b:Asset)
        WHERE type(r_out) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                               'DEPENDS_ON','IMPACTS','CONNECTS']
        OPTIONAL MATCH (c:Asset)-[r_in]->(a)
        WHERE type(r_in) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                               'DEPENDS_ON','IMPACTS','CONNECTS']
        OPTIONAL MATCH (m:MoC)-[:TARGETS]->(a)
        OPTIONAL MATCH (m2:MoC)-[:TARGETS]->(a)-[:IDENTIFIES]->(h:Hazard)
        OPTIONAL MATCH (esd:Asset {asset_id: 'ESD-SYS'})-[:SHUTS_DOWN]->(a)
        RETURN a.asset_id AS asset_id,
               a.name AS name,
               a.criticality AS criticality,
               count(DISTINCT b) AS downstream_connections,
               count(DISTINCT c) AS upstream_connections,
               count(DISTINCT m) AS moc_count,
               count(DISTINCT h) AS hazard_count,
               CASE WHEN esd IS NOT NULL THEN 1 ELSE 0 END AS is_esd_target
        """
        result = self._run(query, {"asset_id": asset_id})
        if not result:
            return {"asset_id": asset_id, "score": 0, "components": {}}
        r = result[0]
        # Weighted connectivity score
        components = {
            "criticality":            int(r.get("criticality") or 0) * 10,
            "downstream_connections": int(r.get("downstream_connections") or 0) * 5,
            "upstream_connections":   int(r.get("upstream_connections") or 0) * 3,
            "moc_count":              int(r.get("moc_count") or 0) * 4,
            "hazard_count":           int(r.get("hazard_count") or 0) * 6,
            "is_esd_target":          int(r.get("is_esd_target") or 0) * 15,
        }
        total = sum(components.values())
        return {
            "asset_id":              r.get("asset_id"),
            "name":                  r.get("name"),
            "criticality":           r.get("criticality"),
            "downstream_connections": r.get("downstream_connections"),
            "upstream_connections":  r.get("upstream_connections"),
            "moc_count":             r.get("moc_count"),
            "hazard_count":          r.get("hazard_count"),
            "is_esd_target":         bool(r.get("is_esd_target")),
            "score":                 total,
            "components":            components,
        }

    def get_enriched_impact_chain(self, asset_id: str, depth: int = 4):
        """
        Enhanced impact chain that includes relationship types, flow metadata,
        criticality scores, and whether each downstream asset has active MoCs.
        Used by the downtime propagator and agent.
        """
        query = """
        MATCH path = (a:Asset {asset_id: $asset_id})
                     -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|
                        FEEDS|CONNECTS|CIRCULATES_TO*1..4]->
                     (b:Asset)
        WITH b, path, length(path) AS hops
        OPTIONAL MATCH (m:MoC)-[:TARGETS]->(b)
        OPTIONAL MATCH (b)-[:BELONGS_TO]->(ar:Area)
        RETURN DISTINCT
               b.asset_id AS node_id,
               b.name AS node_name,
               b.equipment_type AS node_type,
               b.criticality AS criticality,
               hops AS hop_distance,
               [rel IN relationships(path) | type(rel)] AS relationship_chain,
               [rel IN relationships(path) | coalesce(rel.flow_type, '')] AS flow_types,
               count(DISTINCT m) AS active_moc_count,
               ar.name AS area
        ORDER BY hops, b.criticality DESC
        """
        return self._run(query, {"asset_id": asset_id})

    def get_critical_path(self, from_asset: str, to_asset: str):
        """
        Finds the shortest critical path between two assets, weighted by
        criticality. Returns path nodes, relationship types, and total
        criticality weight.
        """
        query = """
        MATCH path = (a:Asset {asset_id: $from_asset})
                     -[:UPSTREAM_OF|DEPENDS_ON|IMPACTS|CONTROLS_FLOW_TO|
                        FEEDS|CONNECTS|CIRCULATES_TO*1..6]->
                     (b:Asset {asset_id: $to_asset})
        WITH path,
             [node IN nodes(path) | node.asset_id] AS path_nodes,
             [node IN nodes(path) | coalesce(node.criticality, 1)] AS criticalities,
             [rel IN relationships(path) | type(rel)] AS rel_types,
             length(path) AS hops
        RETURN path_nodes,
               rel_types,
               hops,
               reduce(total = 0, c IN criticalities | total + c) AS criticality_weight
        ORDER BY criticality_weight DESC, hops
        LIMIT 3
        """
        return self._run(query, {"from_asset": from_asset, "to_asset": to_asset})

    def get_all_assets_with_connectivity(self):
        """
        Returns all assets with their connectivity scores for the topology
        overview panel and agent reasoning.
        """
        query = """
        MATCH (a:Asset)
        OPTIONAL MATCH (a)-[r_out]->(b:Asset)
        WHERE type(r_out) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                               'DEPENDS_ON','IMPACTS','CONNECTS']
        OPTIONAL MATCH (c:Asset)-[r_in]->(a)
        WHERE type(r_in) IN ['UPSTREAM_OF','FEEDS','CONTROLS_FLOW_TO',
                               'DEPENDS_ON','IMPACTS','CONNECTS']
        OPTIONAL MATCH (m:MoC)-[:TARGETS]->(a)
        OPTIONAL MATCH (a)-[:BELONGS_TO]->(ar:Area)
        RETURN a.asset_id AS asset_id,
               a.name AS name,
               a.equipment_type AS equipment_type,
               a.criticality AS criticality,
               ar.name AS area,
               count(DISTINCT b) AS downstream_count,
               count(DISTINCT c) AS upstream_count,
               count(DISTINCT m) AS moc_count
        ORDER BY a.criticality DESC, a.asset_id
        """
        return self._run(query)

    def get_shutdown_propagation_tree(self, asset_id: str):
        """
        Returns the full shutdown propagation tree — which assets would be
        affected if this asset goes offline, including ESD-triggered shutdowns.
        """
        query = """
        MATCH (src:Asset {asset_id: $asset_id})
        OPTIONAL MATCH path1 = (src)-[:UPSTREAM_OF|FEEDS|CONTROLS_FLOW_TO*1..4]->(affected:Asset)
        OPTIONAL MATCH (esd:Asset {asset_id: 'ESD-SYS'})-[:SHUTS_DOWN]->(esd_target:Asset)
        WITH src,
             collect(DISTINCT {
                 asset_id: affected.asset_id,
                 name: affected.name,
                 type: affected.equipment_type,
                 criticality: affected.criticality,
                 hops: length(path1),
                 trigger: 'process_flow'
             }) AS flow_affected,
             collect(DISTINCT {
                 asset_id: esd_target.asset_id,
                 name: esd_target.name,
                 type: esd_target.equipment_type,
                 criticality: esd_target.criticality,
                 hops: 1,
                 trigger: 'esd_shutdown'
             }) AS esd_affected
        RETURN src.asset_id AS source_asset,
               src.name AS source_name,
               src.criticality AS source_criticality,
               [n IN flow_affected WHERE n.asset_id IS NOT NULL] AS flow_affected,
               [n IN esd_affected WHERE n.asset_id IS NOT NULL] AS esd_affected
        """
        result = self._run(query, {"asset_id": asset_id})
        return result[0] if result else None
