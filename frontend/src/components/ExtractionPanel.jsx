import React, { useEffect, useState } from 'react'
import { api } from '../api.js'

export default function ExtractionPanel() {
  const [reports, setReports] = useState([])
  const [selected, setSelected] = useState('')
  const [preview, setPreview] = useState(null) // { kind, raw_text? , image_data_url? }
  const [result, setResult] = useState(null)   // { ocr_used, raw_text, extracted }
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    api.listSampleReports().then((r) => {
      setReports(r)
      if (r.length) setSelected(r[0])
    })
  }, [])

  useEffect(() => {
    if (!selected) return
    api.getSampleReportText(selected).then(setPreview)
    setResult(null)
  }, [selected])

  const runExtraction = async () => {
    setLoading(true)
    try {
      const res = await api.extractSample(selected)
      setResult(res)
    } finally {
      setLoading(false)
    }
  }

  const isImage = preview?.kind === 'image'

  return (
    <div style={{ padding: 24, width: '100%', overflowY: 'auto' }}>
      <h2 style={{ marginTop: 0 }}>AI Document Extraction — WCR / DDR Ingestion</h2>
      <p style={{ color: 'var(--text-dim)', fontSize: 13, maxWidth: 800 }}>
        Turns Well Completion Reports and Daily Drilling Reports into structured, queryable data: formation
        tops, casing program, mud program, and NPT (non-productive time) events. Scanned/image reports run
        through a real Tesseract OCR pass before the same extraction logic parses the result — pick the
        "_scanned.png" report below to see the full image → OCR → structured-JSON pipeline.
      </p>

      <div style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 16 }}>
        <select value={selected} onChange={(e) => setSelected(e.target.value)}>
          {reports.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <button onClick={runExtraction} disabled={loading}>
          {loading ? 'Extracting…' : isImage ? 'Run OCR + AI Extraction' : 'Run AI Extraction'}
        </button>
        {result && (
          <span className={`badge ${result.ocr_used ? 'medium' : 'low'}`}>
            {result.ocr_used ? 'Tesseract OCR used' : 'Digital text (no OCR needed)'}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        {isImage && (
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="section-title">1. Scanned document (input)</div>
            {preview?.image_data_url && (
              <img src={preview.image_data_url} alt="scanned report" style={{ width: '100%', border: '1px solid var(--border)', borderRadius: 6 }} />
            )}
          </div>
        )}

        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="section-title">{isImage ? '2. Raw OCR output' : '1. Raw report (input)'}</div>
          <div className="raw-text">
            {isImage ? (result?.raw_text ?? 'Run OCR + AI Extraction to see the raw text Tesseract recovers from the image above.') : preview?.raw_text}
          </div>
        </div>

        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="section-title">{isImage ? '3. Structured extraction (output)' : '2. Structured extraction (output)'}</div>
          {!result && <div className="empty-state">Run extraction to see structured JSON output.</div>}
          {result && (
            <div className="panel" style={{ background: 'var(--panel-2)' }}>
              <p><strong>Well:</strong> {result.extracted.well_name} &middot; <strong>Type:</strong> {result.extracted.report_type}</p>

              <div className="section-title">Formation tops</div>
              <table>
                <thead><tr><th>Formation</th><th>Top depth (m)</th></tr></thead>
                <tbody>
                  {result.extracted.formation_tops.map((f, i) => <tr key={i}><td>{f.formation}</td><td>{f.depth_m}</td></tr>)}
                </tbody>
              </table>

              <div className="section-title">Casing program</div>
              <table>
                <thead><tr><th>Size</th><th>Set depth (m)</th></tr></thead>
                <tbody>
                  {result.extracted.casing_program.map((c, i) => <tr key={i}><td>{c.size}</td><td>{c.set_depth_m}</td></tr>)}
                </tbody>
              </table>

              <div className="section-title">NPT events detected</div>
              {result.extracted.npt_events.map((e, i) => (
                <div className="event-card" key={i}>
                  <div className="meta">{e.event_type.replace('_', ' ')}{e.depth_m ? ` · ${e.depth_m}m` : ''}</div>
                  {e.description}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
