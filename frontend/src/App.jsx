import React, { useEffect, useState } from 'react'
import WellExplorer from './components/WellExplorer.jsx'
import SearchPanel from './components/SearchPanel.jsx'
import ExtractionPanel from './components/ExtractionPanel.jsx'
import RiskSimulator from './components/RiskSimulator.jsx'
import { api } from './api.js'

const TABS = [
  { id: 'map', label: 'Offset Well Map' },
  { id: 'search', label: 'Knowledge Search' },
  { id: 'extract', label: 'Document Extraction (AI/OCR)' },
  { id: 'risk', label: 'Predictive Risk & Alerts' },
]

export default function App() {
  const [tab, setTab] = useState('map')
  const [wells, setWells] = useState([])

  useEffect(() => {
    api.getWells().then(setWells).catch(() => {})
  }, [])

  return (
    <div className="app">
      <div className="topbar">
        <div>
          <h1>eRTMAC-NWIS · <span>DrillMemory</span></h1>
        </div>
        <div className="subtitle">{wells.length} wells indexed</div>
      </div>
      <div className="tabs">
        {TABS.map((t) => (
          <div key={t.id} className={`tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
            {t.label}
          </div>
        ))}
      </div>
      <div className="main">
        {tab === 'map' && <WellExplorer wells={wells} />}
        {tab === 'search' && <SearchPanel />}
        {tab === 'extract' && <ExtractionPanel />}
        {tab === 'risk' && <RiskSimulator wells={wells} />}
      </div>
    </div>
  )
}
