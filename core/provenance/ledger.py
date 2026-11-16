"""
core/provenance/ledger.py — collects evidence, findings, gaps and checkpoints for one case.

Agents write to the ledger; the supervisor turns it into the case record. Evidence is
de-duplicated by id, so two agents citing the same asset share one evidence entry.

Pure: standard library only.
"""
from __future__ import annotations

import threading
from typing import Dict, Iterable, List, Optional

from .types import (
    AgentContribution,
    Basis,
    CheckpointKind,
    Evidence,
    Finding,
    HumanCheckpoint,
    SourceKind,
    Verification,
    to_jsonable,
)


def evidence_id(source: SourceKind, reference: str) -> str:
    return f"{source.value}:{reference}"


class Ledger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._evidence: Dict[str, Evidence] = {}
        self._checkpoints: Dict[str, HumanCheckpoint] = {}
        self._counter = 0

    # evidence ─────────────────────────────────────────────────────────────────
    def cite(self, source: SourceKind, reference: str, label: str, detail: str = "") -> str:
        """Record a piece of evidence (once) and return its id."""
        eid = evidence_id(source, reference)
        with self._lock:
            if eid not in self._evidence:
                self._evidence[eid] = Evidence(id=eid, source=source, reference=reference, label=label, detail=detail)
        return eid

    def cite_many(self, source: SourceKind, items: Iterable[tuple]) -> List[str]:
        return [self.cite(source, *item) for item in items]

    def has(self, eid: str) -> bool:
        return eid in self._evidence

    def evidence(self) -> List[Evidence]:
        return sorted(self._evidence.values(), key=lambda e: (e.source.value, e.reference))

    # findings ─────────────────────────────────────────────────────────────────
    def finding(self, agent: str, statement: str, basis: Basis, evidence: Iterable[str] = (),
                confidence: Optional[str] = None, verification: Verification = Verification.UNVERIFIED,
                note: str = "") -> Finding:
        with self._lock:
            self._counter += 1
            fid = f"F{self._counter:03d}"
        return Finding(id=fid, statement=statement, agent=agent, basis=basis, evidence=list(dict.fromkeys(evidence)),
                       confidence=confidence, verification=verification, note=note)

    # checkpoints ──────────────────────────────────────────────────────────────
    def checkpoint(self, kind: CheckpointKind, what: str, why: str, role: str, raised_by: str) -> None:
        key = f"{kind.value}:{what}"
        with self._lock:
            if key not in self._checkpoints:
                cid = f"H{len(self._checkpoints) + 1:02d}"
                self._checkpoints[key] = HumanCheckpoint(id=cid, kind=kind, what=what, why=why, role=role, raised_by=raised_by)

    def checkpoints(self) -> List[HumanCheckpoint]:
        # approvals last: verification comes before the decision
        return sorted(self._checkpoints.values(), key=lambda c: (c.kind == CheckpointKind.APPROVAL, c.id))


def summarise(contributions: List[AgentContribution], ledger: Ledger) -> Dict:
    """The 'Why this recommendation?' payload: everything, grouped for display."""
    findings = [f for c in contributions for f in c.findings]
    gaps = [g for c in contributions for g in c.gaps]
    by_source: Dict[str, List[Evidence]] = {}
    for e in ledger.evidence():
        by_source.setdefault(e.source.value, []).append(e)
    return {
        "contributions": to_jsonable(contributions),
        "evidence": to_jsonable(ledger.evidence()),
        "evidence_by_source": {k: to_jsonable(v) for k, v in by_source.items()},
        "findings": to_jsonable(findings),
        "conflicts": to_jsonable([f for f in findings if f.verification is Verification.CONFLICT]),
        "assumptions": to_jsonable([g for g in gaps if g.kind == "assumption"]),
        "uncertainties": to_jsonable([g for g in gaps if g.kind == "uncertainty"]),
        "missing": to_jsonable([g for g in gaps if g.kind == "missing"]),
        "checkpoints": to_jsonable(ledger.checkpoints()),
        "counts": {
            "agents": len(contributions),
            "evidence": len(ledger.evidence()),
            "findings": len(findings),
            "verified": sum(1 for f in findings if f.verification is Verification.VERIFIED),
            "unverified": sum(1 for f in findings if f.verification is Verification.UNVERIFIED),
            "conflicts": sum(1 for f in findings if f.verification is Verification.CONFLICT),
        },
    }
