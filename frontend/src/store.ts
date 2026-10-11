import { create } from 'zustand'

export interface ChatMessage { role: 'user' | 'assistant'; content: string; intent?: string }

interface AppStore {
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
