import React, { Suspense, useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useStore } from './store'
import { ONBOARDING_STORAGE_KEY } from './onboardingContent'
import {
  currentPath,
  navigate,
  parsePath,
  pathForTab,
  pathOnboarding,
  replace,
  tabIndex,
  PATH_LANDING,
} from './navigation'
import { PAGES } from './nav'
import Onboarding from './components/Onboarding'
import Sidebar from './components/shell/Sidebar'
import TopBar from './components/shell/TopBar'
import { Spinner } from './components/ui'

const COLLAPSED_KEY = 'moc-sidebar-collapsed'

function readFlag(key: string) {
  try {
    return localStorage.getItem(key) === '1'
  } catch {
    return false
  }
}

function writeFlag(key: string, value: boolean) {
  try {
    localStorage.setItem(key, value ? '1' : '0')
  } catch { /* storage unavailable: the choice lasts for this visit only */ }
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
  const [showOnboarding, setShowOnboarding] = useState(true)
  const [collapsed, setCollapsed] = useState(() => readFlag(COLLAPSED_KEY))
  const [drawerOpen, setDrawerOpen] = useState(false)

  const page = PAGES[activeTab] ?? PAGES[0]
  const PageComponent = page.component

  const syncFromLocation = useCallback(() => {
    applyRoute(currentPath(), readFlag(ONBOARDING_STORAGE_KEY), setShowOnboarding, setActiveTab)
  }, [setActiveTab])

  // Every fresh load opens onboarding; Enter Platform / navigation / Back–Forward update history after that
  useEffect(() => {
    replace(pathOnboarding())
    setShowOnboarding(true)

    window.addEventListener('popstate', syncFromLocation)
    return () => window.removeEventListener('popstate', syncFromLocation)
  }, [syncFromLocation])

  // Esc closes the navigation drawer on small screens.
  useEffect(() => {
    if (!drawerOpen) return
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setDrawerOpen(false) }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [drawerOpen])

  const enterPlatform = () => {
    writeFlag(ONBOARDING_STORAGE_KEY, true)
    setActiveTab(tabIndex(PATH_LANDING))
    setShowOnboarding(false)
    navigate(PATH_LANDING)
  }

  const reopenAbout = () => {
    setDrawerOpen(false)
    setShowOnboarding(true)
    navigate(pathOnboarding())
  }

  const goToTab = (i: number) => {
    setActiveTab(i)
    setDrawerOpen(false)
    navigate(pathForTab(i))
    window.scrollTo({ top: 0 })
  }

  const toggleCollapsed = () => {
    setCollapsed(c => {
      writeFlag(COLLAPSED_KEY, !c)
      return !c
    })
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
        // Opacity only: a transform here would turn the fixed drawer and orbs into
        // absolutely positioned boxes. No overflow container either, so sticky works.
        <motion.div
          key="dashboard"
          className="moc-dash-root relative flex min-h-screen overflow-clip"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.35 }}
        >
          <div className="moc-dash-orb moc-dash-orb-a" aria-hidden />
          <div className="moc-dash-orb moc-dash-orb-b" aria-hidden />
          <div className="moc-dash-grid fixed inset-0 z-0" aria-hidden />
          <div className="moc-dash-vignette" aria-hidden />

          {drawerOpen && (
            <div className="moc-drawer-overlay fixed inset-0 z-40 lg:hidden" onClick={() => setDrawerOpen(false)} aria-hidden />
          )}

          <Sidebar
            active={activeTab}
            onSelect={goToTab}
            collapsed={collapsed}
            onToggleCollapsed={toggleCollapsed}
            mobileOpen={drawerOpen}
            onCloseMobile={() => setDrawerOpen(false)}
            onAbout={reopenAbout}
          />

          <div className="moc-shell-main relative z-10 flex min-w-0 flex-1 flex-col">
            <TopBar page={page} onMenu={() => setDrawerOpen(true)} />

            <main className="moc-main-scroll min-w-0 flex-1 px-4 py-5 sm:px-6">
              <AnimatePresence mode="wait">
                <motion.div
                  key={page.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.22 }}
                >
                  <Suspense fallback={<Spinner text={`Loading ${page.label}…`} />}>
                    <PageComponent />
                  </Suspense>
                </motion.div>
              </AnimatePresence>
            </main>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
