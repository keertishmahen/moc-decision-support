import axios from 'axios'

const api = axios.create({ baseURL: '/api', timeout: 180_000 })

// Add response interceptor to surface errors clearly
api.interceptors.response.use(
  r => r,
  err => {
    const detail = err?.response?.data?.detail
    if (detail) {
      return Promise.reject(new Error(typeof detail === 'string' ? detail : JSON.stringify(detail)))
    }
    return Promise.reject(err)
  }
)

export const getHealth = () => api.get('/health').then(r => r.data)
export const getAssets = () => api.get('/assets').then(r => r.data)
export const getMocs   = () => api.get('/mocs').then(r => r.data)

export const prefillForm = (body: { change_type: string; asset_id: string; description: string }) =>
  api.post('/forms/prefill', body).then(r => r.data)

export const analyseRisk = (body: { change_type: string; asset_id: string; description: string }) =>
  api.post('/risk/analyse', body).then(r => r.data)

export const predictCost = (body: {
  change_type: string; asset_id: string; asset_category: string
  risk_level: string; description: string
}) => api.post('/cost/predict', body).then(r => r.data)

export const sendChat = (body: { message: string; asset_id?: string }) =>
  api.post('/chat', body).then(r => r.data)

export const resetChat = () => api.post('/chat/reset').then(r => r.data)

export const getGraphContext = (body: { query: string; asset_id?: string; moc_id?: string }) =>
  api.post('/graph/context', body).then(r => r.data)

// ── Enhancement 1: Process Asset Connectivity ──────────────────────────────
export const getTopology = () =>
  api.get('/topology').then(r => r.data)

export const getConnectivity = (body: { asset_id: string }) =>
  api.post('/connectivity', body).then(r => r.data)

export const getAllAssetsConnectivity = () =>
  api.get('/assets/connectivity').then(r => r.data)

// ── Enhancement 2: Dynamic Downtime Propagation ────────────────────────────
export const propagateDowntime = (body: { asset_id: string; downtime_hours: number; max_depth?: number }) =>
  api.post('/downtime/propagate', body).then(r => r.data)

export const getPropagationMatrix = () =>
  api.get('/downtime/matrix').then(r => r.data)

export const propagateDowntimeFromMoc = (moc_id: string) =>
  api.get(`/downtime/moc/${moc_id}`).then(r => r.data)

// ── Enhancement 3: Agent-Based Execution ──────────────────────────────────
export const runAgent = (body: { query: string; max_iterations?: number }) =>
  api.post('/agent', body).then(r => r.data)
