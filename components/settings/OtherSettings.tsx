import React, { useState, useEffect } from 'react'
import { ApiConfig } from '../../types'
import { apiClient } from '../../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from '../swal'

export default function OtherSettings() {
  const [configs, setConfigs] = useState<ApiConfig[]>([])
  const [formData, setFormData] = useState({
    name: '',
    api_type: 'rest',
    endpoint: '',
    method: 'GET',
    auth_type: 'none',
    auth_value: '',
  })
  const [editingId, setEditingId] = useState<string | null>(null)
  const [envSaved, setEnvSaved] = useState<string[]>([])

  useEffect(() => {
    loadConfigs()
  }, [])

  const loadConfigs = async () => {
    try {
      const response = await apiClient.getAPIConfigs()
      setConfigs(response.data.data || [])
    } catch (error) {
      console.error('Error loading API configs:', error)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }))
  }

  const handleSave = async () => {
    try {
      let resp
      if (editingId) {
        resp = await apiClient.updateAPIConfig(editingId, formData)
      } else {
        resp = await apiClient.createAPIConfig(formData)
      }
      const saved = resp.data?.data?.env_saved || []
      setEnvSaved(saved)
      await loadConfigs()
      resetForm()
    } catch (error) {
      console.error('Error saving API config:', error)
      showAlert('Error', 'Error saving config', 'error')
    }
  }

  const handleEdit = (config: ApiConfig) => {
    setEditingId(config.id)
    setFormData({
      name: config.name,
      api_type: config.api_type,
      endpoint: config.endpoint,
      method: config.method,
      auth_type: config.auth_type || 'none',
      auth_value: '',
    })
  }

  const handleDelete = async (id: string) => {
    const ok = await showConfirm('Delete this API config?', 'Are you sure you want to delete this API config?')
    if (!ok) return
    try {
      showLoading('Deleting...')
      await apiClient.deleteAPIConfig(id)
      await loadConfigs()
    } catch (error) {
      console.error('Error deleting config:', error)
      showAlert('Error', 'Error deleting config', 'error')
    } finally {
      closeSwal()
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setFormData({
      name: '',
      api_type: 'rest',
      endpoint: '',
      method: 'GET',
      auth_type: 'none',
      auth_value: '',
    })
  }

  return (
    <div>
      <h3>Other Settings</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        Configure additional external API integrations for custom actions.
      </p>

      <form>
        <h4>Add External API Configuration</h4>
        <div className="form-group">
          <label>API Name</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            placeholder="e.g., Weather API, Slack"
          />
        </div>

        <div className="form-group-row">
          <div className="form-group">
            <label>API Type</label>
            <select name="api_type" value={formData.api_type} onChange={handleInputChange}>
              <option value="rest">REST</option>
              <option value="graphql">GraphQL</option>
              <option value="soap">SOAP</option>
            </select>
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
          <label>API Endpoint</label>
          <input
            type="text"
            name="endpoint"
            value={formData.endpoint}
            onChange={handleInputChange}
            placeholder="https://api.example.com/v1/resource"
          />
        </div>

        <div className="form-group-row">
          <div className="form-group">
            <label>Authentication Type</label>
            <select name="auth_type" value={formData.auth_type} onChange={handleInputChange}>
              <option value="none">None</option>
              <option value="bearer">Bearer Token</option>
              <option value="apikey">API Key</option>
              <option value="basic">Basic Auth</option>
            </select>
          </div>
          {formData.auth_type !== 'none' && (
            <div className="form-group">
              <label>{formData.auth_type === 'bearer' ? 'Token' : 'Auth Value'}</label>
              <input
                type="password"
                name="auth_value"
                value={formData.auth_value}
                onChange={handleInputChange}
              />
            </div>
          )}
        </div>

        <div className="form-actions">
          <button type="button" className="btn-save" onClick={handleSave}>
            {editingId ? 'Update API Config' : 'Add API Config'}
          </button>
          {envSaved.length > 0 && (
            <div style={{ marginLeft: '1rem', color: '#2f855a', alignSelf: 'center' }}>
              Saved to .env: {envSaved.join(', ')}
            </div>
          )}
          <button type="button" className="btn-cancel" onClick={resetForm}>
            Clear
          </button>
        </div>
      </form>

      <div style={{ marginTop: '2rem' }}>
        <h4>Configured APIs</h4>
        {configs.length === 0 ? (
          <p style={{ color: '#718096' }}>No APIs configured yet</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Endpoint</th>
                <th>Method</th>
                <th>Auth</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {configs.map(config => (
                <tr key={config.id}>
                  <td>{config.name}</td>
                  <td>{config.api_type}</td>
                  <td style={{ fontSize: '0.875rem', fontFamily: 'monospace' }}>
                    {config.endpoint.substring(0, 40)}...
                  </td>
                  <td>{config.method}</td>
                  <td>{config.auth_type || '-'}</td>
                  <td>
                    <div className="table-actions">
                      <button className="btn-edit" onClick={() => handleEdit(config)}>
                        Edit
                      </button>
                      <button className="btn-delete" onClick={() => handleDelete(config.id)}>
                        Delete
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
