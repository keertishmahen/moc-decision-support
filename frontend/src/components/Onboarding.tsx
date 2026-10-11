import React, { useEffect, useRef, useState } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ArrowUpRight,
  Bot,
  Check,
  ClipboardList,
  DollarSign,
  Handshake,
  Lightbulb,
  Rocket,
  ShieldAlert,
  Users,
  X,
} from 'lucide-react'
import {
  CAPABILITIES,
  HERO,
  PROCESS,
  STATS,
  VALUES,
  WHO_WE_ARE,
  WHY_US,
} from '../onboardingContent'
import BrandMark from './BrandMark'

type Props = {
  onEnter: () => void
}

const VALUE_ICONS = {
  lightbulb: Lightbulb,
  handshake: Handshake,
  rocket: Rocket,
  users: Users,
} as const

const CAP_ICONS = {
  form: ClipboardList,
  risk: ShieldAlert,
  cost: DollarSign,
  bot: Bot,
} as const

const ease = [0.22, 1, 0.36, 1] as const

const fadeUp = (reduce: boolean | null, delay = 0) =>
  reduce
    ? { initial: false, animate: { opacity: 1 }, transition: { duration: 0 } }
    : {
        initial: { opacity: 0, y: 22 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.6, ease, delay },
      }

const viewFade = (reduce: boolean | null, delay = 0) =>
  reduce
    ? {}
    : {
        initial: { opacity: 0, y: 28 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: '-72px' },
        transition: { duration: 0.55, ease, delay },
      }

/** Scroll-in + hover for onboarding cards */
const cardMotion = (reduce: boolean | null, delay = 0, from: 'up' | 'left' | 'right' = 'up') => {
  if (reduce) return {}
  const offset =
    from === 'left' ? { x: -28, y: 12 } : from === 'right' ? { x: 28, y: 12 } : { x: 0, y: 40 }
  return {
    initial: { opacity: 0, scale: 0.94, ...offset },
    whileInView: { opacity: 1, scale: 1, x: 0, y: 0 },
    viewport: { once: true, amount: 0.35 },
    transition: { duration: 0.6, ease, delay },
    whileHover: {
      y: -8,
      scale: 1.02,
      transition: { duration: 0.28, ease },
    },
  }
}

function BrandLockup({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-3">
      <BrandMark size={compact ? 34 : 40} />
      <div className="text-left leading-tight">
        <div
          className={`font-semibold tracking-tight text-white ${compact ? 'text-[15px]' : 'text-base'}`}
          style={{ fontFamily: 'Outfit, Inter, sans-serif' }}
        >
          {HERO.brand}
        </div>
        <div className={`text-white/45 ${compact ? 'text-[10px]' : 'text-[11px]'}`}>{HERO.tagline}</div>
      </div>
    </div>
  )
}

function Pill({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-full border border-white/15 bg-white/[0.04] px-3.5 py-1 text-[11px] font-medium tracking-[0.04em] text-white/75 backdrop-blur-sm">
      {children}
    </span>
  )
}

function PrimaryCta({
  onClick,
  label = HERO.cta,
  size = 'md',
}: {
  onClick: () => void
  label?: string
  size?: 'sm' | 'md'
}) {
  const pad = size === 'sm' ? 'px-4 py-2.5 text-[13px]' : 'px-7 py-3.5 text-sm'
  return (
    <motion.button
      type="button"
      onClick={onClick}
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.98 }}
      className={`moc-cta inline-flex items-center gap-2 rounded-xl font-semibold text-white ${pad}`}
    >
      {label}
      <ArrowUpRight className="h-4 w-4" strokeWidth={2.25} />
    </motion.button>
  )
}

export default function Onboarding({ onEnter }: Props) {
  const reduce = useReducedMotion()
  const rootRef = useRef<HTMLDivElement>(null)
  type Star = {
    left: string
    top: string
    size: number
    delay: number
    o: number
    dur: string
  }
  const [starLayers, setStarLayers] = useState<{
    far: Star[]
    mid: Star[]
    near: Star[]
  }>({ far: [], mid: [], near: [] })

  useEffect(() => {
    const make = (count: number, seed: number, sizeBase: number, opacityBase: number): Star[] =>
      Array.from({ length: count }, (_, i) => {
        const n = i + seed
        return {
          left: `${((n * 47 + 13) * 7) % 100}%`,
          top: `${((n * 31 + 19) * 11) % 100}%`,
          size: sizeBase + (n % 5 === 0 ? 1 : 0),
          delay: (n % 11) * 0.45,
          o: opacityBase + (n % 6) * 0.08,
          dur: `${3.2 + (n % 8) * 0.55}s`,
        }
      })

    setStarLayers({
      far: make(40, 0, 1, 0.12),
      mid: make(40, 41, 1.5, 0.22),
      near: make(30, 82, 2, 0.35),
    })
  }, [])

  useEffect(() => {
    if (reduce) return
    const el = rootRef.current
    if (!el) return

    const onMove = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect()
      const x = ((e.clientX - rect.left) / rect.width - 0.5) * 24
      const y = ((e.clientY - rect.top) / rect.height - 0.5) * 18
      el.style.setProperty('--mx', `${x.toFixed(2)}px`)
      el.style.setProperty('--my', `${y.toFixed(2)}px`)
    }

    el.addEventListener('mousemove', onMove)
    return () => el.removeEventListener('mousemove', onMove)
  }, [reduce])

  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' })
  }

  const renderStars = (stars: Star[], keyPrefix: string) =>
    stars.map((s, i) => (
      <span
        key={`${keyPrefix}-${i}`}
        className="onboarding-star absolute rounded-full bg-white"
        style={{
          left: s.left,
          top: s.top,
          width: s.size,
          height: s.size,
          opacity: s.o,
          animationDelay: `${s.delay}s`,
          ['--twinkle-dur' as string]: s.dur,
        }}
      />
    ))

  return (
    <div
      ref={rootRef}
      className="onboarding-root relative min-h-screen overflow-x-hidden text-[#e8eeff]"
      style={{ fontFamily: 'Outfit, Inter, sans-serif' }}
    >
      {/* Atmosphere: layered drifting starfield + nebula */}
      <div className="onboarding-stars pointer-events-none absolute inset-0 z-0 overflow-hidden" aria-hidden>
        <div className="onboarding-star-layer onboarding-star-layer--far">
          {renderStars(starLayers.far, 'far')}
        </div>
        <div className="onboarding-star-layer onboarding-star-layer--mid">
          {renderStars(starLayers.mid, 'mid')}
        </div>
        <div className="onboarding-star-layer onboarding-star-layer--near">
          {renderStars(starLayers.near, 'near')}
        </div>
      </div>

      {/* Header */}
      <header className="relative z-20 mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-5 md:px-8">
        <BrandLockup compact />
        <nav className="hidden items-center gap-1 rounded-full border border-white/10 bg-white/[0.03] px-1.5 py-1.5 text-[13px] text-white/55 backdrop-blur-md md:flex">
          {[
            ['who', 'Who'],
            ['capabilities', 'Platform'],
            ['process', 'Process'],
            ['values', 'Values'],
            ['why', 'Why'],
          ].map(([id, label]) => (
            <button
              key={id}
              type="button"
              className="rounded-full px-3.5 py-1.5 transition-colors hover:bg-white/[0.06] hover:text-white"
              onClick={() => scrollTo(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        <PrimaryCta onClick={onEnter} size="sm" />
      </header>

      {/* Hero */}
      <section className="relative z-10 flex min-h-[88vh] flex-col items-center justify-center px-5 pb-16 pt-8 text-center md:px-8">
        <div className="onboarding-nebula-layer absolute inset-0 overflow-hidden" aria-hidden>
          <div className="onboarding-glow absolute left-1/2 top-[42%] h-[520px] w-[520px] -translate-x-1/2 -translate-y-1/2 rounded-full md:h-[720px] md:w-[720px]" />
          <div className="onboarding-glow-soft absolute left-[46%] top-[48%] h-[380px] w-[420px] -translate-x-1/2 -translate-y-1/2 rounded-full md:h-[520px] md:w-[580px]" />
        </div>

        <motion.div className="relative max-w-3xl" {...fadeUp(reduce, 0.04)}>
          <motion.div
            className="mb-8 flex justify-center"
            {...(reduce ? {} : { initial: { scale: 0.92, opacity: 0 }, animate: { scale: 1, opacity: 1 }, transition: { duration: 0.7, ease } })}
          >
            <div className="moc-hero-brand inline-flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0b1020]/70 px-4 py-3 backdrop-blur-xl">
              <BrandMark size={44} />
              <div className="text-left">
                <div className="text-lg font-semibold tracking-tight text-white">{HERO.brand}</div>
                <div className="text-xs text-white/45">{HERO.tagline}</div>
              </div>
            </div>
          </motion.div>

          <h1 className="text-[2.35rem] font-semibold leading-[1.12] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
            {HERO.headline}
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-white/55 md:text-lg">
            {HERO.subhead}
          </p>
          <div className="mt-9 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <PrimaryCta onClick={onEnter} />
            <button
              type="button"
              onClick={() => scrollTo('who')}
              className="rounded-xl border border-white/12 bg-white/[0.03] px-5 py-3.5 text-sm text-white/65 transition-colors hover:border-white/25 hover:text-white"
            >
              Explore the platform
            </button>
          </div>
          <p className="mt-6 text-xs tracking-wide text-white/35">{HERO.trust}</p>
        </motion.div>

        {/* Stats ribbon */}
        <div className="relative z-10 mt-16 grid w-full max-w-4xl grid-cols-2 gap-3 sm:grid-cols-4">
          {STATS.map((s, i) => (
            <motion.div
              key={s.label}
              className="onboarding-stat moc-glass cursor-default rounded-2xl border border-white/10 px-4 py-4 text-center"
              {...cardMotion(reduce, 0.15 + i * 0.08)}
            >
              <div className="text-2xl font-semibold tracking-tight text-[#93c5fd]">{s.value}</div>
              <div className="mt-1 text-[11px] uppercase tracking-[0.12em] text-white/40">{s.label}</div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Who We Are */}
      <section id="who" className="relative z-10 mx-auto max-w-6xl px-5 py-20 md:px-8 md:py-24">
        <motion.div className="mx-auto max-w-2xl text-center" {...viewFade(reduce)}>
          <Pill>{WHO_WE_ARE.badge}</Pill>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white md:text-4xl">{WHO_WE_ARE.headline}</h2>
          <p className="mt-4 text-base leading-relaxed text-white/55 md:text-[17px]">{WHO_WE_ARE.subhead}</p>
        </motion.div>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {WHO_WE_ARE.cards.map((card, i) => (
            <motion.article
              key={card.title}
              className="onboarding-card moc-glass group cursor-default rounded-2xl border border-white/10 p-6 text-left"
              {...cardMotion(reduce, i * 0.1)}
            >
              <div className="mb-4 h-px w-10 bg-gradient-to-r from-[#F4A261] to-transparent" />
              <h3 className="text-lg font-semibold text-white">{card.title}</h3>
              <p className="mt-3 text-sm leading-relaxed text-white/55">{card.body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      {/* Capabilities */}
      <section id="capabilities" className="relative z-10 mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-20">
        <motion.div className="mx-auto max-w-2xl text-center" {...viewFade(reduce)}>
          <Pill>Platform</Pill>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white md:text-4xl">Everything in one intelligence surface</h2>
          <p className="mt-4 text-base leading-relaxed text-white/55">
            Five connected workspaces — each grounded in the same FCC Unit knowledge graph.
          </p>
        </motion.div>
        <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {CAPABILITIES.map((cap, i) => {
            const Icon = CAP_ICONS[cap.icon]
            return (
              <motion.article
                key={cap.title}
                className="onboarding-card moc-glass cursor-default rounded-2xl border border-white/10 p-5"
                {...cardMotion(reduce, i * 0.09)}
              >
                <span className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#4f8ef7]/25 bg-[#4f8ef7]/10 text-[#93c5fd]">
                  <Icon className="h-4 w-4" strokeWidth={1.75} />
                </span>
                <h3 className="text-[15px] font-semibold text-white">{cap.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-white/50">{cap.body}</p>
              </motion.article>
            )
          })}
        </div>
      </section>

      {/* Process */}
      <section id="process" className="relative z-10 mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
        <motion.div className="mx-auto max-w-2xl text-center" {...viewFade(reduce)}>
          <Pill>{PROCESS.badge}</Pill>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white md:text-4xl">{PROCESS.headline}</h2>
          <p className="mt-4 text-base leading-relaxed text-white/55">{PROCESS.subhead}</p>
        </motion.div>
        <div className="relative mt-14 grid gap-4 md:grid-cols-4">
          <div className="pointer-events-none absolute left-[12%] right-[12%] top-8 hidden h-px bg-gradient-to-r from-transparent via-[#4f8ef7]/35 to-transparent md:block" aria-hidden />
          {PROCESS.steps.map((step, i) => (
            <motion.article
              key={step.step}
              className="onboarding-process-card moc-glass relative cursor-default rounded-2xl border border-white/10 p-5 text-left"
              {...cardMotion(reduce, i * 0.12)}
            >
              <div className="text-xs font-semibold tracking-[0.18em] text-[#F4A261]">{step.step}</div>
              <h3 className="mt-3 text-base font-semibold text-white">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/50">{step.body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      {/* Values */}
      <section id="values" className="relative z-10 mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
        <div className="pointer-events-none absolute left-1/2 top-1/2 h-80 w-80 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#4f8ef7]/10 blur-3xl" aria-hidden />
        <motion.div className="relative mx-auto max-w-2xl text-center" {...viewFade(reduce)}>
          <Pill>{VALUES.badge}</Pill>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white md:text-4xl">{VALUES.headline}</h2>
          <p className="mt-4 text-base leading-relaxed text-white/55">{VALUES.subhead}</p>
        </motion.div>

        <div className="relative mt-12 grid gap-4 sm:grid-cols-2">
          {VALUES.cards.map((card, i) => {
            const Icon = VALUE_ICONS[card.icon]
            return (
              <motion.article
                key={card.title}
                className="onboarding-card moc-glass cursor-default rounded-2xl border border-white/10 p-6"
                {...cardMotion(reduce, i * 0.1)}
              >
                <div className="flex items-center gap-3">
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-[#F4A261]">
                    <Icon className="h-4 w-4" strokeWidth={1.75} />
                  </span>
                  <h3 className="text-base font-semibold text-white">{card.title}</h3>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-white/55">{card.body}</p>
              </motion.article>
            )
          })}
        </div>
      </section>

      {/* Why Us */}
      <section id="why" className="relative z-10 mx-auto max-w-6xl px-5 py-16 md:px-8 md:py-24">
        <motion.div className="mx-auto max-w-2xl text-center" {...viewFade(reduce)}>
          <Pill>{WHY_US.badge}</Pill>
          <h2 className="mt-5 text-3xl font-semibold tracking-tight text-white md:text-4xl">{WHY_US.headline}</h2>
          <p className="mt-4 text-base leading-relaxed text-white/55">{WHY_US.subhead}</p>
        </motion.div>

        <div className="mt-12 grid gap-4 lg:grid-cols-2">
          <motion.div
            className="onboarding-card moc-glass cursor-default rounded-2xl border border-white/10 p-6 md:p-8"
            {...cardMotion(reduce, 0, 'left')}
          >
            <h3 className="text-lg font-semibold text-white">{WHY_US.problems.title}</h3>
            <ul className="mt-5 space-y-3.5">
              {WHY_US.problems.items.map((item, i) => (
                <motion.li
                  key={item}
                  className="flex items-start gap-3 text-sm text-white/55"
                  {...(reduce
                    ? {}
                    : {
                        initial: { opacity: 0, x: -10 },
                        whileInView: { opacity: 1, x: 0 },
                        viewport: { once: true },
                        transition: { duration: 0.35, delay: 0.2 + i * 0.06, ease },
                      })}
                >
                  <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-white/5">
                    <X className="h-3 w-3 text-white/65" strokeWidth={2.5} />
                  </span>
                  {item}
                </motion.li>
              ))}
            </ul>
          </motion.div>

          <motion.div
            className="onboarding-card moc-solution relative cursor-default overflow-hidden rounded-2xl border border-[#4f8ef7]/30 p-6 md:p-8"
            {...cardMotion(reduce, 0.12, 'right')}
          >
            <div className="pointer-events-none absolute -right-10 -top-10 h-44 w-44 rounded-full bg-[#4f8ef7]/30 blur-3xl" aria-hidden />
            <div className="pointer-events-none absolute -bottom-8 left-8 h-28 w-28 rounded-full bg-[#F4A261]/15 blur-3xl" aria-hidden />
            <h3 className="relative text-lg font-semibold text-white">{WHY_US.solutions.title}</h3>
            <ul className="relative mt-5 space-y-3.5">
              {WHY_US.solutions.items.map((item, i) => (
                <motion.li
                  key={item}
                  className="flex items-start gap-3 text-sm text-white/75"
                  {...(reduce
                    ? {}
                    : {
                        initial: { opacity: 0, x: 10 },
                        whileInView: { opacity: 1, x: 0 },
                        viewport: { once: true },
                        transition: { duration: 0.35, delay: 0.28 + i * 0.06, ease },
                      })}
                >
                  <span className="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-[#4f8ef7]/20">
                    <Check className="h-3 w-3 text-[#93c5fd]" strokeWidth={2.5} />
                  </span>
                  {item}
                </motion.li>
              ))}
            </ul>
          </motion.div>
        </div>
      </section>

      {/* Footer CTA */}
      <footer className="relative z-10 px-5 pb-20 pt-8 md:px-8">
        <motion.div
          className="moc-footer-panel relative mx-auto max-w-4xl overflow-hidden rounded-3xl border border-white/10 px-6 py-14 text-center md:px-12"
          {...viewFade(reduce)}
        >
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#0b1020]/80 to-black/90" aria-hidden />
          <div className="relative">
            <BrandMark size={48} />
            <h2 className="mt-5 text-2xl font-semibold text-white md:text-3xl">Ready to explore the platform?</h2>
            <p className="mx-auto mt-3 max-w-lg text-sm text-white/50">
              Enter Smart Form, Risk & Impact, Cost Predictor, MoCBot, and Process Intelligence — all grounded in your FCC Unit graph.
            </p>
            <div className="mt-8">
              <PrimaryCta onClick={onEnter} />
            </div>
          </div>
        </motion.div>
        <p className="mt-8 text-center text-[11px] text-white/25">MoC Intelligence Platform · FCC Unit</p>
      </footer>
    </div>
  )
}
