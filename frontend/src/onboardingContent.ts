export const ONBOARDING_STORAGE_KEY = 'moc-onboarding-seen'

export const HERO = {
  brand: 'MoC Platform',
  tagline: 'FCC Unit · AI Decision Support',
  headline: 'Management of Change intelligence in one place',
  subhead:
    'A hybrid knowledge graph, retrieval pipeline, and ML decision-support stack for plant engineers from MoC intake to risk, cost, and lessons learned.',
  cta: 'Enter Platform',
  trust: 'Built for FCC Unit engineers · Grounded in your knowledge graph',
}

export const STATS = [
  { label: 'MoC Records', value: '10' },
  { label: 'Assets Mapped', value: '14+' },
  { label: 'Work Orders', value: '21' },
  { label: 'Incidents Linked', value: '4' },
]

export const CAPABILITIES = [
  { icon: 'form' as const, title: 'Smart Form', body: 'Embed descriptions and retrieve matching historical MoCs with structured suggestions.' },
  { icon: 'risk' as const, title: 'Risk & Impact', body: 'Surface hazards, severity, and downstream effects from the living graph.' },
  { icon: 'cost' as const, title: 'Cost Predictor', body: 'Estimate change cost with models trained on plant maintenance patterns.' },
  { icon: 'bot' as const, title: 'MoCBot', body: 'Ask grounded questions across MoCs, HAZOP, PSSR, and lessons learned.' },
]

export const PROCESS = {
  badge: 'Our Process',
  headline: 'A simple, scalable MoC intelligence flow',
  subhead: 'From intake to insight designed to grow with your FCC Unit.',
  steps: [
    { step: '01', title: 'Capture the change', body: 'Describe the MoC and match it against historical records with embeddings.' },
    { step: '02', title: 'Traverse the graph', body: 'Pull assets, hazards, approvers, and related work from Neo4j.' },
    { step: '03', title: 'Reason with context', body: 'GPT-4o synthesizes graph + vector hits into actionable engineering guidance.' },
    { step: '04', title: 'Decide with confidence', body: 'Risk, cost, and process views stay aligned as the plant evolves.' },
  ],
}

export const WHO_WE_ARE = {
  badge: 'Who We Are',
  headline: 'Who We Are',
  subhead:
    'The MoC Intelligence Platform helps FCC Unit teams turn scattered change records, hazards, and work orders into trusted, actionable guidance.',
  cards: [
    {
      title: 'Built for plant engineers',
      body: 'Production-grade MoC support for process, integrity, and operations teams  without standing up a full data science org.',
    },
    {
      title: 'Graph + AI grounded answers',
      body: 'Neo4j traversals and ChromaDB embeddings feed GPT-4o so suggestions cite real assets, hazards, and historical MoCs.',
    },
    {
      title: 'Designed around real workflows',
      body: 'Smart Form, Risk & Impact, Cost Predictor, MoCBot, and Process Intelligence mirror how MoC decisions are made on site.',
    },
  ],
}

export const VALUES = {
  badge: 'Our Values',
  headline: 'The Values Behind MoC',
  subhead: 'A few principles that keep Management of Change useful, reliable, and safe to scale.',
  cards: [
    {
      icon: 'lightbulb' as const,
      title: 'Clarity over complexity',
      body: 'We prefer simple, well-defined models that engineers can inspect, challenge, and maintain.',
    },
    {
      icon: 'handshake' as const,
      title: 'Trust and transparency',
      body: 'You always know which graph paths, embeddings, and historical MoCs shaped a recommendation.',
    },
    {
      icon: 'rocket' as const,
      title: 'Built for the long term',
      body: 'We optimize for stable pipelines and scalable graphs  not one-off dashboards that rot after handoff.',
    },
    {
      icon: 'users' as const,
      title: 'Decision-first thinking',
      body: 'Analytics should reduce risk and cycle time in the field, not just look impressive in a demo.',
    },
  ],
}

export const WHY_US = {
  badge: 'Why us',
  headline: 'What makes MoC Platform different',
  subhead:
    'We focus on analytics foundations plant teams can rely on  not disconnected spreadsheets or black-box tools.',
  problems: {
    title: 'Common MoC Problems',
    items: [
      'Manual reporting and spreadsheet sprawl',
      'Risk ratings that do not match across tools',
      'Hard-to-maintain change history',
      'Tribal knowledge lost when experts rotate',
      'Low trust in predicted cost and impact',
    ],
  },
  solutions: {
    title: 'With MoC Platform',
    items: [
      'Centralized FCC Unit knowledge graph',
      'Shared risk, asset, and MoC definitions',
      'Scalable retrieval across MoCs and incidents',
      'Automated grounding for MoCBot answers',
      'Confidence for engineering decisions',
    ],
  },
}
