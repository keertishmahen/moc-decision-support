/**
 * The pages of the dashboard, in navigation order: the single source for the sidebar, the
 * top bar, the routes (navigation.ts builds TAB_PATHS from this list) and code splitting
 * (each page is loaded on first visit).
 */
import { lazy, type ComponentType, type LazyExoticComponent } from 'react'
import {
  Bot, CircleDollarSign, ClipboardList, GitBranch, LayoutDashboard, Scale, TriangleAlert, Workflow,
  type LucideIcon,
} from 'lucide-react'

export type PageGroup = 'Home' | 'Assess' | 'Intelligence'

export interface Page {
  id: string
  path: string
  label: string
  description: string
  icon: LucideIcon
  group: PageGroup
  component: LazyExoticComponent<ComponentType>
}

export const PAGE_GROUPS: PageGroup[] = ['Home', 'Assess', 'Intelligence']

export const PAGES: Page[] = [
  {
    id: 'overview', path: '/app/overview', label: 'Overview', group: 'Home', icon: LayoutDashboard,
    description: 'Live summary of the knowledge graph, recorded changes and decision allocations',
    component: lazy(() => import('./tabs/Overview')),
  },
  {
    id: 'case', path: '/app/case', label: 'Change Case', group: 'Assess', icon: Workflow,
    description: 'One change end to end: what happens, who should decide, and why to trust it',
    component: lazy(() => import('./tabs/ChangeCase')),
  },
  {
    id: 'smart-form', path: '/app/smart-form', label: 'Smart Form', group: 'Assess', icon: ClipboardList,
    description: 'An MoC form prefilled from the knowledge graph',
    component: lazy(() => import('./tabs/SmartForm')),
  },
  {
    id: 'risk', path: '/app/risk', label: 'Risk & Impact', group: 'Assess', icon: TriangleAlert,
    description: 'Risks, hazards and the equipment a change affects',
    component: lazy(() => import('./tabs/RiskAnalysis')),
  },
  {
    id: 'cost', path: '/app/cost', label: 'Cost Predictor', group: 'Assess', icon: CircleDollarSign,
    description: 'Cost and downtime estimates with ranges',
    component: lazy(() => import('./tabs/CostPredictor')),
  },
  {
    id: 'mocbot', path: '/app/mocbot', label: 'MoCBot', group: 'Intelligence', icon: Bot,
    description: 'Ask about the plant, its assets and past changes',
    component: lazy(() => import('./tabs/MoCBot')),
  },
  {
    id: 'process', path: '/app/process', label: 'Process Intelligence', group: 'Intelligence', icon: GitBranch,
    description: 'Connectivity, downtime propagation and agent reasoning',
    component: lazy(() => import('./tabs/ProcessIntelligence')),
  },
  {
    id: 'allocation', path: '/app/allocation', label: 'Decision Allocation', group: 'Intelligence', icon: Scale,
    description: 'Whether a change should be AI-led, AI-supported or human-led',
    component: lazy(() => import('./tabs/DecisionAllocation')),
  },
]
