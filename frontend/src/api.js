const BASE = '/api'

async function handle(res) {
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`API error ${res.status}: ${text}`)
  }
  return res.json()
}

export const api = {
  getWells: () => fetch(`${BASE}/wells`).then(handle),
  getNearby: (lat, lon, radiusKm, excludeId) =>
    fetch(`${BASE}/wells/nearby?lat=${lat}&lon=${lon}&radius_km=${radiusKm}${excludeId ? `&exclude_id=${excludeId}` : ''}`).then(handle),
  getWellDetail: (id) => fetch(`${BASE}/wells/${id}`).then(handle),
  getFormationRiskProfile: (id, radiusKm) => fetch(`${BASE}/wells/${id}/formation_risk_profile?radius_km=${radiusKm}`).then(handle),
  search: (q) => fetch(`${BASE}/search?q=${encodeURIComponent(q)}`).then(handle),
  listSampleReports: () => fetch(`${BASE}/sample_reports`).then(handle),
  getSampleReportText: (filename) => fetch(`${BASE}/sample_reports/${filename}`).then(handle),
  extractSample: (filename) => fetch(`${BASE}/extract_sample/${filename}`, { method: 'POST' }).then(handle),
  predictRisk: (payload) =>
    fetch(`${BASE}/predict/risk`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(handle),
}
