/**
 * Landing page ("aurora" theme): a warm page with soft multicolour glows, a split hero with a
 * preview of a real Change Case, the platform as a feature list, and a dark closing card.
 * All copy is in onboardingContent.ts; colours come from index.css (onb-*, aurora-* and tokens).
 */
import React, { useMemo } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import {
  ArrowRight, Bot, Check, CircleDollarSign, ClipboardList, FileSearch, FlaskConical, Gavel, GitBranch,
  LayoutDashboard, Network, Scale, ShieldAlert, ShieldCheck, SlidersHorizontal, TriangleAlert, UserCheck,
  Workflow, X, type LucideIcon,
} from 'lucide-react'
import {
  CAPABILITIES, CAPABILITIES_INTRO, FOOTER, HERO, PREVIEW, PROCESS, STATS, VALUES, WHO_WE_ARE, WHY_US,
  type CapabilityIcon,
} from '../onboardingContent'
import { cssVar, tint, type Token } from '../theme/palette'
import SymmetraLogo from './SymmetraLogo'
import ThemeToggle from './ThemeToggle'

type Props = { onEnter: () => void }

const CAP_ICONS: Record<CapabilityIcon, LucideIcon> = {
  overview: LayoutDashboard, case: Workflow, form: ClipboardList, risk: ShieldAlert,
  cost: CircleDollarSign, bot: Bot, process: GitBranch, allocation: Scale,
}

const VALUE_ICONS = {
  shield: ShieldCheck, authority: UserCheck, synthetic: FlaskConical, evidence: FileSearch, calibration: SlidersHorizontal,
} as const
const VALUE_TONES: Token[] = ['accent', 'accent2', 'node-lesson', 'ok', 'highlight']
const ABOUT = [
  { icon: Network, tone: 'node-category' as Token },
  { icon: ClipboardList, tone: 'accent2' as Token },
  { icon: Scale, tone: 'highlight' as Token },
]
const AGENT_DOTS: Token[] = ['node-category', 'accent', 'danger', 'node-hazop', 'highlight', 'ok', 'accent2', 'slate']

const NAV = [
  ['who', 'About'], ['why', 'Problem'], ['capabilities', 'Platform'], ['process', 'Journey'], ['values', 'Safeguards'],
] as const

const ease = [0.22, 1, 0.36, 1] as const

const fadeUp = (reduce: boolean | null, delay = 0) =>
  reduce
    ? {}
    : { initial: { opacity: 0, y: 22 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.65, ease, delay } }

const inView = (reduce: boolean | null, delay = 0) =>
  reduce
    ? {}
    : {
        initial: { opacity: 0, y: 26 },
        whileInView: { opacity: 1, y: 0 },
        viewport: { once: true, margin: '-60px' },
        transition: { duration: 0.55, ease, delay },
      }

/** Gentle vertical float for the hero chips. */
const float = (reduce: boolean | null, delay: number) =>
  reduce ? {} : { animate: { y: [0, -7, 0] }, transition: { duration: 5.5, repeat: Infinity, ease: 'easeInOut' as const, delay } }

function IconCircle({ icon: Icon, tone, size = 40 }: { icon: LucideIcon; tone: Token; size?: number }) {
  return (
    <span className="inline-flex shrink-0 items-center justify-center rounded-full"
      style={{ width: size, height: size, background: tint(tone, 14), color: cssVar(tone) }}>
      <Icon style={{ width: size * 0.45, height: size * 0.45 }} strokeWidth={1.75} aria-hidden />
    </span>
  )
}

function SectionHead({ badge, title, sub }: { badge: string; title: string; sub?: string }) {
  return (
    <div className="max-w-2xl">
      <div className="text-[12px] font-semibold uppercase tracking-[0.2em] text-accent">{badge}</div>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white md:text-[2.6rem] md:leading-[1.1]">{title}</h2>
      {sub && <p className="mt-4 text-base leading-relaxed text-white/55 md:text-[17px]">{sub}</p>}
    </div>
  )
}

function Stars({ count, seed, className = '' }: { count: number; seed: number; className?: string }) {
  const stars = useMemo(() => Array.from({ length: count }, (_, i) => {
    const n = i + seed
    return {
      left: `${((n * 47 + 13) * 7) % 100}%`, top: `${((n * 31 + 19) * 11) % 100}%`,
      size: 1 + (n % 5 === 0 ? 1 : 0), delay: (n % 11) * 0.45, dur: `${3.2 + (n % 8) * 0.55}s`,
    }
  }), [count, seed])
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`} aria-hidden>
      {stars.map((s, i) => (
        <span key={i} className="onb-star" style={{
          left: s.left, top: s.top, width: s.size, height: s.size, animationDelay: `${s.delay}s`,
          ['--twinkle-dur' as string]: s.dur,
        }} />
      ))}
    </div>
  )
}

/** A faint glow behind a section, so the colour carries down the page. */
function SectionGlow({ side, colours }: { side: 'left' | 'right'; colours: ('cyan' | 'violet' | 'pink' | 'orange')[] }) {
  return (
    <div className={`onb-aurora -z-10 top-0 h-[70%] w-[55%] opacity-60 ${side === 'left' ? '-left-[15%]' : '-right-[15%]'}`} aria-hidden>
      {colours.map((c, i) => (
        <div key={c} className={`onb-blob onb-blob-${c} h-[70%] w-[70%]`} style={{ left: `${i * 25}%`, top: `${i * 20}%` }} />
      ))}
    </div>
  )
}

function HeroPreview({ reduce }: { reduce: boolean | null }) {
  return (
    <div className="relative mx-auto w-full max-w-[560px] lg:h-[500px]">
      {/* glow behind the preview */}
      <div className="onb-aurora -inset-16 lg:-inset-24" aria-hidden>
        <div className="onb-blob onb-blob-cyan left-[8%] top-[2%] h-[55%] w-[55%]" />
        <div className="onb-blob onb-blob-violet left-[20%] top-[38%] h-[60%] w-[60%]" />
        <div className="onb-blob onb-blob-pink left-[38%] top-[48%] h-[55%] w-[55%]" />
        <div className="onb-blob onb-blob-orange right-[0%] top-[8%] h-[58%] w-[52%]" />
      </div>

      <div className="relative flex flex-col items-center gap-3 lg:block lg:h-full">
        <motion.div className="lg:absolute lg:right-0 lg:top-4" {...float(reduce, 0)}>
          <span className="onb-chip"><ShieldCheck className="h-4 w-4" strokeWidth={2} aria-hidden />{PREVIEW.chips.verified}</span>
        </motion.div>
        <motion.div className="lg:absolute lg:left-0 lg:top-[92px]" {...float(reduce, 1.2)}>
          <span className="onb-chip"><Scale className="h-4 w-4" strokeWidth={2} aria-hidden />{PREVIEW.chips.allocation}</span>
        </motion.div>

        <div className="onb-preview relative w-full max-w-[400px] lg:absolute lg:left-1/2 lg:top-[150px] lg:-translate-x-1/2">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-3">
            <div className="flex items-center gap-2 text-[13px] text-white/70">
              <Workflow className="h-4 w-4 text-accent" strokeWidth={1.75} aria-hidden />
              <span className="font-semibold text-white/85">{PREVIEW.label}</span>
            </div>
            <span className="inline-flex items-center gap-1.5 text-[11px] font-semibold" style={{ color: cssVar('ok') }}>
              <span className="h-1.5 w-1.5 rounded-full" style={{ background: cssVar('ok') }} aria-hidden />{PREVIEW.example}
            </span>
          </div>
          <div className="px-4 py-3">
            <div className="text-[12px] text-white/45"><span className="tabular-nums text-accent">{PREVIEW.asset}</span> · {PREVIEW.changeType}</div>
            <div className="mt-0.5 text-[15px] font-semibold text-white">{PREVIEW.title}</div>
          </div>
          <ul className="space-y-2 border-t border-white/10 px-4 py-3 text-[13px] text-white/70">
            {PREVIEW.rows.map(r => (
              <li key={r.text} className="flex items-center gap-2">
                {r.icon === 'reach'
                  ? <Network className="h-3.5 w-3.5 shrink-0" style={{ color: cssVar('node-category') }} strokeWidth={2} aria-hidden />
                  : <TriangleAlert className="h-3.5 w-3.5 shrink-0" style={{ color: cssVar('warn') }} strokeWidth={2} aria-hidden />}
                {r.text}
              </li>
            ))}
            <li className="flex items-center gap-2">
              <span className="flex gap-1" aria-hidden>
                {AGENT_DOTS.map((t, i) => <span key={i} className="h-2 w-2 rounded-full" style={{ background: cssVar(t) }} />)}
              </span>
              <span className="text-white/55">{PREVIEW.agents}</span>
            </li>
          </ul>
        </div>

        <div className="flex gap-2 lg:absolute lg:left-[4%] lg:top-[372px]">
          {PREVIEW.scores.map(s => (
            <span key={s.label} className="onb-preview rounded-full px-3 py-1.5 text-[12px] font-semibold" style={{ color: cssVar(s.tone) }}>
              {s.label}
            </span>
          ))}
        </div>
        <motion.div className="lg:absolute lg:bottom-6 lg:right-0" {...float(reduce, 2.4)}>
          <span className="onb-chip onb-chip-violet"><Gavel className="h-4 w-4" strokeWidth={2} aria-hidden />{PREVIEW.chips.approval}</span>
        </motion.div>
      </div>
    </div>
  )
}

export default function Onboarding({ onEnter }: Props) {
  const reduce = useReducedMotion()
  const scrollTo = (id: string) => document.getElementById(id)?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth' })

  return (
    <div className="onb-root relative min-h-screen overflow-x-clip text-ink">
      <Stars count={70} seed={0} className="onb-page-stars" />

      {/* ── Header ── */}
      <header className="relative z-20 mx-auto flex max-w-7xl items-center justify-between gap-4 px-5 py-5 md:px-8">
        <div className="flex items-center gap-3">
          <SymmetraLogo size={32} />
          <div className="hidden border-l border-white/15 pl-3 leading-tight sm:block">
            <div className="text-[13px] font-medium text-white/85">{HERO.brand}</div>
            <div className="text-[10px] text-white/45">{HERO.tagline}</div>
          </div>
        </div>
        <nav className="hidden items-center gap-7 text-[15px] text-white/60 lg:flex" aria-label="Sections">
          {NAV.map(([id, label]) => (
            <button key={id} type="button" onClick={() => scrollTo(id)} className="transition-colors hover:text-white">{label}</button>
          ))}
        </nav>
        <div className="flex items-center gap-2.5">
          <ThemeToggle />
          <button type="button" onClick={onEnter} className="onb-pill-btn px-4 py-2.5 text-[14px]">{HERO.cta}</button>
        </div>
      </header>

      {/* ── Hero ── */}
      <section className="relative z-10 mx-auto grid max-w-7xl items-center gap-12 px-5 pb-16 pt-10 md:px-8 lg:grid-cols-[1.12fr_1fr] lg:pb-24 lg:pt-16">
        <motion.div {...fadeUp(reduce, 0.05)}>
          <div className="text-[12px] font-semibold uppercase tracking-[0.22em] text-accent">{HERO.eyebrow}</div>
          <h1 className="mt-5 text-[2.4rem] font-semibold leading-[1.06] tracking-[-0.02em] text-white sm:text-5xl lg:text-[3.2rem] xl:text-[3.55rem]">
            {HERO.headline.lead}<br />
            <span className="onb-gradient-text">{HERO.headline.accent}</span><br />
            {HERO.headline.tail}
          </h1>
          <p className="mt-6 flex max-w-xl items-start gap-2 text-[15px] text-white/55">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" style={{ color: cssVar('accent2') }} strokeWidth={2} aria-hidden />
            <span><b className="font-semibold text-white/85">{HERO.proof.strong}</b>{HERO.proof.rest}</span>
          </p>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-white/55">{HERO.subhead}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <button type="button" onClick={onEnter} className="onb-pill-btn px-6 py-3.5 text-[15px]">
              {HERO.cta}<ArrowRight className="h-4 w-4" strokeWidth={2.25} aria-hidden />
            </button>
            <button type="button" onClick={() => scrollTo('process')} className="onb-ghost-btn px-6 py-3.5 text-[15px] text-white/80">
              {HERO.secondary}
            </button>
          </div>
          <ul className="mt-7 flex flex-wrap gap-x-6 gap-y-2 text-[13px] text-white/50">
            {HERO.points.map(p => (
              <li key={p} className="flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5" style={{ color: cssVar('ok') }} strokeWidth={2.5} aria-hidden />{p}
              </li>
            ))}
          </ul>
        </motion.div>

        <motion.div {...fadeUp(reduce, 0.2)}>
          <HeroPreview reduce={reduce} />
        </motion.div>
      </section>

      {/* ── Stats ── */}
      <section className="relative z-10 mx-auto max-w-7xl px-5 md:px-8">
        <div className="onb-card grid grid-cols-2 divide-white/10 md:grid-cols-4 md:divide-x">
          {STATS.map(s => (
            <div key={s.label} className="px-6 py-6 text-center">
              <div className="onb-gradient-text text-4xl font-semibold tracking-tight">{s.value}</div>
              <div className="mt-1 text-[11px] uppercase tracking-[0.14em] text-white/45">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── About ── */}
      <section id="who" className="relative z-10 mx-auto max-w-7xl scroll-mt-6 px-5 py-20 md:px-8 md:py-28">
        <SectionGlow side="left" colours={['cyan', 'violet']} />
        <motion.div {...inView(reduce)}>
          <SectionHead badge={WHO_WE_ARE.badge} title={WHO_WE_ARE.headline} sub={WHO_WE_ARE.subhead} />
        </motion.div>
        <div className="mt-12 grid gap-5 md:grid-cols-3">
          {WHO_WE_ARE.cards.map((card, i) => (
            <motion.article key={card.title} className="onb-card onb-card-hover p-6" {...inView(reduce, i * 0.08)}>
              <IconCircle icon={ABOUT[i % ABOUT.length].icon} tone={ABOUT[i % ABOUT.length].tone} />
              <h3 className="mt-4 text-lg font-semibold text-white">{card.title}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-white/55">{card.body}</p>
              <div className="mt-5 h-1 w-14 rounded-full" style={{ background: `linear-gradient(90deg, ${cssVar(ABOUT[i % ABOUT.length].tone)}, transparent)` }} aria-hidden />
            </motion.article>
          ))}
        </div>
      </section>

      {/* ── Problem and response ── */}
      <section id="why" className="relative z-10 mx-auto max-w-7xl scroll-mt-6 px-5 py-12 md:px-8 md:py-20">
        <motion.div {...inView(reduce)}>
          <SectionHead badge={WHY_US.badge} title={WHY_US.headline} sub={WHY_US.subhead} />
        </motion.div>
        <div className="mt-12 grid gap-5 lg:grid-cols-2">
          <motion.div className="onb-card p-7" {...inView(reduce)}>
            <h3 className="text-lg font-semibold text-white">{WHY_US.problems.title}</h3>
            <ul className="mt-5 space-y-4">
              {WHY_US.problems.items.map(item => (
                <li key={item} className="flex items-start gap-3 text-[15px] text-white/60">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/[0.06]">
                    <X className="h-3.5 w-3.5 text-white/55" strokeWidth={2.5} aria-hidden />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>
          <motion.div className="onb-card relative overflow-hidden p-7" {...inView(reduce, 0.1)}>
            <div className="onb-aurora -right-20 -top-20 h-72 w-72" aria-hidden>
              <div className="onb-blob onb-blob-violet inset-0" />
            </div>
            <div className="onb-aurora -bottom-24 left-10 h-64 w-64" aria-hidden>
              <div className="onb-blob onb-blob-cyan inset-0" />
            </div>
            <h3 className="relative text-lg font-semibold text-white">{WHY_US.solutions.title}</h3>
            <ul className="relative mt-5 space-y-4">
              {WHY_US.solutions.items.map(item => (
                <li key={item} className="flex items-start gap-3 text-[15px] text-white/80">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full" style={{ background: tint('ok', 16) }}>
                    <Check className="h-3.5 w-3.5" style={{ color: cssVar('ok') }} strokeWidth={2.5} aria-hidden />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </motion.div>
        </div>
      </section>

      {/* ── Platform ── */}
      <section id="capabilities" className="relative z-10 mx-auto max-w-7xl scroll-mt-6 px-5 py-12 md:px-8 md:py-20">
        <SectionGlow side="right" colours={['pink', 'orange']} />
        <motion.div {...inView(reduce)}>
          <SectionHead badge={CAPABILITIES_INTRO.badge} title={CAPABILITIES_INTRO.headline} sub={CAPABILITIES_INTRO.subhead} />
        </motion.div>
        <div className="mt-10 grid gap-x-12 md:grid-cols-2">
          {CAPABILITIES.map((cap, i) => {
            const Icon = CAP_ICONS[cap.icon]
            return (
              <motion.article key={cap.title} className="onb-feature py-7" {...inView(reduce, (i % 2) * 0.06)}>
                <div className="flex items-center gap-3">
                  <IconCircle icon={Icon} tone={cap.tone} size={38} />
                  <h3 className="text-[17px] font-semibold text-white">{cap.title}</h3>
                </div>
                <p className="mt-3 text-[15px] leading-relaxed text-white/55">{cap.body}</p>
                {cap.proof?.kind === 'source' && (
                  <div className="onb-card mt-4 px-4 py-3 text-[13px]">
                    <div className="text-white/45">&ldquo;{cap.proof.question}&rdquo;</div>
                    <div className="mt-1 text-white/85">{cap.proof.answer}</div>
                    <div className="mt-1.5 flex items-center gap-1.5 text-[12px] font-medium text-accent">
                      <Network className="h-3.5 w-3.5" strokeWidth={2} aria-hidden />{cap.proof.source}
                    </div>
                  </div>
                )}
                {cap.proof?.kind === 'scores' && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {cap.proof.scores.map(s => (
                      <span key={s} className="rounded-full px-3 py-1 text-[12px] font-semibold"
                        style={{ color: cssVar('ok'), background: tint('ok', 12), border: `1px solid ${tint('ok', 30)}` }}>
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </motion.article>
            )
          })}
        </div>
      </section>

      {/* ── Journey ── */}
      <section id="process" className="relative z-10 mx-auto max-w-7xl scroll-mt-6 px-5 py-12 md:px-8 md:py-20">
        <SectionGlow side="left" colours={['violet', 'cyan']} />
        <motion.div {...inView(reduce)}>
          <SectionHead badge={PROCESS.badge} title={PROCESS.headline} sub={PROCESS.subhead} />
        </motion.div>
        <div className="relative mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-5">
          <div className="pointer-events-none absolute left-[8%] right-[8%] top-[34px] hidden h-0.5 rounded-full lg:block"
            style={{ background: 'var(--aurora-text)', opacity: 0.5 }} aria-hidden />
          {PROCESS.steps.map((step, i) => (
            <motion.article key={step.step} className="onb-card onb-card-hover relative p-5" {...inView(reduce, i * 0.08)}>
              <div className="onb-gradient-text text-3xl font-semibold">{step.step}</div>
              <h3 className="mt-3 text-base font-semibold text-white">{step.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/55">{step.body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      {/* ── Safeguards ── */}
      <section id="values" className="relative z-10 mx-auto max-w-7xl scroll-mt-6 px-5 py-12 md:px-8 md:py-20">
        <motion.div {...inView(reduce)}>
          <SectionHead badge={VALUES.badge} title={VALUES.headline} sub={VALUES.subhead} />
        </motion.div>
        <div className="mt-10 grid gap-x-12 md:grid-cols-2">
          {VALUES.cards.map((card, i) => (
            <motion.article key={card.title} className="onb-feature py-7" {...inView(reduce, (i % 2) * 0.06)}>
              <div className="flex items-center gap-3">
                <IconCircle icon={VALUE_ICONS[card.icon]} tone={VALUE_TONES[i % VALUE_TONES.length]} size={38} />
                <h3 className="text-[17px] font-semibold text-white">{card.title}</h3>
              </div>
              <p className="mt-3 text-[15px] leading-relaxed text-white/55">{card.body}</p>
            </motion.article>
          ))}
        </div>
      </section>

      {/* ── Closing call to action ── */}
      <section className="relative z-10 mx-auto max-w-5xl px-5 py-16 md:px-8 md:py-24">
        <motion.div className="onb-cta-card px-6 py-16 text-center md:px-12 md:py-20" {...inView(reduce)}>
          <Stars count={36} seed={200} />
          <div className="relative">
            <h2 className="mx-auto max-w-2xl text-4xl font-semibold leading-[1.08] tracking-tight text-white md:text-6xl">{FOOTER.headline}</h2>
            <p className="mx-auto mt-5 max-w-lg text-[15px] text-white/70">{FOOTER.body}</p>
            <button type="button" onClick={onEnter} className="onb-cta-btn mt-8 px-6 py-3 text-[15px]">
              {HERO.cta}<ArrowRight className="h-4 w-4" strokeWidth={2.25} aria-hidden />
            </button>
          </div>
        </motion.div>
      </section>

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-white/10">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-[1.4fr_1fr_1fr_1fr] md:px-8">
          <div>
            <SymmetraLogo size={32} />
            <p className="mt-4 max-w-sm text-[15px] leading-relaxed text-white/50">{FOOTER.blurb}</p>
          </div>
          <div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-white/80">Explore</div>
            <ul className="mt-4 space-y-2.5 text-[15px] text-white/55">
              {NAV.map(([id, label]) => (
                <li key={id}><button type="button" onClick={() => scrollTo(id)} className="hover:text-white">{label}</button></li>
              ))}
            </ul>
          </div>
          <div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-white/80">Workspaces</div>
            <ul className="mt-4 space-y-2.5 text-[15px] text-white/55">
              {CAPABILITIES.map(c => <li key={c.title}>{c.title}</li>)}
            </ul>
          </div>
          <div>
            <div className="text-[12px] font-semibold uppercase tracking-[0.18em] text-white/80">Safeguards</div>
            <ul className="mt-4 space-y-2.5 text-[15px] text-white/55">
              {FOOTER.safeguards.map(s => <li key={s}>{s}</li>)}
            </ul>
            <button type="button" onClick={onEnter} className="mt-6 inline-flex items-center gap-1.5 text-[15px] font-semibold text-accent hover:text-accent-soft">
              {HERO.cta}<ArrowRight className="h-4 w-4" strokeWidth={2} aria-hidden />
            </button>
          </div>
        </div>
        <p className="pb-10 text-center text-[12px] text-white/35">{FOOTER.line}</p>
      </footer>
    </div>
  )
}
