/** Colour tokens and labels shared by the decision-allocation views (colours come from src/index.css). */
import type { Token } from '../theme/palette'
import type { AllocationCode, FactorCode, LevelCode } from './api'

export const ALLOCATION_TONE: Record<AllocationCode, Token> = {
  AI_LED: 'ok',
  AI_SUPPORTED: 'warn',
  HUMAN_LED: 'danger',
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

export const FACTOR_TONE: Record<FactorCode, Token> = { I: 'ok', II: 'warn', III: 'danger' }

export const LEVEL_TONE: Record<LevelCode, Token> = { LOW: 'ok', MED: 'warn', HIGH: 'danger' }

export const LEVELS_TOP_DOWN: LevelCode[] = ['HIGH', 'MED', 'LOW']
export const LEVELS_LEFT_RIGHT: LevelCode[] = ['LOW', 'MED', 'HIGH']

export const SOURCE_LABEL: Record<string, string> = {
  'graph-rule': 'From the knowledge graph',
  default: 'Assumed — no data',
  description: 'Read from the description',
}

export const fmtScore = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1))
