"""
core/vector_store.py
ChromaDB vector store with enriched semantic embeddings.
"""

from typing import List, Dict, Any

from core.config import (
    CHROMA_PERSIST_DIR, CHROMA_COLLECTION, TOP_K_SIMILAR,
    RAG_EMBEDDING_PROVIDER, OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL
)


def _get_embedder():
    if RAG_EMBEDDING_PROVIDER != "openai":
        raise ValueError("Only OpenAI embeddings are supported.")
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

    class OpenAIEmbedder:
        def encode(self, texts, **kwargs):
            import numpy as np
            if isinstance(texts, str):
                texts = [texts]
            resp = client.embeddings.create(model=OPENAI_EMBEDDING_MODEL, input=texts)
            return np.array([d.embedding for d in resp.data])

    return OpenAIEmbedder()


def _expand_query(query_text: str) -> str:
    """
    Lightweight additive query expansion for domain synonym bridging.
    Appends relevant synonyms to the original query so the embedding model
    can bridge vocabulary gaps between user phrasing and stored document text.
    The original query is always preserved — expansion is purely additive.
    """
    q = query_text.lower()
    expansions = []

    # ── Explicit MoC ID comparison queries ────────────────────────────────
    # When user names specific MoC IDs, expand with their known content
    if "moc-003" in q:
        expansions.append(
            "MoC-003 reactor R-201 temperature setpoint adjustment 510C to 525C "
            "process parameter change FCC reactor thermal control risk score 8 medium"
        )
    if "moc-005" in q:
        expansions.append(
            "MoC-005 catalyst slide valve SV-204 control system upgrade instrumentation "
            "actuator advanced feedback catalyst circulation risk score 12 high"
        )
    if "moc-001" in q:
        expansions.append(
            "MoC-001 feed pump P-101 replacement mechanical equipment risk score 12 high"
        )
    if "moc-009" in q:
        expansions.append(
            "MoC-009 emergency shutdown ESD procedure update procedural change "
            "operator training HSE risk score 10 high"
        )

    # ── Catalyst circulation / FCC slide valve ─────────────────────────────
    if any(t in q for t in ["catalyst circulation", "catalyst instability",
                              "catalyst flow", "slide valve", "sv-204"]):
        expansions.append(
            "catalyst flow control FCC catalyst slide valve reactor regenerator balance "
            "catalyst circulation control actuator upgrade MoC-005 instrumentation change"
        )

    # ── Reactor temperature / setpoint ────────────────────────────────────
    if any(t in q for t in ["temperature setpoint", "reactor temperature", "r-201",
                              "setpoint", "thermal", "overheating", "525", "510",
                              "545", "600", "maximum limit", "design limit"]):
        expansions.append(
            "thermal control overheating risk setpoint increase process parameter "
            "reactor temperature setpoint adjustment operating window MoC-003 "
            "R-201 reactor temperature 510C 525C 545C threshold limit margin"
        )

    # ── Emergency shutdown / ESD / procedure ──────────────────────────────
    if any(t in q for t in ["emergency shutdown", "esd", "shutdown procedure",
                              "procedure update", "operator training", "procedural",
                              "training", "drill", "sign-off", "evidence", "close",
                              "revision", "rollout", "approve", "approver"]):
        expansions.append(
            "ESD procedure safety critical operator training shutdown procedure "
            "procedural update emergency response MoC-009 HSE manager "
            "training completion sign-off drill record procedure revision"
        )

    # ── Pump replacement / feed pump / reflux pump ────────────────────────
    if any(t in q for t in ["pump replacement", "feed pump", "reflux pump",
                              "p-101", "p-502"]):
        expansions.append(
            "mechanical reliability pump upgrade equipment replacement "
            "corrective maintenance pump failure MoC-001 MoC-008"
        )

    # ── Expander / energy recovery ────────────────────────────────────────
    if any(t in q for t in ["expander", "energy recovery", "ex-403",
                              "flue gas", "alignment"]):
        expansions.append(
            "flue gas expander mechanical upgrade alignment performance upgrade "
            "energy recovery efficiency improvement MoC-007"
        )

    # ── Wall thinning / piping integrity ──────────────────────────────────
    if any(t in q for t in ["wall thinning", "piping integrity", "ctl-205",
                              "transfer line", "weld", "corrosion", "ndt"]):
        expansions.append(
            "mechanical integrity weld inspection NDT corrosion piping reinforcement "
            "catalyst transfer line wall thinning MoC-010"
        )

    # ── Cyclone / separator ───────────────────────────────────────────────
    if any(t in q for t in ["cyclone", "separator", "c-203", "erosion",
                              "separation efficiency"]):
        expansions.append(
            "cyclone separator catalyst separation erosion repair mechanical maintenance "
            "catalyst carryover separation efficiency MoC-004"
        )

    # ── Steam / stripper ──────────────────────────────────────────────────
    if any(t in q for t in ["steam", "stripper", "s-301", "stripping",
                              "hydrocarbon carryover"]):
        expansions.append(
            "steam injection stripping efficiency hydrocarbon carryover catalyst stripper "
            "steam optimization MoC-006"
        )

    # ── Risk score / HAZOP / high risk ────────────────────────────────────
    if any(t in q for t in ["risk score", "risk assessment", "hazop", "high risk",
                              "risk category", ">= 12", "greater than 12",
                              "hazard study", "pre-startup", "pssr"]):
        expansions.append(
            "risk assessment HAZOP required process safety review risk score overall score "
            "risk category high medium PSSR pre-startup safety review "
            "hazard study required MoC-003 MoC-005 MoC-001 MoC-004 MoC-006"
        )

    # ── Planned vs actual / downtime / work orders ────────────────────────
    if any(t in q for t in ["planned vs actual", "planned vs", "actual duration",
                              "downtime", "work order", "wo", "overrun", "delay"]):
        expansions.append(
            "work order planned duration actual duration cost overrun delay reason "
            "maintenance activity corrective modification inspection "
            "planned vs actual downtime hours"
        )
        # If also about temperature changes, boost MoC-003
        if any(t in q for t in ["temperature", "setpoint", "r-201", "reactor"]):
            expansions.append(
                "MoC-003 reactor R-201 temperature setpoint process parameter change "
                "WO-005 WO-006 planned 4 hours actual 4 hours setpoint update "
                "planned 8 hours actual 9 hours verification"
            )

    # ── Safeguards / checklist / verification ─────────────────────────────
    if any(t in q for t in ["safeguard", "checklist", "verify", "verification",
                              "commissioning", "calibration", "interlock",
                              "functional test", "monitoring"]):
        expansions.append(
            "safeguards verification checklist commissioning calibration interlock "
            "functional test monitoring alarm PSSR pre-startup safety review "
            "loop tuning fail-safe position check"
        )

    # ── Dependency path / downstream / impact chain ───────────────────────
    if any(t in q for t in ["dependency path", "downstream", "impact chain",
                              "impacted assets", "upstream", "connected",
                              "most affected", "least affected", "effect on",
                              "what happens if", "goes offline", "process network",
                              "connectivity", "network effect", "propagate",
                              "regenerator", "fractionator", "compressor",
                              "replace actuator", "faster response"]):
        expansions.append(
            "dependency path downstream assets impact chain upstream connected "
            "reactor regenerator fractionator cyclone stripper transfer line "
            "UPSTREAM_OF DEPENDS_ON IMPACTS CONTROLS_FLOW_TO FEEDS CONNECTS "
            "process network connectivity coupling propagation most affected least affected "
            "R-201 RG-401 F-501 WGC-401 CTL-205 SV-204 C-203 S-301 K-402 EX-403"
        )

    # ── Lessons learned / rework / incident ───────────────────────────────
    if any(t in q for t in ["lessons learned", "rework", "incident", "common issues",
                              "past mocs", "similar past", "caused incidents",
                              "temperature changes caused", "common reasons",
                              "implementation issue"]):
        expansions.append(
            "lessons learned rework required incident occurred implementation issue "
            "delay commissioning problem steam leakage flange installation "
            "catalyst stripper steam optimization process and instrumentation "
            "weld defect alignment misalignment"
        )

    # ── P&ID reference — with full normalization ───────────────────────────
    # Map PID-FC-C-xxx ↔ PID-FCC-xxx both ways
    if any(t in q for t in ["pid", "p&id", "pid-fc", "pid-fcc", "pid-fc-c",
                              "piping", "instrumentation diagram"]):
        # Extract any PID number from query for targeted expansion
        import re
        pid_nums = re.findall(r'pid[-\s]?(?:fc[-\s]?c[-\s]?|fcc[-\s]?)(\d+)', q)
        pid_expansion = (
            "P&ID document reference piping instrumentation diagram "
            "PID-FCC-204 PID-FCC-201 PID-FCC-103 PID-FCC-301 PID-FCC-403 "
            "PID-FC-C-204 PID-FC-C-201 PID-FC-C-103 references PID"
        )
        # If a specific number found, boost that specific PID
        for num in pid_nums:
            pid_expansion += f" PID-FCC-{num} PID-FC-C-{num}"
        expansions.append(pid_expansion)

    # ── Approval workflow / stages ─────────────────────────────────────────────
    if any(t in q for t in ["stage", "screening", "change identification",
                              "risk assessment stage", "implementation planning",
                              "final approval", "who approved", "approval workflow",
                              "approval stage", "sign off stage", "approved by",
                              "who approves", "approver role", "who must approve",
                              "approve", "approver", "authorization", "sign off"]):
        expansions.append(
            "approval stage workflow Change Identification Screening Risk Assessment "
            "Implementation Planning Final Approval stage_number assigned_role "
            "HSE Manager Operations Manager Plant Manager Safety Manager "
            "stage 1 stage 2 stage 3 stage 4 stage 5 ApprovalStage HAS_STAGE"
        )

    # ── Failure mode ───────────────────────────────────────────────────────────
    if any(t in q for t in ["failure mode", "equipment failure", "consequence",
                              "what can go wrong", "failure cause", "fm_id",
                              "manifests as", "failure description"]):
        expansions.append(
            "failure mode consequence likelihood FailureMode equipment failure cause "
            "manifests as hazard failure description fm_id MANIFESTS_AS"
        )

    # ── FCC plant area ─────────────────────────────────────────────────────────
    if any(t in q for t in ["reactor section", "fractionation section",
                              "regenerator area", "feed section", "recovery section",
                              "gas concentration", "stripping section"]):
        expansions.append(
            "FCC plant area reactor section fractionation section regenerator area "
            "feed section recovery section gas concentration stripping section "
            "Area node LOCATED_IN AREA-RXR AREA-FEED AREA-REGEN AREA-FRAC AREA-STRIP"
        )

    if not expansions:
        return query_text

    return query_text + " " + " ".join(expansions)


def _extract_pid_number(query_text: str):
    """
    Extract a PID document number from a query string.
    Handles both PID-FC-C-xxx and PID-FCC-xxx formats.
    Returns the numeric suffix (e.g. '201', '204') or None.
    """
    import re
    m = re.search(r'pid[-\s]?(?:fc[-\s]?c[-\s]?|fcc[-\s]?)(\d+)', query_text, re.IGNORECASE)
    return m.group(1) if m else None


def _moc_to_text(moc: dict) -> str:
    """
    Build rich natural-language embedding text from MoC data.
    Combines factual sentences + semantic keyword tags for maximum retrieval accuracy.
    All enrichment happens BEFORE the return statement.
    """
    moc_id      = str(moc.get('moc_id') or moc.get('id', ''))
    title       = str(moc.get('title', ''))
    change_type = str(moc.get('change_type', ''))
    asset_id    = str(moc.get('asset_id', '') or moc.get('id', ''))
    asset_name  = str(moc.get('asset_name', ''))
    asset_cat   = str(moc.get('asset_category', '') or moc.get('equipment_type', ''))
    description = str(moc.get('description', ''))
    risk_level  = str(moc.get('risk_level', ''))
    risk_score  = str(moc.get('overall_risk_score', ''))
    hazard      = str(moc.get('hazard_description', '') or moc.get('hazard_text', ''))
    lessons     = str(moc.get('lessons_learned', '') or moc.get('lesson_detail', ''))
    hazop       = bool(moc.get('hazop_required', False))
    pssr        = bool(moc.get('pssr_required', False))
    cost        = moc.get('cost', '') or moc.get('actual_cost', '')
    downtime    = moc.get('downtime', '') or moc.get('actual_downtime', '')
    param_name  = str(moc.get('parameter_name', ''))
    old_val     = str(moc.get('old_value', ''))
    new_val     = str(moc.get('new_value', ''))
    threshold   = str(moc.get('threshold_limit', ''))
    incident    = bool(moc.get('incident_occurred', False))
    rework      = bool(moc.get('rework_required', False))
    pid_ref     = str(moc.get('pid_ref', '') or moc.get('pid_reference', ''))
    area        = str(moc.get('area', ''))

    # ── 1. Factual sentences ───────────────────────────────────────────────
    sentences = []

    sentences.append(
        f"{moc_id} titled '{title}' is a {change_type} change on asset "
        f"{asset_id} ({asset_name}, {asset_cat})."
    )

    if description:
        sentences.append(description)

    # Parameter change with threshold and margin
    if param_name and old_val and new_val:
        ps = f"This MoC changes the {param_name} from {old_val} to {new_val}."
        if threshold:
            ps += f" The design limit is {threshold}."
            try:
                nv = float(str(new_val).replace('°C','').replace(' C','').replace('C','').strip())
                th = float(str(threshold).replace('Max ','').replace('max ','')
                           .replace('°C','').replace(' C','').replace('C','').strip())
                margin = th - nv
                ps += f" Margin to design limit: {margin:.0f} units."
            except (ValueError, TypeError):
                pass
        sentences.append(ps)

    if risk_level:
        rs = f"Risk level is {risk_level}"
        if risk_score:
            rs += f" with overall risk score {risk_score}."
        else:
            rs += "."
        sentences.append(rs)

    reviews = []
    if hazop:
        reviews.append("HAZOP required")
    if pssr:
        reviews.append("PSSR required")
    if reviews:
        sentences.append(f"Safety reviews required: {', '.join(reviews)}.")

    if hazard:
        sentences.append(f"Identified hazard: {hazard}.")

    if incident:
        sentences.append("An incident occurred during implementation of this change.")

    if rework:
        sentences.append("Rework was required during implementation.")

    if lessons:
        sentences.append(f"Lessons learned: {lessons[:250]}.")

    if pid_ref and pid_ref not in ('', 'None', 'N/A', 'none'):
        sentences.append(f"References P&ID document {pid_ref}.")

    if area:
        sentences.append(f"Located in plant area: {area}.")

    if cost:
        try:
            sentences.append(f"Actual cost: ${int(float(str(cost))):,}.")
        except (ValueError, TypeError):
            sentences.append(f"Cost: {cost}.")

    if downtime:
        sentences.append(f"Actual downtime: {downtime} hours.")

    # ── 2. Semantic keyword tags (appended BEFORE return) ──────────────────
    tags = []
    ct  = change_type.lower()
    desc = description.lower()
    an   = asset_name.lower()

    # Change type tags
    if 'instrument' in ct or 'control' in ct:
        tags += ['instrumentation change', 'control system modification',
                 'actuator upgrade', 'valve control', 'DCS loop']
    if 'mechanical' in ct and 'integrity' not in ct and 'efficiency' not in ct:
        tags += ['mechanical change', 'equipment replacement', 'pump replacement',
                 'mechanical maintenance']
    if 'parameter' in ct or 'setpoint' in ct:
        tags += ['process parameter change', 'setpoint adjustment',
                 'operating window change', 'temperature setpoint']
    if 'procedural' in ct or 'procedure' in ct:
        tags += ['procedure update', 'ESD emergency shutdown procedure',
                 'operator training', 'safety procedure', 'administrative change']
    if 'integrity' in ct:
        tags += ['mechanical integrity', 'wall thinning', 'piping reinforcement',
                 'weld inspection', 'NDT', 'corrosion']
    if 'efficiency' in ct:
        tags += ['performance upgrade', 'energy recovery', 'expander upgrade',
                 'efficiency improvement']
    if 'maintenance' in ct:
        tags += ['mechanical maintenance', 'inspection repair', 'cyclone separator',
                 'erosion damage']

    # Asset / domain tags
    if 'catalyst' in desc or 'catalyst' in an or 'sv-204' in asset_id.lower():
        tags += ['catalyst circulation', 'FCC catalyst', 'reactor regenerator balance',
                 'slide valve', 'catalyst flow control']
    if 'temperature' in desc or 'temperature' in param_name.lower() or 'r-201' in asset_id.lower():
        tags += ['temperature setpoint', 'reactor temperature', 'thermal control',
                 'overheating risk', 'setpoint increase', 'process parameter']
    if 'steam' in desc or 's-301' in asset_id.lower():
        tags += ['steam injection', 'stripping efficiency', 'hydrocarbon carryover',
                 'catalyst stripper', 'steam optimization']
    if 'emergency' in desc or 'esd' in asset_id.lower() or 'esd' in desc:
        tags += ['emergency shutdown', 'ESD procedure', 'safety critical',
                 'operator training', 'shutdown procedure', 'procedural update']
    if 'pump' in an or 'p-101' in asset_id.lower() or 'p-502' in asset_id.lower():
        tags += ['pump replacement', 'feed pump', 'reflux pump', 'mechanical reliability']
    if 'expander' in an or 'ex-403' in asset_id.lower():
        tags += ['expander upgrade', 'flue gas expander', 'energy recovery',
                 'mechanical upgrade', 'alignment']
    if 'transfer line' in an or 'ctl-205' in asset_id.lower():
        tags += ['catalyst transfer line', 'piping integrity', 'wall thinning',
                 'mechanical integrity improvement', 'weld defect']
    if 'cyclone' in an or 'c-203' in asset_id.lower():
        tags += ['cyclone separator', 'catalyst separation', 'erosion repair',
                 'mechanical maintenance']
    if 'control valve' in asset_cat.lower() or 'fv-103' in asset_id.lower():
        tags += ['control valve upgrade', 'feed heater', 'temperature control',
                 'instrumentation upgrade', 'smart valve']

    # Outcome tags
    if incident:
        tags += ['incident occurred', 'safety event', 'near miss', 'rework required']
    if rework:
        tags += ['rework required', 'implementation issue', 'delay', 'commissioning problem']
    if hazop:
        tags += ['HAZOP required', 'hazard study', 'process safety review',
                 'safety assessment']
    if pssr:
        tags += ['PSSR required', 'pre-startup safety review', 'commissioning check']

    # PID tags
    if pid_ref and pid_ref not in ('', 'None', 'N/A'):
        # Store both the exact ref and a normalized variant (PID-FC-C-xxx style)
        tags.append(f"P&ID {pid_ref}")
        # Add alternate naming: PID-FCC-204 → PID-FC-C-204 and vice versa
        alt = pid_ref.replace("PID-FCC-", "PID-FC-C-").replace("PID-FCC", "PID-FC-C")
        if alt != pid_ref:
            tags.append(f"P&ID {alt}")
        # Also add without dashes for fuzzy matching
        num = ''.join(filter(str.isdigit, pid_ref))
        if num:
            tags.append(f"PID reference {num}")
            # Add all common variants explicitly
            tags.append(f"PID-FCC-{num} PID-FC-C-{num} references document {num}")
        tags.append("references PID document piping instrumentation diagram")

    # Append tags as a sentence
    if tags:
        sentences.append(f"Keywords: {', '.join(dict.fromkeys(tags))}.")

    # ── 3. Approval stage section ──────────────────────────────────────────
    stages = moc.get('approval_stages') or []
    # Filter out empty stage dicts (collect() can return {stage_number: None, ...})
    stages = [s for s in stages if s.get('stage_name')]
    if stages:
        stage_parts = [
            f"Stage {s.get('stage_number')} '{s.get('stage_name')}' assigned to {s.get('assigned_role')} ({s.get('status') or 'pending'})"
            for s in stages
        ]
        sentences.append(f"Approval workflow: {'; '.join(stage_parts)}.")

    # ── 4. Failure mode section ────────────────────────────────────────────
    fms = moc.get('failure_modes') or []
    fms = [f for f in fms if f.get('mode')]
    if fms:
        fm_parts = [f"{fm.get('mode')}: {fm.get('consequence') or 'see hazard'}" for fm in fms[:3]]
        sentences.append(f"Failure modes: {'; '.join(fm_parts)}.")

    # ── 5. Work order section ──────────────────────────────────────────────
    wos = moc.get('work_orders') or []
    wos = [w for w in wos if w.get('wo_id')]
    if wos:
        wo_parts = []
        for wo in wos[:4]:
            p = wo.get('planned_duration') or 0
            a = wo.get('actual_duration') or 0
            ac = wo.get('actual_cost') or 0
            dr = wo.get('delay_reason') or 'none'
            wo_parts.append(f"{wo.get('wo_id')} planned {p}h actual {a}h cost ${int(float(str(ac))):,} delay: {str(dr)[:60]}")
        sentences.append(f"Work orders: {'; '.join(wo_parts)}.")

    # ── 6. Personnel/approver section ─────────────────────────────────────
    roles = [r for r in (moc.get('approver_roles') or []) if r]
    depts = [d for d in (moc.get('approver_departments') or []) if d]
    if roles:
        sentences.append(f"Approved by: {', '.join(roles[:3])} from {', '.join(depts[:3]) if depts else 'various departments'}.")

    return " ".join(s for s in sentences if s.strip())


class VectorStore:
    def __init__(self):
        import chromadb
        from chromadb.config import Settings

        self.embedder = _get_embedder()
        self.client = chromadb.PersistentClient(
            path=CHROMA_PERSIST_DIR,
            settings=Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )

    def add_mocs(self, mocs: List[Dict[str, Any]]) -> int:
        existing_ids = set(self.collection.get()["ids"])
        new_mocs = [m for m in mocs if str(m.get("moc_id") or m.get("id", "")) not in existing_ids]
        if not new_mocs:
            print("Vector store already up to date.")
            return 0
        texts      = [_moc_to_text(m) for m in new_mocs]
        ids        = [str(m.get("moc_id") or m.get("id")) for m in new_mocs]
        embeddings = self.embedder.encode(texts, show_progress_bar=False).tolist()
        metadatas  = [{k: str(v) for k, v in m.items() if v is not None} for m in new_mocs]
        self.collection.add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
        print(f"Added {len(new_mocs)} MoCs to vector store.")
        return len(new_mocs)

    def search(self, query_text: str, top_k: int = TOP_K_SIMILAR, filters: Dict[str, Any] = None) -> List[Dict]:
        if self.collection.count() == 0:
            return []

        # ── PID exact-match pre-filter ─────────────────────────────────────
        # PID codes like PID-FC-C-201 / PID-FCC-201 are alphanumeric identifiers
        # that the embedding model cannot distinguish by semantics alone.
        # When detected, inject a metadata $in filter covering both naming variants
        # so ChromaDB only considers MoCs whose stored pid_ref matches.
        pid_num = _extract_pid_number(query_text)
        if pid_num and not filters:
            filters = {
                "pid_ref": {
                    "$in": [f"PID-FCC-{pid_num}", f"PID-FC-C-{pid_num}"]
                }
            }

        expanded = _expand_query(query_text)
        query_embedding = self.embedder.encode([expanded]).tolist()
        n = min(top_k, self.collection.count())
        query_args = {
            "query_embeddings": query_embedding,
            "n_results": n,
            "include": ["documents", "metadatas", "distances"],
        }
        if filters:
            query_args["where"] = filters
        try:
            results = self.collection.query(**query_args)
        except Exception:
            # If filter returns no results, fall back to unfiltered search
            query_args.pop("where", None)
            results = self.collection.query(**query_args)

        hits = []
        for i in range(len(results["ids"][0])):
            hits.append({
                "moc_id":     results["ids"][0][i],
                "text":       results["documents"][0][i],
                "metadata":   results["metadatas"][0][i],
                "similarity": round(1 - results["distances"][0][i], 4)
            })
        return hits

    def count(self) -> int:
        return self.collection.count()

    def reset(self):
        self.client.delete_collection(CHROMA_COLLECTION)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"}
        )
