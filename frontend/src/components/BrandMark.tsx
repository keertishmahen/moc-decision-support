import React from 'react'

type Props = {
  size?: number
  className?: string
}

/**
 * MoC brand mark — connected knowledge-graph nodes in a navy tile.
 * Blue #4f8ef7 hub + satellites (matches app accent).
 */
export default function BrandMark({ size = 36, className = '' }: Props) {
  const icon = size * 0.58
  return (
    <span
      className={`moc-brand-mark inline-flex flex-shrink-0 items-center justify-center rounded-[10px] ${className}`}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <svg
        width={icon}
        height={icon}
        viewBox="0 0 24 24"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        {/* Edges behind nodes */}
        <line
          x1="7"
          y1="16.5"
          x2="12"
          y2="9"
          stroke="#4f8ef7"
          strokeWidth="1.75"
          strokeLinecap="round"
          opacity="0.85"
        />
        <line
          x1="17"
          y1="16.5"
          x2="12"
          y2="9"
          stroke="#4f8ef7"
          strokeWidth="1.75"
          strokeLinecap="round"
          opacity="0.85"
        />
        {/* Satellite nodes */}
        <circle cx="7" cy="16.5" r="2.6" fill="#4f8ef7" />
        <circle cx="17" cy="16.5" r="2.6" fill="#4f8ef7" />
        {/* Hub */}
        <circle cx="12" cy="8.2" r="3.35" fill="#4f8ef7" />
        <circle cx="12" cy="8.2" r="1.35" fill="#0a1020" opacity="0.55" />
      </svg>
    </span>
  )
}
