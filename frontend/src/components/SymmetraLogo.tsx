import React from 'react'
import mark from '../assets/symmetra-mark.png'

type Props = {
  /** Height of the icon in pixels; the wordmark scales with it. */
  size?: number
  /** Show "Symmetra Systems" next to the icon. */
  wordmark?: boolean
  className?: string
}

/**
 * Symmetra Systems logo for dark backgrounds: the loop-and-nodes icon (cut from the
 * supplied logo artwork) with the wordmark set in white. The only place the logo is defined.
 */
export default function SymmetraLogo({ size = 36, wordmark = true, className = '' }: Props) {
  return (
    <span className={`inline-flex flex-shrink-0 items-center ${className}`} style={{ gap: size * 0.3 }}>
      <img
        src={mark}
        alt={wordmark ? '' : 'Symmetra Systems'}
        style={{ height: size, width: 'auto' }}
        draggable={false}
      />
      {wordmark && (
        <span className="text-left leading-none" style={{ fontFamily: 'Outfit, Inter, sans-serif' }}>
          <span className="block font-semibold tracking-tight text-white" style={{ fontSize: size * 0.5 }}>
            Symmetra
          </span>
          <span className="block text-white/65" style={{ fontSize: size * 0.36, marginTop: size * 0.1 }}>
            Systems
          </span>
        </span>
      )}
    </span>
  )
}
