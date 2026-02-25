import React from 'react'

interface Props {
  visible: boolean
  onClose: () => void
  title?: string
  data?: any
}

export default function SearchModal({ visible, onClose, title, data }: Props) {
  if (!visible) return null

  return (
    <div className="modal-overlay" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="modal" style={{ width: '80%', maxWidth: 900, background: '#fff', borderRadius: 8, padding: '1rem', boxShadow: '0 4px 20px rgba(0,0,0,0.2)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <h3 style={{ margin: 0 }}>{title || 'Result'}</h3>
          <button onClick={onClose} style={{ border: 'none', background: 'transparent', fontSize: '1.25rem', cursor: 'pointer' }}>✕</button>
        </div>
        <div style={{ marginTop: '0.75rem', maxHeight: '60vh', overflow: 'auto' }}>
          {data && data.row && typeof data.row === 'object' ? (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '8px' }}>Column</th>
                    <th style={{ textAlign: 'left', borderBottom: '1px solid #eee', padding: '8px' }}>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(data.row).map(([k, v]) => {
                    const isMatched = Array.isArray(data.matched_columns) && data.matched_columns.includes(k)
                    const display = v && typeof v === 'object' ? JSON.stringify(v) : String(v === null || v === undefined ? '' : v)
                    return (
                      <tr key={k} style={{ background: isMatched ? '#fff8e1' : 'transparent' }}>
                        <td style={{ padding: '8px', verticalAlign: 'top', fontWeight: isMatched ? 700 : 500 }}>{k}</td>
                        <td style={{ padding: '8px', verticalAlign: 'top', whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{display}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>{JSON.stringify(data, null, 2)}</pre>
          )}
        </div>
      </div>
    </div>
  )
}
