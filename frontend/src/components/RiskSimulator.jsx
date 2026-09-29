import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api.js'

const FORMATIONS = ['Alluvium', 'Girujan Clay', 'Tipam Sandstone', 'Barail Group', 'Basement (Pre-Tertiary)']

export default function RiskSimulator({ wells }) {
  const [activeWellId, setActiveWellId] = useState('')
  const [formation, setFormation] = useState('Barail Group')
  const [depth, setDepth] = useState(1900)
  const [rop, setRop] = useState(14)
  const [mudWeight, setMudWeight] = useState(1.18)
  const [torque, setTorque] = useState(24)
  const [pressure, setPressure] = useState(1.4)
  const [radiusKm, setRadiusKm] = useState(15)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [autoSim, setAutoSim] = useState(false)
  const intervalRef = useRef(null)

  const activeWell = wells.find((w) => w.id === Number(activeWellId))

  const predict = async (overrideDepth) => {
    setLoading(true)
    try {
      const payload = {
        formation,
        depth_m: overrideDepth ?? depth,
        rop_m_hr: rop,
        mud_weight_sg: mudWeight,
        torque_knm: torque,
        downhole_pressure_sg: pressure,
        radius_km: radiusKm,
      }
      if (activeWell) {
        payload.lat = activeWell.latitude
        payload.lon = activeWell.longitude
      }
      const res = await api.predictRisk(payload)
      setResult(res)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (autoSim) {
      intervalRef.current = setInterval(() => {
        setDepth((d) => {
          const next = d + 15 > 3100 ? 200 : d + 15
          predict(next)
          return next
        })
      }, 1500)
    } else {
      clearInterval(intervalRef.current)
    }
    return () => clearInterval(intervalRef.current)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSim, formation, rop, mudWeight, torque, pressure, radiusKm, activeWellId])

  return (
    <div style={{ padding: 24, width: '100%', overflowY: 'auto' }}>
      <h2 style={{ marginTop: 0 }}>Predictive Risk & Proactive Alerts</h2>
      <p style={{ color: 'var(--text-dim)', fontSize: 13, maxWidth: 800 }}>
        A RandomForest model trained on drilling-parameter patterns estimates the probability of a mud loss,
        stuck-pipe, or kick event at the current depth/formation, then cross-references live offset-well history
        to generate a proactive recommendation — the same alert an engineer would want the moment eRTMAC crosses
        a risky interval.
      </p>

      <div style={{ display: 'flex', gap: 24 }}>
        <div style={{ flex: '0 0 320px' }} className="panel">
          <div className="field-row">
            <label>Active well (for offset-radius context)</label>
            <select value={activeWellId} onChange={(e) => setActiveWellId(e.target.value)}>
              <option value="">— none —</option>
              {wells.map((w) => <option key={w.id} value={w.id}>{w.name} ({w.field_name})</option>)}
            </select>
          </div>
          <div className="field-row">
            <label>Formation</label>
            <select value={formation} onChange={(e) => setFormation(e.target.value)}>
              {FORMATIONS.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
          </div>
          <div className="field-row">
            <label>Current depth: {depth} m</label>
            <input type="range" min="50" max="3100" value={depth} onChange={(e) => setDepth(Number(e.target.value))} />
          </div>
          <div className="field-row">
            <label>Rate of penetration: {rop} m/hr</label>
            <input type="range" min="4" max="35" value={rop} onChange={(e) => setRop(Number(e.target.value))} />
          </div>
          <div className="field-row">
            <label>Mud weight: {mudWeight} SG</label>
            <input type="range" min="1.05" max="1.85" step="0.01" value={mudWeight} onChange={(e) => setMudWeight(Number(e.target.value))} />
          </div>
          <div className="field-row">
            <label>Torque: {torque} kNm</label>
            <input type="range" min="8" max="32" value={torque} onChange={(e) => setTorque(Number(e.target.value))} />
          </div>
          <div className="field-row">
            <label>Downhole pressure gradient: {pressure} SG-equiv</label>
            <input type="range" min="0.9" max="1.6" step="0.01" value={pressure} onChange={(e) => setPressure(Number(e.target.value))} />
          </div>
          <div className="field-row">
            <label>Offset-well search radius: {radiusKm} km</label>
            <input type="range" min="5" max="40" value={radiusKm} onChange={(e) => setRadiusKm(Number(e.target.value))} />
          </div>

          <button onClick={() => predict()} disabled={loading} style={{ width: '100%', marginBottom: 8 }}>
            {loading ? 'Evaluating…' : 'Predict Risk'}
          </button>
          <button
            className="secondary"
            style={{ width: '100%' }}
            onClick={() => setAutoSim((s) => !s)}
          >
            {autoSim ? '⏸ Stop live drilling simulation' : '▶ Start live drilling simulation'}
          </button>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          {!result && <div className="empty-state">Set parameters and click "Predict Risk", or start the live simulation to watch alerts trigger as depth increases.</div>}
          {result && (
            <>
              {result.risk_level === 'high' && (
                <div className="alert-banner">
                  ⚠ PROACTIVE ALERT — high-risk interval detected at {depth}m. {result.recommendation}
                </div>
              )}
              <div className={`risk-gauge ${result.risk_level}`}>
                <div className="pct">{(result.risk_probability * 100).toFixed(1)}%</div>
                <div>Predicted risk probability — <strong>{result.risk_level.toUpperCase()}</strong></div>
              </div>

              <div className="section-title">Recommendation</div>
              <div className="panel" style={{ background: 'var(--panel-2)', fontSize: 13 }}>{result.recommendation}</div>

              <div className="section-title">Similar offset-well events (institutional memory)</div>
              {result.similar_offset_events.length === 0 && <div className="empty-state">No matching offset-well events found in this radius/formation window.</div>}
              {result.similar_offset_events.map((e) => (
                <div className="event-card" key={e.id}>
                  <div className="meta">
                    <span className={`badge ${e.severity}`}>{e.severity}</span>{' '}
                    <strong>{e.well_name}</strong> ({e.field_name}){e.distance_km != null ? ` · ${e.distance_km} km away` : ''} &middot; {e.depth_m}m &middot; {e.date}
                  </div>
                  {e.description}
                  <div className="mitigation">Mitigation: {e.mitigation}</div>
                </div>
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
