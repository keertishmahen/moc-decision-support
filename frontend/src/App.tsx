import React, { useCallback, useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bot,
  CircleDollarSign,
  ClipboardList,
  GitBranch,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react'
import { getHealth } from './api'
import { useStore } from './store'
import { ONBOARDING_STORAGE_KEY } from './onboardingContent'
import {
  navigate,
  parsePath,
  pathForTab,
  pathOnboarding,
  replace,
  PATH_SMART_FORM,
} from './navigation'
import Onboarding from './components/Onboarding'
import BrandMark from './components/BrandMark'
import SmartForm    from './tabs/SmartForm'
import RiskAnalysis from './tabs/RiskAnalysis'
import CostPredictor from './tabs/CostPredictor'
import MoCBot       from './tabs/MoCBot'
import ProcessIntelligence from './tabs/ProcessIntelligence'

const TABS: { icon: LucideIcon; label: string }[] = [
  { icon: ClipboardList, label: 'Smart Form' },
  { icon: TriangleAlert, label: 'Risk & Impact' },
  { icon: CircleDollarSign, label: 'Cost Predictor' },
  { icon: Bot, label: 'MoCBot' },
  { icon: GitBranch, label: 'Process Intelligence' },
]

const DATASET = [
  { label: 'MoC Records', value: '10' },
  { label: 'Assets', value: '14+' },
  { label: 'Work Orders', value: '21' },
  { label: 'Incidents', value: '4' },
]

const STACK = ['Neo4j Knowledge Graph', 'GPT-4o · LangChain', 'ChromaDB · OpenAI Embeddings', 'GradientBoosting ML']

function readOnboardingSeen() {
  try {
    return localStorage.getItem(ONBOARDING_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function applyRoute(
  pathname: string,
  seen: boolean,
  setShowOnboarding: (v: boolean) => void,
  setActiveTab: (t: number) => void,
) {
  const route = parsePath(pathname, seen)
  setShowOnboarding(route.view === 'onboarding')
  if (route.view === 'app') setActiveTab(route.tab)
}

export default function App() {
  const { activeTab, setActiveTab } = useStore()
  const { data: health, refetch } = useQuery({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 30_000 })
  const [showOnboarding, setShowOnboarding] = useState(true)

  const panels = [<SmartForm />, <RiskAnalysis />, <CostPredictor />, <MoCBot />, <ProcessIntelligence />]

  const syncFromLocation = useCallback(() => {
    const seen = readOnboardingSeen()
    applyRoute(window.location.pathname, seen, setShowOnboarding, setActiveTab)
  }, [setActiveTab])

  // Every fresh load opens onboarding; Enter Platform / tabs / Back–Forward update history after that
  useEffect(() => {
    replace(pathOnboarding())
    setShowOnboarding(true)

    window.addEventListener('popstate', syncFromLocation)
    return () => window.removeEventListener('popstate', syncFromLocation)
  }, [syncFromLocation])

  const enterPlatform = () => {
    try {
      localStorage.setItem(ONBOARDING_STORAGE_KEY, '1')
    } catch { /* ignore */ }
    setActiveTab(0)
    setShowOnboarding(false)
    navigate(PATH_SMART_FORM)
  }

  const reopenAbout = () => {
    setShowOnboarding(true)
    navigate(pathOnboarding())
  }

  const goToTab = (i: number) => {
    setActiveTab(i)
    navigate(pathForTab(i))
  }

  return (
    <AnimatePresence mode="wait">
      {showOnboarding ? (
        <motion.div
          key="onboarding"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, y: -12 }}
          transition={{ duration: 0.35 }}
        >
          <Onboarding onEnter={enterPlatform} />
        </motion.div>
      ) : (
        <motion.div
          key="dashboard"
          className="moc-dash-root moc-dash-mesh relative flex min-h-screen overflow-hidden"
          style={{ fontFamily: 'Outfit, Inter, sans-serif' }}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div className="moc-dash-orb moc-dash-orb-a" aria-hidden />
          <div className="moc-dash-orb moc-dash-orb-b" aria-hidden />
          <div className="moc-dash-grid absolute inset-0 z-0" aria-hidden />
          <div className="moc-dash-vignette" aria-hidden />

          {/* ── Sidebar ── */}
          <aside className="moc-sidebar relative z-10 w-56 flex-shrink-0 flex flex-col p-4 gap-4">
            <div className="pt-1">
              <div className="flex items-center gap-2.5">
                <BrandMark size={32} />
                <div>
                  <div className="text-[15px] font-semibold text-white tracking-tight">MoC Platform</div>
                  <div className="text-[10px] text-white/40 mt-0.5">FCC Unit · AI Decision Support</div>
                </div>
              </div>
              <button
                type="button"
                onClick={reopenAbout}
                className="mt-3 text-[11px] font-medium text-[#4f8ef7] hover:text-blue-300 transition-colors"
              >
                About
              </button>
            </div>

            <div className="moc-sidebar-panel p-3">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-white/40 mb-2">System Status</div>
              <button onClick={() => refetch()} className="text-[11px] text-[#4f8ef7] hover:text-blue-300 mb-2 transition-colors">↺ Refresh</button>
              {(['neo4j','openai'] as const).map(svc => {
                const info = health?.[svc]
                const ok = info?.ok ?? false
                return (
                  <div key={svc} className="moc-status-row flex items-center gap-2 p-2 rounded-xl mb-1.5 last:mb-0">
                    <span className={`w-2 h-2 rounded-full flex-shrink-0 ${ok ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]' : 'bg-red-400 shadow-[0_0_6px_#f87171]'}`} />
                    <span className="text-[11px] font-semibold text-white/80 w-12">{svc === 'neo4j' ? 'Neo4j' : 'OpenAI'}</span>
                    <span className="text-[10px] text-white/40 truncate">{info?.message ?? '…'}</span>
                  </div>
                )
              })}
            </div>

            <div className="moc-sidebar-panel p-3">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-white/40 mb-2">Tech Stack</div>
              {STACK.map(s => (
                <div key={s} className="text-[11px] text-white/60 py-1.5 border-b border-white/5 last:border-0">▸ {s}</div>
              ))}
            </div>

            <div className="moc-sidebar-panel p-3">
              <div className="text-[10px] font-semibold uppercase tracking-widest text-white/40 mb-2">Dataset</div>
              {DATASET.map(d => (
                <div key={d.label} className="flex justify-between py-1.5 border-b border-white/5 last:border-0">
                  <span className="text-[11px] text-white/50">{d.label}</span>
                  <span className="text-[11px] font-bold text-[#4f8ef7]">{d.value}</span>
                </div>
              ))}
            </div>
          </aside>

          {/* ── Main ── */}
          <div className="relative z-10 flex-1 flex flex-col min-w-0">
            <div className="moc-hero-bar relative overflow-hidden px-6 py-5">
              <div className="shimmer absolute inset-0 pointer-events-none" />
              <div className="relative">
                <h1 className="text-xl font-semibold text-white tracking-tight">MoC Intelligence Platform</h1>
                <p className="text-sm text-white/50 mt-1">Hybrid Neo4j + ChromaDB retrieval · GPT-4o reasoning · Engineering-grade decision support</p>
                <div className="flex flex-wrap gap-2 mt-3">
                  {['Live Graph', 'RAG Pipeline', 'ML Prediction', 'Vector Search'].map(b => (
                    <span key={b} className="moc-chip px-2.5 py-0.5 rounded-full text-[11px] font-semibold text-[#93c5fd]">{b}</span>
                  ))}
                </div>
              </div>
            </div>

            <div className="px-6 pt-4 pb-0">
              <div className="moc-tab-rail flex flex-wrap">
                {TABS.map((t, i) => {
                  const Icon = t.icon
                  return (
                  <button
                    key={i}
                    type="button"
                    onClick={() => goToTab(i)}
                    className={`moc-tab inline-flex items-center gap-2 px-4 py-2 text-sm font-medium ${
                      activeTab === i ? 'moc-tab-active' : 'moc-tab-idle'
                    }`}
                  >
                    <Icon className="h-4 w-4 shrink-0" strokeWidth={1.75} />
                    {t.label}
                  </button>
                  )
                })}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.22 }}
                >
                  {panels[activeTab]}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
