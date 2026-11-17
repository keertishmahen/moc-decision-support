/**
 * Frosted left navigation. Grouped pages from nav.ts; collapses to icons on large screens
 * and becomes an off-canvas drawer below the lg breakpoint.
 */
import React from 'react'
import { Info, PanelLeftClose, PanelLeftOpen, X } from 'lucide-react'
import SymmetraLogo from '../SymmetraLogo'
import { PAGE_GROUPS, PAGES } from '../../nav'

export default function Sidebar({ active, onSelect, collapsed, onToggleCollapsed, mobileOpen, onCloseMobile, onAbout }: {
  active: number
  onSelect: (index: number) => void
  collapsed: boolean
  onToggleCollapsed: () => void
  mobileOpen: boolean
  onCloseMobile: () => void
  onAbout: () => void
}) {
  // The drawer always shows labels; only the desktop sidebar collapses.
  const compact = collapsed && !mobileOpen
  return (
    <aside
      aria-label="Main navigation"
      className={`moc-shell-sidebar glass-strong fixed inset-y-0 left-0 z-50 flex w-64 flex-col transition-[width,transform] duration-300
        lg:sticky lg:top-0 lg:z-20 lg:h-screen lg:translate-x-0 ${compact ? 'lg:w-[78px]' : 'lg:w-60'}
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}
    >
      <div className={`flex items-center gap-2 px-4 pt-5 pb-4 ${compact ? 'lg:justify-center lg:px-2' : ''}`}>
        <div className="min-w-0 flex-1">
          <SymmetraLogo size={compact ? 34 : 30} wordmark={!compact} />
          {!compact && <div className="mt-1.5 truncate text-[10px] text-white/40">MoC Intelligence Platform · FCC Unit</div>}
        </div>
        <button type="button" onClick={onCloseMobile} aria-label="Close navigation"
          className="rounded-lg p-1.5 text-white/50 hover:text-white lg:hidden">
          <X className="h-5 w-5" strokeWidth={1.75} />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 pb-3">
        {PAGE_GROUPS.map(group => (
          <div key={group} className="mt-3 first:mt-0">
            {compact
              ? <div className="mx-auto my-2 h-px w-8 bg-white/10" aria-hidden />
              : <div className="px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-widest text-white/35">{group}</div>}
            <ul className="space-y-1">
              {PAGES.map((page, i) => page.group !== group ? null : (
                <li key={page.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(i)}
                    title={compact ? page.label : undefined}
                    aria-current={active === i ? 'page' : undefined}
                    className={`moc-nav-item flex w-full items-center gap-3 px-3 py-2.5 text-sm font-medium
                      ${compact ? 'lg:justify-center lg:px-0' : ''} ${active === i ? 'moc-nav-item-active' : ''}`}
                  >
                    <page.icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} aria-hidden />
                    <span className={compact ? 'lg:sr-only' : 'truncate'}>{page.label}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>

      <div className={`flex items-center gap-1 border-t border-white/10 px-3 py-3 ${compact ? 'lg:flex-col' : ''}`}>
        <button type="button" onClick={onAbout} title="About the platform"
          className="moc-nav-item flex flex-1 items-center gap-2 px-3 py-2 text-xs font-medium">
          <Info className="h-4 w-4 shrink-0" strokeWidth={1.75} aria-hidden />
          <span className={compact ? 'lg:sr-only' : ''}>About</span>
        </button>
        <button type="button" onClick={onToggleCollapsed} aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="moc-nav-item hidden p-2 lg:inline-flex">
          {collapsed
            ? <PanelLeftOpen className="h-4 w-4" strokeWidth={1.75} />
            : <PanelLeftClose className="h-4 w-4" strokeWidth={1.75} />}
        </button>
      </div>
    </aside>
  )
}
