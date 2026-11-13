import React from 'react'
import { Moon, Sun } from 'lucide-react'
import { useTheme } from '../theme/ThemeProvider'

/** Switches between light and dark. Shows the mode you will switch TO. */
export default function ThemeToggle({ className = '', withLabel = false }: { className?: string; withLabel?: boolean }) {
  const { theme, toggle } = useTheme()
  const toLight = theme === 'dark'
  const label = toLight ? 'Switch to light mode' : 'Switch to dark mode'
  const Icon = toLight ? Sun : Moon
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={label}
      title={label}
      aria-pressed={theme === 'light'}
      className={`inline-flex items-center gap-2 rounded-xl border border-white/12 bg-white/[0.04] px-2.5 py-2 text-white/70 transition-colors hover:border-white/25 hover:text-white ${className}`}
    >
      <Icon className="h-4 w-4" strokeWidth={1.75} />
      {withLabel && <span className="text-[12px] font-medium">{toLight ? 'Light mode' : 'Dark mode'}</span>}
    </button>
  )
}
