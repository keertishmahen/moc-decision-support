/** Colours and labels shared by the decision-allocation views. */
import type { AllocationCode, FactorCode, LevelCode } from './api'

export const ALLOCATION_COLOR: Record<AllocationCode, string> = {
  AI_LED: '#34d399',
  AI_SUPPORTED: '#fbbf24',
  HUMAN_LED: '#f87171',
}

export const ALLOCATION_LABEL: Record<AllocationCode, string> = {
  AI_LED: 'AI-led',
  AI_SUPPORTED: 'AI-supported',
  HUMAN_LED: 'Human-led',
}

export const ALLOCATION_MEANING: Record<AllocationCode, string> = {
  AI_LED: 'AI may take the decision; a person oversees.',
  AI_SUPPORTED: 'AI prepares and recommends; a person decides.',
  HUMAN_LED: 'A person leads and decides; AI assists and challenges.',
}

export const FACTOR_COLOR: Record<FactorCode, string> = { I: '#34d399', II: '#fbbf24', III: '#f87171' }

export const LEVEL_COLOR: Record<LevelCode, string> = { LOW: '#34d399', MED: '#fbbf24', HIGH: '#f87171' }

export const LEVELS_TOP_DOWN: LevelCode[] = ['HIGH', 'MED', 'LOW']
export const LEVELS_LEFT_RIGHT: LevelCode[] = ['LOW', 'MED', 'HIGH']

export const SOURCE_LABEL: Record<string, string> = {
  'graph-rule': 'From the knowledge graph',
  default: 'Assumed — no data',
  description: 'Read from the description',
}

export const fmtScore = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1))
