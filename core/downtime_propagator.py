"""
core/downtime_propagator.py
Enhancement 2: Dynamic Downtime Propagation Between Linked Assets

Traverses the Neo4j process topology graph and propagates downtime estimates
across connected assets. Each downstream asset receives a fraction of the
upstream downtime based on:
  - Relationship type (FEEDS/CONTROLS_FLOW_TO = high coupling)
  - Asset criticality (higher criticality = more impact)
  - Hop distance (exponential decay per hop)
  - Historical MoC downtime data for the asset

The result is a ranked list of assets with their estimated propagated downtime,
confidence intervals, and the propagation path that caused the impact.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from core.neo4j_client import Neo4jClient


# ── Coupling coefficients by relationship type ─────────────────────────────
# How much of the upstream downtime propagates through each relationship type.
# Values are fractions (0.0 – 1.0).
COUPLING_COEFFICIENTS: dict[str, float] = {
    "FEEDS":              0.85,   # Direct material/energy flow — very high coupling
    "CONTROLS_FLOW_TO":  0.80,   # Control dependency — high coupling
    "CIRCULATES_TO":     0.75,   # Catalyst circulation — high coupling
    "UPSTREAM_OF":       0.65,   # Generic upstream — moderate-high coupling
    "IMPACTS":           0.60,   # Explicit impact relationship
    "DEPENDS_ON":        0.50,   # Functional dependency — moderate coupling
    "CONNECTS":          0.40,   # Physical connection — lower coupling
    "SHUTS_DOWN":        0.95,   # ESD shutdown — near-total coupling
}

# Hop decay factor — downtime multiplied by this per additional hop
HOP_DECAY: float = 0.70

# Criticality amplifier — high-criticality assets amplify propagated downtime
CRITICALITY_AMPLIFIER: dict[int, float] = {
    5: 1.20,   # Critical asset — amplifies impact
    4: 1.05,   # High criticality — slight amplification
    3: 0.90,   # Medium criticality — slight reduction
    2: 0.75,   # Low criticality
    1: 0.60,   # Minimal criticality
}


@dataclass
class PropagatedDowntime:
    """Downtime estimate for a single asset in the propagation tree."""
    asset_id:          str
    asset_name:        str
    equipment_type:    str
    criticality:       int
    hop_distance:      int
    propagated_hours:  float          # Estimated downtime hours at this asset
    confidence_low:    float          # Lower bound (80% CI)
    confidence_high:   float          # Upper bound (80% CI)
    coupling_factor:   float          # Combined coupling coefficient
    propagation_path:  list[str]      # Asset IDs from source to this node
    relationship_chain: list[str]     # Relationship types along the path
    flow_types:        list[str]      # Flow type labels along the path
    area:              Optional[str]  # Plant area
    active_moc_count:  int            # Number of active MoCs on this asset
    risk_level:        str            # Low / Medium / High / Critical


@dataclass
class PropagationResult:
    """Full result of a downtime propagation analysis."""
    source_asset_id:   str
    source_asset_name: str
    source_downtime:   float          # Input downtime at the source asset (hours)
    total_affected:    int            # Number of assets with propagated downtime
    total_propagated_hours: float     # Sum of all propagated downtime hours
    affected_assets:   list[PropagatedDowntime] = field(default_factory=list)
    summary:           str = ""       # Human-readable summary


class DowntimePropagator:
    """
    Propagates downtime estimates across the FCC Unit process topology.

    Usage:
        propagator = DowntimePropagator()
        result = propagator.propagate("P-101", source_downtime_hours=24.0)
        for asset in result.affected_assets:
            print(f"{asset.asset_id}: {asset.propagated_hours:.1f}h")
    """

    def __init__(self, neo4j_client: Neo4jClient = None):
        self.neo4j = neo4j_client or Neo4jClient()

    def propagate(
        self,
        source_asset_id: str,
        source_downtime_hours: float,
        max_depth: int = 4,
        min_propagated_hours: float = 0.5,
    ) -> PropagationResult:
        """
        Propagate downtime from a source asset through the process topology.

        Args:
            source_asset_id:       The asset that is going offline.
            source_downtime_hours: Estimated downtime at the source (hours).
            max_depth:             Maximum hop depth to traverse (default 4).
            min_propagated_hours:  Minimum threshold — assets below this are excluded.

        Returns:
            PropagationResult with all affected assets ranked by propagated downtime.
        """
        # Fetch enriched impact chain from Neo4j
        chain = self.neo4j.get_enriched_impact_chain(source_asset_id, depth=max_depth)

        # Fetch source asset info
        source_info = self._get_asset_info(source_asset_id)
        source_name = source_info.get("name", source_asset_id) if source_info else source_asset_id

        affected: list[PropagatedDowntime] = []

        for node in chain:
            asset_id   = node.get("node_id", "")
            asset_name = node.get("node_name", "")
            eq_type    = node.get("node_type", "")
            criticality = int(node.get("criticality") or 3)
            hops       = int(node.get("hop_distance") or 1)
            rel_chain  = node.get("relationship_chain") or []
            flow_types = node.get("flow_types") or []
            area       = node.get("area")
            moc_count  = int(node.get("active_moc_count") or 0)

            if not asset_id or asset_id == source_asset_id:
                continue

            # Compute coupling factor from relationship chain
            coupling = self._compute_coupling(rel_chain, hops)

            # Apply criticality amplifier
            crit_amp = CRITICALITY_AMPLIFIER.get(criticality, 0.90)

            # Propagated downtime
            propagated = source_downtime_hours * coupling * crit_amp

            if propagated < min_propagated_hours:
                continue

            # Confidence interval (±30% for direct, ±50% for indirect)
            ci_mult = 0.30 if hops == 1 else 0.50
            ci_low  = round(max(0.0, propagated * (1 - ci_mult)), 1)
            ci_high = round(propagated * (1 + ci_mult), 1)

            # Risk level based on propagated hours
            risk_level = self._classify_risk(propagated, criticality)

            # Build propagation path
            path_nodes = [source_asset_id] + (
                node.get("relationship_chain") and
                [asset_id] or [asset_id]
            )

            affected.append(PropagatedDowntime(
                asset_id=asset_id,
                asset_name=asset_name,
                equipment_type=eq_type,
                criticality=criticality,
                hop_distance=hops,
                propagated_hours=round(propagated, 1),
                confidence_low=ci_low,
                confidence_high=ci_high,
                coupling_factor=round(coupling, 3),
                propagation_path=[source_asset_id, asset_id],
                relationship_chain=rel_chain,
                flow_types=[ft for ft in flow_types if ft],
                area=area,
                active_moc_count=moc_count,
                risk_level=risk_level,
            ))

        # Sort by propagated hours descending
        affected.sort(key=lambda x: x.propagated_hours, reverse=True)

        total_hours = sum(a.propagated_hours for a in affected)
        summary = self._build_summary(
            source_asset_id, source_name, source_downtime_hours, affected
        )

        return PropagationResult(
            source_asset_id=source_asset_id,
            source_asset_name=source_name,
            source_downtime=source_downtime_hours,
            total_affected=len(affected),
            total_propagated_hours=round(total_hours, 1),
            affected_assets=affected,
            summary=summary,
        )

    def propagate_from_moc(self, moc_id: str) -> PropagationResult | None:
        """
        Convenience method: propagate downtime from a MoC's target asset
        using the MoC's actual downtime (manhours) as the source.
        """
        detail = self.neo4j.get_moc_full_detail(moc_id)
        if not detail:
            return None
        asset_id = detail.get("asset_id")
        downtime = float(detail.get("actual_manhours") or
                         detail.get("estimated_manhours") or 24.0)
        if not asset_id:
            return None
        return self.propagate(asset_id, downtime)

    def get_propagation_matrix(self) -> list[dict]:
        """
        Computes a propagation matrix for all high-criticality assets (criticality ≥ 4).
        Returns a list of dicts with source asset, top affected asset, and max propagated hours.
        Useful for risk overview dashboards.
        """
        assets = self.neo4j.get_all_assets_with_connectivity()
        high_crit = [a for a in assets if int(a.get("criticality") or 0) >= 4]

        matrix = []
        for asset in high_crit:
            aid = asset.get("asset_id", "")
            if not aid:
                continue
            # Use a representative downtime of 24h for comparison
            result = self.propagate(aid, source_downtime_hours=24.0, max_depth=3)
            top = result.affected_assets[0] if result.affected_assets else None
            matrix.append({
                "source_asset_id":   aid,
                "source_name":       asset.get("name", ""),
                "criticality":       asset.get("criticality"),
                "total_affected":    result.total_affected,
                "total_propagated_hours": result.total_propagated_hours,
                "top_affected_asset": top.asset_id if top else None,
                "top_affected_hours": top.propagated_hours if top else 0.0,
                "top_affected_risk":  top.risk_level if top else "Low",
            })

        matrix.sort(key=lambda x: x["total_propagated_hours"], reverse=True)
        return matrix

    # ── Private helpers ────────────────────────────────────────────────────

    def _compute_coupling(self, rel_chain: list[str], hops: int) -> float:
        """
        Compute the combined coupling factor for a relationship chain.
        Each hop applies the coupling coefficient and the hop decay.
        """
        if not rel_chain:
            return HOP_DECAY ** hops

        coupling = 1.0
        for i, rel in enumerate(rel_chain):
            coeff = COUPLING_COEFFICIENTS.get(rel, 0.40)
            decay = HOP_DECAY ** i  # Decay increases with each hop
            coupling *= coeff * decay

        return min(coupling, 0.95)  # Cap at 95%

    def _classify_risk(self, propagated_hours: float, criticality: int) -> str:
        """Classify propagated downtime risk level."""
        score = propagated_hours * criticality
        if score >= 200:
            return "Critical"
        elif score >= 80:
            return "High"
        elif score >= 30:
            return "Medium"
        else:
            return "Low"

    def _get_asset_info(self, asset_id: str) -> dict | None:
        """Fetch basic asset info."""
        results = self.neo4j._run(
            "MATCH (a:Asset {asset_id: $id}) "
            "RETURN a.asset_id AS asset_id, a.name AS name, "
            "a.equipment_type AS equipment_type, a.criticality AS criticality",
            {"id": asset_id}
        )
        return results[0] if results else None

    def _build_summary(
        self,
        source_id: str,
        source_name: str,
        source_hours: float,
        affected: list[PropagatedDowntime],
    ) -> str:
        """Build a human-readable summary of the propagation result."""
        if not affected:
            return (
                f"Downtime at {source_id} ({source_name}) of {source_hours:.0f}h "
                f"has no significant propagation to downstream assets."
            )

        critical = [a for a in affected if a.risk_level in ("Critical", "High")]
        top = affected[0]
        lines = [
            f"Downtime propagation from {source_id} ({source_name}) — "
            f"source: {source_hours:.0f}h:",
            f"  • {len(affected)} downstream assets affected",
            f"  • {len(critical)} assets at High/Critical risk",
            f"  • Highest impact: {top.asset_id} ({top.asset_name}) "
            f"— {top.propagated_hours:.1f}h propagated "
            f"({top.hop_distance} hop, {top.risk_level} risk)",
        ]
        if len(affected) > 1:
            lines.append(
                f"  • Total propagated downtime across all assets: "
                f"{sum(a.propagated_hours for a in affected):.1f}h"
            )
        return "\n".join(lines)


def propagation_result_to_dict(result: PropagationResult) -> dict:
    """Serialise a PropagationResult to a JSON-safe dict for API responses."""
    return {
        "source_asset_id":        result.source_asset_id,
        "source_asset_name":      result.source_asset_name,
        "source_downtime":        result.source_downtime,
        "total_affected":         result.total_affected,
        "total_propagated_hours": result.total_propagated_hours,
        "summary":                result.summary,
        "affected_assets": [
            {
                "asset_id":          a.asset_id,
                "asset_name":        a.asset_name,
                "equipment_type":    a.equipment_type,
                "criticality":       a.criticality,
                "hop_distance":      a.hop_distance,
                "propagated_hours":  a.propagated_hours,
                "confidence_low":    a.confidence_low,
                "confidence_high":   a.confidence_high,
                "coupling_factor":   a.coupling_factor,
                "propagation_path":  a.propagation_path,
                "relationship_chain": a.relationship_chain,
                "flow_types":        a.flow_types,
                "area":              a.area,
                "active_moc_count":  a.active_moc_count,
                "risk_level":        a.risk_level,
            }
            for a in result.affected_assets
        ],
    }
