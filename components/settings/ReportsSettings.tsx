import React, { useState, useEffect } from 'react'
import { Report } from '../../types'
import { apiClient } from '../../services/geminiService'

export default function ReportsSettings() {
  const [reports, setReports] = useState<Report[]>([])
  const [selectedReport, setSelectedReport] = useState<Report | null>(null)

  useEffect(() => {
    loadReports()
  }, [])

  const loadReports = async () => {
    try {
      const response = await apiClient.getReports()
      setReports(response.data.data || [])
    } catch (error) {
      console.error('Error loading reports:', error)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this report?')) return
    try {
      await apiClient.deleteReport(id)
      await loadReports()
      setSelectedReport(null)
    } catch (error) {
      console.error('Error deleting report:', error)
    }
  }

  const handleDownload = (report: Report) => {
    const json = JSON.stringify(report, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${report.id}.json`
    a.click()
  }

  return (
    <div>
      <h3>Reports</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        View, manage, and export reports generated from conversations and actions.
      </p>

      {selectedReport ? (
        <div style={{ background: 'white', padding: '1.5rem', borderRadius: '0.5rem', marginBottom: '1.5rem' }}>
          <div style={{ marginBottom: '1rem' }}>
            <button
              onClick={() => setSelectedReport(null)}
              style={{
                background: 'none',
                border: 'none',
                color: '#667eea',
                cursor: 'pointer',
                fontSize: '0.9rem',
                padding: 0,
              }}
            >
              ← Back to Reports
            </button>
          </div>
          <h4>{selectedReport.title}</h4>
          {selectedReport.description && (
            <p style={{ marginBottom: '1rem', color: '#718096' }}>{selectedReport.description}</p>
          )}
          <div style={{ marginBottom: '1rem' }}>
            <strong>Type:</strong> {selectedReport.report_type}
          </div>
          <div style={{ marginBottom: '1rem' }}>
            <strong>Created:</strong> {new Date(selectedReport.created_at).toLocaleString()}
          </div>
          <div style={{ marginBottom: '1rem', padding: '1rem', background: '#f7fafc', borderRadius: '0.5rem' }}>
            <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
              {JSON.stringify(selectedReport.data, null, 2)}
            </pre>
          </div>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <button className="btn-save" onClick={() => handleDownload(selectedReport)}>
              Download Report
            </button>
            <button className="btn-danger" onClick={() => handleDelete(selectedReport.id)}>
              Delete Report
            </button>
          </div>
        </div>
      ) : (
        <>
          {reports.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📊</div>
              <div className="empty-state-text">No reports yet</div>
              <p>Reports are generated from conversations and actions.</p>
            </div>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Title</th>
                  <th>Type</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {reports.map(report => (
                  <tr key={report.id}>
                    <td>
                      <strong>{report.title}</strong>
                      {report.description && (
                        <div style={{ fontSize: '0.875rem', color: '#718096' }}>
                          {report.description}
                        </div>
                      )}
                    </td>
                    <td>{report.report_type}</td>
                    <td>{new Date(report.created_at).toLocaleDateString()}</td>
                    <td>
                      <div className="table-actions">
                        <button className="btn-edit" onClick={() => setSelectedReport(report)}>
                          View
                        </button>
                        <button className="btn-delete" onClick={() => handleDelete(report.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </div>
  )
}
