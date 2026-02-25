import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from '../swal'
import { FiTrash2, FiPlus } from 'react-icons/fi'

interface DataSource {
  id: string
  name: string
  type: string
  db_type?: string
  host?: string
  database?: string
  is_active: boolean
}

export default function DataSourcesSettings() {
  const [sources, setSources] = useState<DataSource[]>([])
  const [formData, setFormData] = useState({
    name: '',
    type: 'database',
    description: '',
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadDataSources()
  }, [])

  const loadDataSources = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getDataSources()
      setSources(response.data.data || [])
    } catch (error) {
      console.error('Error loading data sources:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleAddSource = async () => {
    if (!formData.name) {
      showAlert('Validation', 'Please enter a source name', 'warning')
      return
    }

    try {
      setLoading(true)
      showLoading('Adding data source...')
      await apiClient.createDataSource(formData)
      setFormData({ name: '', type: 'database', description: '' })
      await loadDataSources()
    } catch (error) {
      console.error('Error adding data source:', error)
      showAlert('Error', 'Failed to add data source', 'error')
    } finally {
      setLoading(false)
      closeSwal()
    }
  }

  const handleDeleteSource = async (id: string) => {
    const confirmed = await showConfirm('Delete Data Source', 'Are you sure you want to delete this data source?')
    if (!confirmed) return

    try {
      setLoading(true)
      showLoading('Deleting data source...')
      // Attempt to call backend delete if available, otherwise remove locally
      if ((apiClient as any).deleteDataSource) {
        await (apiClient as any).deleteDataSource(id)
        await loadDataSources()
      } else {
        setSources(prev => prev.filter(s => s.id !== id))
      }
      showAlert('Deleted', 'Data source removed', 'success')
    } catch (err) {
      console.error('Error deleting data source:', err)
      showAlert('Error', 'Failed to delete data source', 'error')
    } finally {
      setLoading(false)
      closeSwal()
    }
  }

  return (
    <div className="settings-section">
      <h3>Data Sources Management</h3>
      <p className="section-description">Manage data sources that the LLM can use via RAG to answer questions.</p>

      <div className="form-section">
        <h4>Add New Data Source</h4>
        <div className="form-group">
          <label>Source Name *</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            placeholder="e.g., Production DB, Weather API"
          />
        </div>

        <div className="form-group">
          <label>Type</label>
          <select name="type" value={formData.type} onChange={handleInputChange}>
            <option value="database">Database</option>
            <option value="api">API</option>
            <option value="file">File</option>
            <option value="web">Web</option>
          </select>
        </div>

        <div className="form-group">
          <label>Description</label>
          <input
            type="text"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Brief description of this data source"
          />
        </div>

        <button className="btn-primary" onClick={handleAddSource} disabled={loading}>
          <FiPlus style={{ marginRight: '0.5rem' }} />
          Add Data Source
        </button>
      </div>

      <div className="sources-list">
        <h4>Connected Data Sources</h4>
        {loading ? (
          <div className="loading">Loading...</div>
        ) : sources.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Details</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {sources.map(source => (
                  <tr key={source.id}>
                    <td><strong>{source.name}</strong></td>
                    <td>{source.type}</td>
                    <td>
                      {source.is_active ? (
                        <span className="badge-active">Active</span>
                      ) : (
                        <span className="badge-inactive">Inactive</span>
                      )}
                    </td>
                    <td>
                      {source.type === 'database' && source.db_type && (
                        <small>{source.db_type} @ {source.host}/{source.database}</small>
                      )}
                    </td>
                    <td>
                      <button className="btn-danger btn-sm" onClick={() => handleDeleteSource(source.id)}>
                        <FiTrash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No data sources configured yet</div>
        )}
      </div>
    </div>
  )
}
