/**
 * Decision allocation (Human-AI) — typed client for /api/allocation/*.
 *
 * The model (axes, weights, thresholds, rule) is never restated in the frontend:
 * it is fetched from GET /api/allocation/model and every score comes from the backend engine.
 */
import { api } from '../api'

export type AllocationCode = 'AI_LED' | 'AI_SUPPORTED' | 'HUMAN_LED'
export type LevelCode = 'LOW' | 'MED' | 'HIGH'
export type FactorCode = 'I' | 'II' | 'III'
export type AxisSelection = Record<string, string>

export interface AllocationModel {
  model_id: string
  version: string
  title: string
  space_size: number
  attribution: Record<string, string>
  dimensions: {
    id: string; name: string; definition: string; max: number
    low: number; high: number; low_boundary: number; high_boundary: number
  }[]
  axes: {
    id: string; name: string; hint: string
    categories: { id: string; name: string; weights: Record<string, number> }[]
  }[]
  factor_matrix: Record<LevelCode, Record<LevelCode, FactorCode>>
  allocation_rule: { id: string; text: string }
}

export interface AllocationDimension {
  id: string; name: string; score: number; max: number; normalised: number; level: LevelCode
  low_boundary: number; high_boundary: number; margin: number
  contributions: { axis_id: string; axis: string; category_id: string; category: string; weight: number }[]
}

export interface AllocationFactor {
  dimension_id: string; dimension: string; level: LevelCode; impact_level: LevelCode; factor: FactorCode
}

export interface AllocationFlip {
  axis_id: string; axis: string; from: string; to: string; to_name: string
  allocation: AllocationCode; allocation_label: string
}

export interface AllocationResult {
  model_version: string
  selection: AxisSelection
  scores: Record<string, number>
  levels: Record<string, LevelCode>
  dimensions: AllocationDimension[]
  factors: AllocationFactor[]
  signature: string
  allocation: AllocationCode
  allocation_label: string
  escalated_by: string[]
  reasons: string[]
  flips: AllocationFlip[]
}

export interface AxisSuggestion {
  value: string; name: string; source: string
  confidence: 'high' | 'medium' | 'low'; evidence: string; needs_confirmation: boolean
}

export interface AxisAssessment {
  axis_id: string; axis: string; hint: string; selected: string; selected_name: string
  suggested: AxisSuggestion | null
  reference: { value: string; name: string; status: string | null; source: string | null } | null
  agrees: boolean | null
}

export interface ImpactAssessment {
  asset: {
    asset_id: string | null; equipment_type: string | null; criticality: number | null
    areas: string[]; esd_target: boolean
  }
  reach: {
    available: boolean; assets_affected: number | null; areas_reached: string[]
    critical_assets: string[]; direct: string[]
    assets: { asset_id: string; equipment_type: string | null; criticality: number | null; hops: number; area: string | null }[]
  }
  safety: { hazop_required: boolean | null; pssr_required: boolean | null; shutdown_required: boolean | null }
  risk_assessment: { category: string | null; overall_score: number | null; likelihood: number | null } | null
  parameter: { old: string | null; new: string | null; threshold: string | null } | null
  documents: { pid_refs: string[] }
  history: {
    mocs_on_asset: string[]; incidents_on_asset: number | null
    incidents_on_moc: number | null; work_types: string[] | null
  }
}

export interface AllocationAssessment {
  subject: {
    kind: 'moc' | 'proposed'; moc_id: string | null; title: string; case_id: string | null
    asset_id: string | null; change_type: string | null; description: string | null
  }
  impact_assessment: ImpactAssessment | null
  axes: AxisAssessment[]
  selection: AxisSelection
  characterisation_status: string
  result: AllocationResult
  graph_status: 'ok' | 'unavailable'
}

export interface ReferenceCaseRow {
  case_id: string; moc_id: string; title: string; selection: AxisSelection; status: string; alternatives: string
  expected: { scores: Record<string, number>; levels: Record<string, LevelCode>; signature: string; allocation: AllocationCode }
  computed: { scores: Record<string, number>; levels: Record<string, LevelCode>; signature: string; allocation: AllocationCode }
  allocation_label: string; matches: boolean; differences: string[]
  rule_agreement: { agreeing_axes: number; differing_axes: string[] } | null
}

export interface ReferenceCases {
  source: string; reconstruction_note: string; cases: ReferenceCaseRow[]
  reproduced: number; total: number; graph_status: 'ok' | 'unavailable'; model_version: string
}

export interface AllocationMocRow {
  moc_id: string; title: string | null; change_type: string | null; asset_id: string | null
  allocation: AllocationCode | null; allocation_label: string | null; signature: string | null
}

export interface AllocationEnumeration {
  total: number
  allocations: Record<AllocationCode, number>
  shares: Record<AllocationCode, number>
  signatures_reached: number; signatures_possible: number; signatures_unreached: string[]
}

export const getAllocationModel = () => api.get<AllocationModel>('/allocation/model').then(r => r.data)

export const getAllocationCases = () => api.get<ReferenceCases>('/allocation/cases').then(r => r.data)

export const getAllocationMocs = () =>
  api.get<{ mocs: AllocationMocRow[]; graph_status: string }>('/allocation/mocs').then(r => r.data)

export const getAllocationEnumeration = () =>
  api.get<AllocationEnumeration>('/allocation/analysis/enumeration').then(r => r.data)

export const assessMocAllocation = (mocId: string) =>
  api.get<AllocationAssessment>(`/allocation/moc/${encodeURIComponent(mocId)}`).then(r => r.data)

export const assessChangeAllocation = (body: {
  change_type: string; asset_id: string; description: string
  hazop_required?: boolean | null; pssr_required?: boolean | null; shutdown_required?: boolean | null
}) => api.post<AllocationAssessment>('/allocation/assess', body).then(r => r.data)

export const scoreAllocation = (selection: AxisSelection) =>
  api.post<AllocationResult>('/allocation/score', { selection }).then(r => r.data)
