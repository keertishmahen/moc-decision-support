export const ONBOARDING_STORAGE_KEY = 'moc-onboarding-seen'

/**
 * Landing-page copy. It presents the public proposition of SRG – Symmetra Systems Design
 * Studio and describes only what the application does today.
 */

export const HERO = {
  brand: 'MoC Intelligence Platform',
  tagline: 'SRG – Symmetra Systems Design Studio',
  headline: 'Understand what an engineering change affects, identify who should decide, and keep a defensible record',
  subhead:
    'Ontology-driven Management of Change joined with a computable human–AI decision-allocation model: connected engineering knowledge, structured assessment and a transparent recommendation for every change.',
  cta: 'Enter Platform',
  trust: 'Decision-support prototype · Synthetic FCC demonstration data',
}

export const STATS = [
  { label: 'FCC change scenarios', value: '10' },
  { label: 'Assets mapped', value: '22' },
  { label: 'Characterisation axes', value: '8' },
  { label: 'Allocation modes', value: '3' },
]

export const WHO_WE_ARE = {
  badge: 'About',
  headline: 'About Symmetra Systems',
  subhead:
    'Symmetra Systems is a design studio of the Systems Realization Group at the Sustainable Manufacturing Systems Centre, Cranfield University. It turns research on knowledge-driven engineering into an offering that industry can test. Its first application supports Management of Change in asset-intensive and process settings.',
  cards: [
    {
      title: 'Connected engineering knowledge',
      body: 'An ontology and knowledge graph link assets, changes, hazards, reviews and work orders, so the consequences of a change can be traced instead of reassembled from separate documents.',
    },
    {
      title: 'Structured assessment',
      body: 'Each change is assessed the same way: affected assets and dependencies, risk and safety reviews, and the operational and cost evidence available.',
    },
    {
      title: 'Transparent decision allocation',
      body: 'A fixed, inspectable model recommends whether a decision should be AI-led, AI-supported or human-led, and shows the inputs, scores and reasons behind it.',
    },
  ],
}

export const WHY_US = {
  badge: 'The problem',
  headline: 'The change-assessment problems we address',
  subhead:
    'Change reviews often depend on disconnected documents, expert knowledge and manual cross-functional approvals. Each problem below is paired with how the platform responds.',
  problems: {
    title: 'What makes change assessment hard',
    items: [
      'Consequences of a change are hard to trace across assets and processes',
      'Review work is routed inconsistently, with unclear boundaries for AI',
      'Rationale and supporting evidence are fragmented',
      'An organisation cannot readily justify adopting another tool',
    ],
  },
  solutions: {
    title: 'How Symmetra responds',
    items: [
      'A knowledge graph surfaces dependencies and impacted items',
      'A decision-allocation recommendation built on risk, complexity, uncertainty and impact',
      'One case record: impact assessment, characterisation, scores and reasons, exportable',
      'A small, self-contained demonstrator that can be evaluated before any commitment',
    ],
  },
}

export const CAPABILITIES_INTRO = {
  badge: 'Platform',
  headline: 'Change intelligence and decision allocation in one place',
  subhead: 'Six connected workspaces, each grounded in the same FCC unit knowledge graph.',
}

export const CAPABILITIES = [
  { icon: 'form' as const, title: 'Smart Form', body: 'Describe a change and get suggested approvers, documents and review needs, drawn from matching historical changes.' },
  { icon: 'risk' as const, title: 'Risk & Impact', body: 'See the hazards, the directly and indirectly affected assets, and the mitigations for a proposed change.' },
  { icon: 'cost' as const, title: 'Cost Predictor', body: 'Indicative cost and downtime estimates with their ranges. Illustrative until benchmarked.' },
  { icon: 'bot' as const, title: 'MoCBot', body: 'Ask questions across change records, HAZOP, PSSR and lessons learned, answered from the knowledge graph.' },
  { icon: 'process' as const, title: 'Process Intelligence', body: 'Trace asset connectivity and see how downtime propagates through the unit.' },
  { icon: 'allocation' as const, title: 'Decision Allocation', body: 'Eight characteristics scored for risk, complexity, uncertainty and impact, giving an AI-led, AI-supported or human-led recommendation.' },
]

export const PROCESS = {
  badge: 'The journey',
  headline: 'From change request to recorded recommendation',
  subhead: 'One path through the platform for a proposed engineering change.',
  steps: [
    { step: '01', title: 'Change request', body: 'Describe the change: its type, the asset and what is proposed.' },
    { step: '02', title: 'Impacts and dependencies', body: 'The knowledge graph shows affected assets, safety reviews and history.' },
    { step: '03', title: 'Scores and allocation', body: 'Risk, complexity, uncertainty and impact are scored and an allocation is recommended.' },
    { step: '04', title: 'Engineer review', body: 'An engineer confirms or overrides each characteristic; the result updates with the reasons.' },
    { step: '05', title: 'Record', body: 'The characterisation, scores and recommendation are exported as a case record.' },
  ],
}

export const VALUES = {
  badge: 'Limits and safeguards',
  headline: 'What this is, and what it is not',
  subhead: 'The platform supports decisions about change. It does not make or authorise them.',
  cards: [
    {
      icon: 'shield' as const,
      title: 'Decision support, not authorisation',
      body: 'This is a decision-support prototype. It is not an autonomous authorisation system or a certified process-safety product, and it approves nothing on its own.',
    },
    {
      icon: 'authority' as const,
      title: 'A recommendation is not authority',
      body: 'Decision allocation is a computed recommendation for dividing decision work between people and AI. Decision authority, the delegated power to approve a change, is set by the organisation and stays with its accountable approvers.',
    },
    {
      icon: 'synthetic' as const,
      title: 'Synthetic data, no plant connection',
      body: 'The demonstration uses synthetic data for one FCC unit. There is no connection to live control systems and no safety-critical actuation.',
    },
    {
      icon: 'evidence' as const,
      title: 'Evidence and assumptions are shown',
      body: 'Each result shows where its inputs came from, what was assumed and what is missing. Cost and downtime figures are illustrative.',
    },
    {
      icon: 'calibration' as const,
      title: 'The model is not yet calibrated',
      body: 'The allocation model has an explicit rule, but its weights and thresholds are not empirically calibrated. Of the ten FCC scenarios, nine are human-led and one is AI-supported; none is AI-led.',
    },
  ],
}

export const FOOTER = {
  headline: 'Ready to explore the platform?',
  body: 'Smart Form, Risk & Impact, Cost Predictor, MoCBot, Process Intelligence and Decision Allocation, all grounded in one FCC unit knowledge graph.',
  line: 'MoC Intelligence Platform · SRG – Symmetra Systems Design Studio',
}
