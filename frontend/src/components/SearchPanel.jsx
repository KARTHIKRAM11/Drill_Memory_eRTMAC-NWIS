import React, { useState } from 'react'
import { api } from '../api.js'

const SUGGESTIONS = ['stuck pipe', 'mud loss', 'Barail Group', 'kick', 'cementing', 'torque']

export default function SearchPanel() {
  const [q, setQ] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const runSearch = async (term) => {
    const query = term ?? q
    if (!query || query.length < 2) return
    setQ(query)
    setLoading(true)
    try {
      const res = await api.search(query)
      setResults(res)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto', width: '100%', overflowY: 'auto' }}>
      <h2 style={{ marginTop: 0 }}>Searchable Drilling Knowledge Repository</h2>
      <p style={{ color: 'var(--text-dim)', fontSize: 13 }}>
        Search across every extracted historical drilling event — mud losses, kicks, stuck pipe, cementing issues,
        torque spikes — and their recorded mitigations, across all offset wells in the field.
      </p>
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          type="text"
          placeholder="Search e.g. 'stuck pipe in Barail Group'..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && runSearch()}
          style={{ flex: 1 }}
        />
        <button onClick={() => runSearch()}>Search</button>
      </div>
      <div className="pill-row">
        {SUGGESTIONS.map((s) => (
          <button key={s} className="secondary" onClick={() => runSearch(s)}>{s}</button>
        ))}
      </div>

      {loading && <div className="empty-state">Searching…</div>}
      {!loading && results && results.length === 0 && <div className="empty-state">No historical events match "{q}".</div>}
      {!loading && results && results.map((e) => (
        <div className="event-card" key={e.id}>
          <div className="meta">
            <span className={`badge ${e.severity}`}>{e.severity}</span>{' '}
            <strong>{e.well_name}</strong> ({e.field_name}) &middot; {e.formation} &middot; {e.depth_m}m &middot; {e.date}
          </div>
          {e.description}
          <div className="mitigation">Mitigation: {e.mitigation}</div>
        </div>
      ))}
    </div>
  )
}
