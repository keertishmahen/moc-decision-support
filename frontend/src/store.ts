import { create } from 'zustand'

export interface ChatMessage { role: 'user' | 'assistant'; content: string; intent?: string }

/** The change being assessed, shared by Smart Form, Risk, Cost and Decision Allocation. */
export interface CurrentChange {
  changeType: string
  assetId: string
  description: string
  hazopRequired: boolean | null
  pssrRequired: boolean | null
}

interface AppStore {
  // Change under assessment
  currentChange: CurrentChange
  setCurrentChange: (patch: Partial<CurrentChange>) => void
  // Set by another tab to open Decision Allocation on the proposed change
  allocationIntent: 'proposed' | null
  setAllocationIntent: (intent: 'proposed' | null) => void
  // Chat
  messages: ChatMessage[]
  addMessage: (m: ChatMessage) => void
  clearMessages: () => void
  // Graph context
  graphContext: Record<string, unknown> | null
  lastQuery: string
  setGraphContext: (ctx: Record<string, unknown>, query: string) => void
  // Active tab
  activeTab: number
  setActiveTab: (t: number) => void
}

export const useStore = create<AppStore>(set => ({
  currentChange: { changeType: 'Mechanical', assetId: 'P-101', description: '', hazopRequired: null, pssrRequired: null },
  setCurrentChange: patch => set(s => ({ currentChange: { ...s.currentChange, ...patch } })),
  allocationIntent: null,
  setAllocationIntent: intent => set({ allocationIntent: intent }),
  messages: [{
    role: 'assistant',
    content: 'Welcome to MoCBot. I have direct access to the FCC Unit knowledge graph — 10 MoC records, 14+ assets, risk assessments, HAZOP/PSSR, work orders, and lessons learned. Ask me anything specific.',
  }],
  addMessage: m => set(s => ({ messages: [...s.messages, m] })),
  clearMessages: () => set({ messages: [] }),
  graphContext: null,
  lastQuery: '',
  setGraphContext: (ctx, query) => set({ graphContext: ctx, lastQuery: query }),
  activeTab: 0,
  setActiveTab: t => set({ activeTab: t }),
}))
