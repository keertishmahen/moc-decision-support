/** Path-based navigation via History API (no react-router). */

export const PATH_ONBOARDING = '/'
export const PATH_APP_ROOT = '/app'
export const PATH_SMART_FORM = '/app/smart-form'

export const TAB_PATHS = [
  '/app/smart-form',
  '/app/risk',
  '/app/cost',
  '/app/mocbot',
  '/app/process',
] as const

export type AppRoute =
  | { view: 'onboarding'; tab: number }
  | { view: 'app'; tab: number }

export function pathOnboarding() {
  return PATH_ONBOARDING
}

export function pathForTab(tab: number) {
  const i = Math.max(0, Math.min(TAB_PATHS.length - 1, tab))
  return TAB_PATHS[i]
}

export function parsePath(pathname: string, onboardingSeen: boolean): AppRoute {
  const path = (pathname.replace(/\/+$/, '') || '/') as string

  if (path === '/' || path === '') {
    return { view: 'onboarding', tab: 0 }
  }

  if (path === PATH_APP_ROOT) {
    return { view: 'app', tab: 0 }
  }

  const tabIdx = TAB_PATHS.indexOf(path as (typeof TAB_PATHS)[number])
  if (tabIdx >= 0) {
    return { view: 'app', tab: tabIdx }
  }

  // Unknown → onboarding (app opens to onboarding by default)
  return { view: 'onboarding', tab: 0 }
}

/** Canonical path for a route (normalizes /app → smart-form). */
export function pathForRoute(route: AppRoute): string {
  if (route.view === 'onboarding') return PATH_ONBOARDING
  return pathForTab(route.tab)
}

export function navigate(path: string) {
  const current = window.location.pathname.replace(/\/+$/, '') || '/'
  const next = path.replace(/\/+$/, '') || '/'
  if (current === next) return
  window.history.pushState({ moc: true }, '', next)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function replace(path: string) {
  const next = path.replace(/\/+$/, '') || '/'
  window.history.replaceState({ moc: true }, '', next)
}

/**
 * Resolve path on load:
 * - / and unknown non-app paths → onboarding
 * - /app → /app/smart-form
 * - /app/* tab paths stay as-is
 */
export function resolveInitialPath(pathname: string, _onboardingSeen: boolean): string {
  const path = pathname.replace(/\/+$/, '') || '/'

  if (path === PATH_APP_ROOT) return PATH_SMART_FORM

  const tabIdx = TAB_PATHS.indexOf(path as (typeof TAB_PATHS)[number])
  if (tabIdx >= 0) return TAB_PATHS[tabIdx]

  return PATH_ONBOARDING
}
