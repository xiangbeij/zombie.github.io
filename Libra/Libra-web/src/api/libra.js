import axios from 'axios'

const isProd = import.meta.env.PROD
const BASE_URL = isProd ? '/api' : 'http://localhost:5188/api'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
})

// ── Scan ──
export const startScan = (url, scanType) =>
  api.post('/scan', { url, scan_type: scanType })

export const getScanStatus = (taskId) =>
  api.get(`/scan/${taskId}`)

export const listTasks = (limit = 100) =>
  api.get(`/tasks?limit=${limit}`)

export const deleteTask = (taskId) =>
  api.delete(`/scan/${taskId}`)

// ── Batch Scan ──
export const createBatch = (urls, scanType) =>
  api.post('/batch', { urls, scan_type: scanType })

export const getBatchStatus = (batchId) =>
  api.get(`/batch/${batchId}`)

export const listBatches = () =>
  api.get('/batch')

export const deleteBatch = (batchId) =>
  api.delete(`/batch/${batchId}`)

// ── Schedule ──
export const createSchedule = (data) =>
  api.post('/schedule', data)

export const listSchedules = () =>
  api.get('/schedule')

export const updateSchedule = (jobId, data) =>
  api.put(`/schedule/${jobId}`, data)

export const deleteSchedule = (jobId) =>
  api.delete(`/schedule/${jobId}`)

export const triggerScheduleNow = (jobId) =>
  api.post(`/schedule/${jobId}/run`)

// ── Report ──
export const exportReport = (taskId, format = 'json') =>
  api.get(`/report/${taskId}?format=${format}`, { responseType: format === 'json' ? 'json' : 'blob' })

export const getReportUrl = (taskId, format) => {
  const base = isProd ? '/api' : 'http://localhost:5188/api'
  return `${base}/report/${taskId}?format=${format}`
}

// ── AI Analysis ──
export const aiAnalyze = (scanResult) =>
  api.post('/ai/analyze', { result: scanResult })

// ── Stats & Rules ──
export const getStats = () => api.get('/stats')
export const getRules = () => api.get('/rules')
export const healthCheck = () => api.get('/health')

// ── Dashboard ──
export const getThreatSummary = () => api.get('/threat-summary')
export const getAssetStats = () => api.get('/assets/stats')
export const getAlerts = () => api.get('/assets/alerts')
export const getDashboardStats = () => api.get('/dashboard/stats')

// ── Assets ──
export const getAssets = (query) =>
  api.get(`/assets?${query}`)

export const addAssetApi = (data) =>
  api.post('/assets', data)

export const updateAssetTitleApi = (assetId, title) =>
  api.put(`/assets/${assetId}/title`, { title })

export const deleteAssetApi = (assetId) =>
  api.delete(`/assets/${assetId}`)

export const exportAssetsApi = () =>
  api.get('/assets/export', { responseType: 'blob' })

export const batchImportAssetsApi = (assets) =>
  api.post('/assets/batch', { assets })

// ── IP Ranges ──
export const getIpRanges = () => api.get('/assets/ip-ranges')

export const addIpRangeApi = (data) =>
  api.post('/assets/ip-ranges', data)

export const deleteIpRangeApi = (rangeId) =>
  api.delete(`/assets/ip-ranges/${rangeId}`)

export const scanIpRangeApi = (rangeId, ipRange, ports) =>
  api.post('/assets/scan/ip', { range_id: rangeId, ip_range: ipRange, ports })

export const scanDomainApi = (domain, recursive) =>
  api.post('/assets/scan/domain', { domain, recursive })

// ── Sites ──
export const getSites = () => api.get('/sites')

export const getSite = (id) => api.get(`/sites/${id}`)

export const createSite = (data) => api.post('/sites', data)

export const updateSite = (id, data) => api.put(`/sites/${id}`, data)

export const deleteSite = (id) => api.delete(`/sites/${id}`)

export const checkSiteSsl = (id) => api.post(`/sites/${id}/ssl-check`)

// ── Site Monitor ──
export const getSiteMonitors = (params = {}) => {
  const { page = 1, page_size = 50, search = '' } = params
  const p = new URLSearchParams({ page, page_size, search })
  return api.get('/site-monitor?' + p.toString())
}

export const getSiteMonitorStats = () => api.get('/site-monitor/stats')

export const createSiteMonitor = (data) => api.post('/site-monitor', data)

export const updateSiteMonitor = (id, data) => api.put('/site-monitor/' + id, data)

export const deleteSiteMonitor = (id) => api.delete('/site-monitor/' + id)

export const checkSiteMonitor = (id) => api.post('/site-monitor/' + id + '/check')

export const checkAllSiteMonitors = () => api.post('/site-monitor/check-all')

export const getSiteMonitorHistory = (id, limit = 20) =>
  api.get('/site-monitor/' + id + '/history?limit=' + limit)

export default api
