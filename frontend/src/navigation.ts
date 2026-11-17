/** Hash-based navigation (#/app/...) via History API (no react-router). Hash routes work under any base path, e.g. GitHub Pages. */

export const PATH_ONBOARDING = '/'
export const PATH_APP_ROOT = '/app'
import { PAGES } from './nav'

export const PATH_OVERVIEW = '/app/overview'
export const PATH_CHANGE_CASE = '/app/case'
/** Where "Enter Platform" lands: the Overview home page. */
export const PATH_LANDING = PATH_OVERVIEW

/** Route of each page, in navigation order (from nav.ts). */
export const TAB_PATHS: string[] = PAGES.map(p => p.path)

/** Index of a page by its path, for setActiveTab. */
export const tabIndex = (path: string) => Math.max(0, TAB_PATHS.indexOf(path))

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

  const tabIdx = TAB_PATHS.indexOf(path)
  if (tabIdx >= 0) {
    return { view: 'app', tab: tabIdx }
  }

  // Unknown -> onboarding (app opens to onboarding by default)
  return { view: 'onboarding', tab: 0 }
}

/** Canonical path for a route (normalizes /app -> the landing tab). */
export function pathForRoute(route: AppRoute): string {
  if (route.view === 'onboarding') return PATH_ONBOARDING
  return pathForTab(route.tab)
}

/** Current route path, read from the URL hash ("#/app/risk" -> "/app/risk"). */
export function currentPath(): string {
  return window.location.hash.replace(/^#/, '') || '/'
}

export function navigate(path: string) {
  const current = currentPath().replace(/\/+$/, '') || '/'
  const next = path.replace(/\/+$/, '') || '/'
  if (current === next) return
  window.history.pushState({ moc: true }, '', `#${next}`)
  window.dispatchEvent(new PopStateEvent('popstate'))
}

export function replace(path: string) {
  const next = path.replace(/\/+$/, '') || '/'
  window.history.replaceState({ moc: true }, '', `#${next}`)
}

/**
 * Resolve path on load:
 * - / and unknown non-app paths -> onboarding
 * - /app -> the landing tab
 * - /app/* tab paths stay as-is
 */
export function resolveInitialPath(pathname: string, _onboardingSeen: boolean): string {
  const path = pathname.replace(/\/+$/, '') || '/'

  if (path === PATH_APP_ROOT) return PATH_LANDING

  const tabIdx = TAB_PATHS.indexOf(path)
  if (tabIdx >= 0) return TAB_PATHS[tabIdx]

  return PATH_ONBOARDING
}
