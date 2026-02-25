import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/geminiService'
import { FiTrash2, FiPlus, FiEdit2 } from 'react-icons/fi'

interface APIConfig {
  id: string
  name: string
  endpoint: string
  method: string
  auth_type?: string
  description?: string
  is_active: boolean
}

export default function APISettings() {
  const [configs, setConfigs] = useState<APIConfig[]>([])
  const [formData, setFormData] = useState({
    name: '',
    endpoint: '',
    method: 'GET',
    auth_type: 'none',
    description: '',
  })
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadAPIConfigs()
  }, [])

  const loadAPIConfigs = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getAPIConfigsList()
      setConfigs(response.data.data || [])
    } catch (error) {
      console.error('Error loading API configs:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleAddAPI = async () => {
    if (!formData.name || !formData.endpoint) {
      alert('Please fill in name and endpoint')
      return
    }

    try {
      setLoading(true)
      await apiClient.createAPIConfigItem(formData)
      setFormData({
        name: '',
        endpoint: '',
        method: 'GET',
        auth_type: 'none',
        description: '',
      })
      await loadAPIConfigs()
    } catch (error) {
      console.error('Error adding API config:', error)
      alert('Failed to add API configuration')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="settings-section">
      <h3>API Integrations</h3>
      <p className="section-description">Configure external APIs that the LLM can use to fetch data and answer questions.</p>

      <div className="form-section">
        <h4>Add New API</h4>
        <div className="form-group">
          <label>API Name *</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            placeholder="e.g., Weather API, Stock Data API"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Endpoint URL *</label>
            <input
              type="text"
              name="endpoint"
              value={formData.endpoint}
              onChange={handleInputChange}
              placeholder="https://api.example.com/v1/endpoint"
            />
          </div>

          <div className="form-group">
            <label>HTTP Method</label>
            <select name="method" value={formData.method} onChange={handleInputChange}>
              <option value="GET">GET</option>
              <option value="POST">POST</option>
              <option value="PUT">PUT</option>
              <option value="DELETE">DELETE</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Authentication Type</label>
          <select name="auth_type" value={formData.auth_type} onChange={handleInputChange}>
            <option value="none">None</option>
            <option value="bearer">Bearer Token</option>
            <option value="api_key">API Key</option>
            <option value="basic">Basic Auth</option>
            <option value="oauth">OAuth 2.0</option>
          </select>
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Brief description and usage instructions"
            rows={3}
          />
        </div>

        <button className="btn-primary" onClick={handleAddAPI} disabled={loading}>
          <FiPlus style={{ marginRight: '0.5rem' }} />
          Add API
        </button>
      </div>

      <div className="configs-list">
        <h4>Connected APIs</h4>
        {loading ? (
          <div className="loading">Loading...</div>
        ) : configs.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Endpoint</th>
                  <th>Method</th>
                  <th>Auth</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {configs.map(config => (
                  <tr key={config.id}>
                    <td><strong>{config.name}</strong></td>
                    <td>
                      <small style={{ wordBreak: 'break-all' }}>{config.endpoint}</small>
                    </td>
                    <td>
                      <span className="badge" style={{ background: '#e3f2fd' }}>
                        {config.method}
                      </span>
                    </td>
                    <td>{config.auth_type || 'None'}</td>
                    <td>
                      {config.is_active ? (
                        <span className="badge-active">Active</span>
                      ) : (
                        <span className="badge-inactive">Inactive</span>
                      )}
                    </td>
                    <td>
                      <button className="btn-secondary btn-sm">
                        <FiEdit2 size={16} />
                      </button>
                      <button className="btn-danger btn-sm">
                        <FiTrash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state">No API integrations configured yet</div>
        )}
      </div>
    </div>
  )
}
