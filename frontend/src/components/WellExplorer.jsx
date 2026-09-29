import React, { useEffect, useState } from 'react'
import MapView from './MapView.jsx'
import { api } from '../api.js'

const EVENT_LABELS = {
  mud_loss: 'Mud Loss',
  kick: 'Kick',
  stuck_pipe: 'Stuck Pipe',
  cementing_issue: 'Cementing Issue',
  torque_spike: 'Torque Spike',
}

export default function WellExplorer({ wells }) {
  const [selectedWell, setSelectedWell] = useState(null)
  const [wellDetail, setWellDetail] = useState(null)
  const [nearby, setNearby] = useState([])
  const [radiusKm, setRadiusKm] = useState(15)
  const [riskProfile, setRiskProfile] = useState(null)

  useEffect(() => {
    if (!selectedWell) return
    api.getWellDetail(selectedWell.id).then(setWellDetail)
    api.getNearby(selectedWell.latitude, selectedWell.longitude, radiusKm, selectedWell.id).then(setNearby)
    api.getFormationRiskProfile(selectedWell.id, radiusKm).then(setRiskProfile)
  }, [selectedWell, radiusKm])

  return (
    <div className="two-col">
      <div className="col-map">
        <MapView wells={wells} selectedWell={selectedWell} onSelectWell={setSelectedWell} radiusKm={radiusKm} />
      </div>
      <div className="col-side panel">
        {!selectedWell && (
          <div className="empty-state">Click a well on the map to view its offset-well intelligence: formation tops, historical events, and nearby wells within a search radius.</div>
        )}
        {selectedWell && wellDetail && (
          <>
            <h3 style={{ marginTop: 0 }}>{wellDetail.name} <span className="badge low" style={{ marginLeft: 6 }}>{wellDetail.status}</span></h3>
            <div style={{ color: 'var(--text-dim)', fontSize: 13, marginBottom: 10 }}>
              {wellDetail.field_name} field &middot; TD {wellDetail.total_depth_m}m &middot; Spud {wellDetail.spud_date}
            </div>

            <div className="field-row">
              <label>Nearby-well search radius: {radiusKm} km</label>
              <input type="range" min="5" max="40" value={radiusKm} onChange={(e) => setRadiusKm(Number(e.target.value))} />
            </div>

            <div className="section-title">Nearby wells ({nearby.length})</div>
            {nearby.length === 0 && <div className="empty-state">No offset wells within {radiusKm} km.</div>}
            {nearby.map((w) => (
              <div key={w.id} className="event-card" style={{ cursor: 'pointer' }} onClick={() => setSelectedWell(w)}>
                <strong>{w.name}</strong> &middot; {w.distance_km} km away
                <div className="meta">{w.field_name} &middot; {w.status} &middot; TD {w.total_depth_m}m</div>
              </div>
            ))}

            <div className="section-title">Formation risk profile — offset wells within {radiusKm} km</div>
            {!riskProfile && <div className="empty-state">Loading…</div>}
            {riskProfile && riskProfile.formations.length === 0 && (
              <div className="empty-state">No offset-well events recorded in this radius.</div>
            )}
            {riskProfile && riskProfile.formations.map((f) => {
              const maxTotal = riskProfile.formations[0].total || 1
              return (
                <div key={f.formation} style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                    <span>{f.formation}</span>
                    <span style={{ color: 'var(--text-dim)' }}>{f.total} events</span>
                  </div>
                  <div style={{ background: 'var(--panel-2)', borderRadius: 4, height: 8, overflow: 'hidden' }}>
                    <div style={{
                      width: `${(f.total / maxTotal) * 100}%`,
                      height: '100%',
                      background: f.by_severity.high > 0 ? 'var(--danger)' : f.by_severity.medium > 0 ? 'var(--warning)' : 'var(--safe)',
                    }} />
                  </div>
                </div>
              )
            })}
            {riskProfile && (
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 6 }}>
                Correlated across {riskProfile.offset_well_count} offset well{riskProfile.offset_well_count === 1 ? '' : 's'} in this radius — this is the field-level pattern to check before spudding here, independent of this well's own history.
              </div>
            )}

            <div className="section-title">Formation sequence</div>
            <table>
              <thead><tr><th>Formation</th><th>Interval (m)</th></tr></thead>
              <tbody>
                {wellDetail.formation_sequence.split(',').map((f, i) => {
                  const [name, range] = f.split(':')
                  return <tr key={i}><td>{name}</td><td>{range}</td></tr>
                })}
              </tbody>
            </table>

            <div className="section-title">Historical drilling events ({wellDetail.events.length})</div>
            {wellDetail.events
              .slice()
              .sort((a, b) => a.depth_m - b.depth_m)
              .map((e) => (
                <div className="event-card" key={e.id}>
                  <div className="meta">
                    <span className={`badge ${e.severity}`}>{e.severity}</span>{' '}
                    {EVENT_LABELS[e.event_type] || e.event_type} &middot; {e.depth_m}m &middot; {e.formation} &middot; {e.date}
                  </div>
                  {e.description}
                  <div className="mitigation">Mitigation: {e.mitigation}</div>
                </div>
              ))}
          </>
        )}
      </div>
    </div>
  )
}
