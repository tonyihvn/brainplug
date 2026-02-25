import React, { useState } from 'react'
import { ActionData } from '../types'
import { FiCheck, FiX, FiDownload } from 'react-icons/fi'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { showAlert } from './swal'

type Step = ActionData

interface ActionBoxProps {
  action?: ActionData | { type: string; steps: Step[] }
  onConfirm: (action: ActionData | { type: string; steps: Step[] }) => void
  onTogglePopout?: () => void
}

export default function ActionBox({ action, onConfirm, onTogglePopout }: ActionBoxProps) {
  const [viewMode, setViewMode] = useState<'table' | 'chart'>('table')
  const colors = ['#4f46e5', '#06b6d4', '#f97316', '#10b981', '#ef4444']
  const [showRaw, setShowRaw] = useState(false)
  if (!action) {
    return (
      <div className="action-box">
        <div className="action-box-header">
          <span>⚡ Suggested Action</span>
        </div>
        <div className="action-box-empty">
          No action suggested yet. Send a message to get started.
        </div>
      </div>
    )
  }

  const handleConfirm = () => {
    onConfirm(action)
  }

  // Helpers
  const isISODate = (s: string) => {
    return typeof s === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(s)
  }

  const formatCell = (val: any) => {
    if (val === null || typeof val === 'undefined') return ''
    if (typeof val === 'number') return new Intl.NumberFormat().format(val)
    if (isISODate(String(val))) {
      try {
        return new Date(String(val)).toLocaleString()
      } catch (e) {
        return String(val)
      }
    }
    return String(val)
  }

  const rowsToCSV = (columns: string[], rows: any[]) => {
    const esc = (v: any) => '"' + String(v ?? '').replace(/"/g, '""') + '"'
    const header = columns.map(c => esc(c)).join(',')
    const body = rows.map(r => columns.map(c => esc(r[c])).join(',')).join('\n')
    return `${header}\n${body}`
  }

  const downloadCSV = (columns: string[], rows: any[], filename = 'result.csv') => {
    const csv = rowsToCSV(columns, rows)
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const exportExcel = async (columns: string[], rows: any[], filename = 'result.xlsx') => {
    try {
      const XLSX = await import('xlsx')
      const ws_data = [columns, ...rows.map(r => columns.map(c => r[c]))]
      const ws = XLSX.utils.aoa_to_sheet(ws_data)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
      XLSX.writeFile(wb, filename)
    } catch (e) {
      // fallback to CSV if xlsx not installed
      downloadCSV(columns, rows, filename.replace(/\.xlsx?$/, '.csv'))
    }
  }

  const exportWord = (columns: string[], rows: any[], filename = 'result.doc') => {
    // Simple HTML-based Word document (works in Word as import)
    const html = `<!doctype html><html><head><meta charset="utf-8"><title>Export</title></head><body><table border="1" style="border-collapse:collapse">` +
      `<thead><tr>${columns.map(c => `<th style="padding:4px">${c}</th>`).join('')}</tr></thead><tbody>` +
      rows.map(r => `<tr>${columns.map(c => `<td style="padding:4px">${String(r[c] ?? '')}</td>`).join('')}</tr>`).join('') +
      `</tbody></table></body></html>`
    const blob = new Blob([html], { type: 'application/msword' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  const exportPDF = async (columns: string[], rows: any[], filename = 'result.pdf') => {
    try {
      const { jsPDF } = await import('jspdf')
      const doc = new jsPDF({ unit: 'pt' })
      const lineHeight = 14
      let y = 40
      doc.setFontSize(12)
      doc.text('Export', 40, 24)
      // header
      doc.setFontSize(10)
      doc.text(columns.join(' | '), 40, y)
      y += lineHeight
      for (const r of rows.slice(0, 200)) {
        doc.text(columns.map(c => String(r[c] ?? '')).join(' | '), 40, y)
        y += lineHeight
        if (y > 750) {
          doc.addPage(); y = 40
        }
      }
      doc.save(filename)
    } catch (e) {
      // fallback: download txt
      const txt = [columns.join('\t'), ...rows.map(r => columns.map(c => String(r[c] ?? '')).join('\t'))].join('\n')
      const blob = new Blob([txt], { type: 'text/plain;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename.replace(/\.pdf$/, '.txt')
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    }
  }

  const useInNextPrompt = async (columns: string[], rows: any[]) => {
    try {
      const payload = { columns, rows }
      await navigator.clipboard.writeText(JSON.stringify(payload))
        showAlert('Copied', 'Result copied to clipboard. You can paste it into the prompt or use "Attach" in chat.', 'success')
    } catch (e) {
        showAlert('Copy failed', 'Could not copy to clipboard — please use Download to save and attach manually.', 'error')
    }
  }

  return (
    <div className="action-box">
      <div className="action-box-header">
        <span>⚡ Suggested Action</span>
        <span style={{ marginLeft: 'auto', fontSize: '0.875rem', color: '#718096', display: 'flex', gap: 8, alignItems: 'center' }}>
          Confidence: {((action as any).confidence) || 'medium'}
          <button title="Pop out" className="btn-secondary" onClick={() => onTogglePopout && onTogglePopout()} style={{ marginLeft: 8 }}>
            Pop out
          </button>
        </span>
      </div>

      <div className="action-box-content">
        {/* Results are displayed in the Results panel only. */}
        {((action as any).result) && (
          <div style={{ marginBottom: 12, padding: 8, border: '1px dashed #e2e8f0', borderRadius: 6, color: '#475569' }}>
            Results will appear in the Results panel. Use the Results panel to view, export, and operate on the data.
          </div>
        )}

        {/* If procedural plan (has steps), show step list */}
        {Array.isArray((action as any).steps) ? (
          <div>
            <strong>Planned Steps:</strong>
            <ol style={{ marginTop: 8 }}>
              {(action as any).steps.map((s: Step, idx: number) => (
                <li key={idx} style={{ marginBottom: 8 }}>
                  <div><strong>Type:</strong> {s.type}</div>
                  {s.sql_query && <div style={{ marginTop: 4 }}><strong>Query:</strong>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: '0.25rem' }}>{s.sql_query}</pre>
                  </div>}
                  {s.parameters && <div style={{ marginTop: 4 }}><strong>Parameters:</strong>
                    <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: '0.25rem' }}>{s.parameters}</pre>
                  </div>}
                </li>
              ))}
            </ol>

            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn-confirm" onClick={() => onConfirm(action)} style={{ flex: 1 }}>
                <FiCheck style={{ marginRight: '0.5rem' }} />
                Confirm All Steps
              </button>
            </div>
          </div>
        ) : (
          <div>
            <div>
              <strong>Type:</strong> {(action as ActionData).type}
            </div>
            {(action as ActionData).sql_query && (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Query:</strong>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: '0.25rem' }}>
                  {(action as ActionData).sql_query}
                </pre>
              </div>
            )}
            {(action as ActionData).parameters && (
              <div style={{ marginTop: '0.5rem' }}>
                <strong>Parameters:</strong>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', marginTop: '0.25rem' }}>
                  {(action as ActionData).parameters}
                </pre>
              </div>
            )}

            <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
              <button className="btn-confirm" onClick={handleConfirm} style={{ flex: 1 }}>
                <FiCheck style={{ marginRight: '0.5rem' }} />
                Confirm Action
              </button>
            </div>
          </div>
        )}


      </div>
    </div>
  )
}
