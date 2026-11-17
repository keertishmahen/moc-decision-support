/**
 * Frosted top bar: where you are, live service status, theme toggle, and the menu button
 * that opens the navigation drawer on small screens.
 */
import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Menu, RefreshCw } from 'lucide-react'
import { getHealth } from '../../api'
import { cssVar } from '../../theme/palette'
import ThemeToggle from '../ThemeToggle'
import type { Page } from '../../nav'

type ServiceInfo = { ok: boolean; message: string }

/** Shared with the Overview page through the same query key. */
export const useHealth = () =>
  useQuery<{ neo4j?: ServiceInfo; openai?: ServiceInfo }>({ queryKey: ['health'], queryFn: getHealth, refetchInterval: 30_000 })

export function ServicePill({ name, info, failed }: { name: string; info?: ServiceInfo; failed: boolean }) {
  // A failed health request means the backend itself is down or waking up, not the service.
  const ok = !failed && !!info?.ok
  const message = failed ? 'Backend unreachable: it may be waking up' : (info?.message ?? 'Checking…')
  const tone = ok ? 'ok' : failed || info ? 'danger' : 'slate'
  return (
    <span title={`${name}: ${message}`}
      className="moc-status-row inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold text-white/75">
      <span className="h-2 w-2 rounded-full" style={{ background: cssVar(tone), boxShadow: `0 0 6px ${cssVar(tone)}` }} aria-hidden />
      {name}
      <span className="sr-only">{ok ? 'connected' : message}</span>
    </span>
  )
}

export default function TopBar({ page, onMenu }: { page: Page; onMenu: () => void }) {
  const health = useHealth()
  return (
    <header className="moc-topbar glass-strong sticky top-0 z-30 flex items-center gap-3 px-4 py-3 sm:px-6">
      <button type="button" onClick={onMenu} aria-label="Open navigation"
        className="glass-tile h-9 w-9 text-white/70 hover:text-white lg:hidden">
        <Menu className="h-4 w-4" strokeWidth={1.75} />
      </button>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5 text-[11px] text-white/40">
          <span>{page.group}</span>
          <span aria-hidden>/</span>
          <span className="font-semibold text-white/80">{page.label}</span>
        </div>
        <div className="hidden truncate text-xs text-white/50 sm:block">{page.description}</div>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden items-center gap-2 md:flex">
          <ServicePill name="Neo4j" info={health.data?.neo4j} failed={health.isError} />
          <ServicePill name="OpenAI" info={health.data?.openai} failed={health.isError} />
        </div>
        <button type="button" onClick={() => health.refetch()} aria-label="Refresh service status" title="Refresh service status"
          className="glass-tile h-9 w-9 text-white/60 hover:text-white">
          <RefreshCw className={`h-4 w-4 ${health.isFetching ? 'animate-spin' : ''}`} strokeWidth={1.75} />
        </button>
        <ThemeToggle />
      </div>
    </header>
  )
}
