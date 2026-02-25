import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/geminiService'
import { showAlert, showLoading, closeSwal } from '../swal'
import { FiTrash2, FiPlus, FiEdit2, FiUpload } from 'react-icons/fi'

interface DataSource {
  id: string
  name: string
  type: string
  endpoint?: string
  method?: string
  auth_type?: string
  description?: string
  file_path?: string
  file_format?: string
  is_active: boolean
}

type SourceType = 'database' | 'api' | 'file' | 'web'

export default function DataSourcesAndAPIsSettings() {
  const [sources, setSources] = useState<DataSource[]>([])
  const [sourceType, setSourceType] = useState<SourceType>('database')
  const [formData, setFormData] = useState({
    name: '',
    type: 'database',
    // For API
    endpoint: '',
    method: 'GET',
    auth_type: 'none',
    // For all
    description: '',
    // For file
    file_path: '',
    file_format: '',
  })
  const [loading, setLoading] = useState(false)
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)

  useEffect(() => {
    loadDataSources()
  }, [])

  const loadDataSources = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getDataSources()
      const apiResponse = await apiClient.getAPIConfigsList()
      
      // Combine both sources and APIs into one list
      const combined = [
        ...(response.data.data || []),
        ...(apiResponse.data.data || []).map((api: any) => ({ ...api, type: 'api' }))
      ]
      setSources(combined)
    } catch (error) {
      console.error('Error loading sources:', error)
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
      setFormData(prev => ({
        ...prev,
        file_path: file.name,
        file_format: file.name.split('.').pop() || '',
      }))
    }
  }

  const handleAddSource = async () => {
    if (!formData.name) {
      showAlert('Validation', 'Please enter a source name', 'warning')
      return
    }

    if (sourceType === 'api' && !formData.endpoint) {
      alert('Please enter an endpoint URL for the API')
      return
    }

    if (sourceType === 'file' && !uploadedFile) {
      showAlert('Validation', 'Please select a file to upload', 'warning')
      return
    }

    try {
      setLoading(true)
      showLoading('Adding data source...')
      
      if (sourceType === 'api') {
        await apiClient.createAPIConfigItem(formData)
      } else if (sourceType === 'file') {
        // Handle file upload - would need multipart form data
        const formDataObj = new FormData()
        formDataObj.append('name', formData.name)
        formDataObj.append('type', 'file')
        formDataObj.append('file_format', formData.file_format)
        formDataObj.append('description', formData.description)
        if (uploadedFile) {
          formDataObj.append('file', uploadedFile)
        }
        
        // You'd need to add this endpoint to the backend
        // For now, just create data source entry
        await apiClient.createDataSource({
          name: formData.name,
          type: 'file',
          description: formData.description,
        })
      } else {
        await apiClient.createDataSource(formData)
      }

      resetForm()
      await loadDataSources()
    } catch (error) {
      console.error('Error adding source:', error)
      showAlert('Error', 'Failed to add data source', 'error')
    } finally {
      setLoading(false)
      closeSwal()
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      type: sourceType,
      endpoint: '',
      method: 'GET',
      auth_type: 'none',
      description: '',
      file_path: '',
      file_format: '',
    })
    setUploadedFile(null)
  }

  const handleSourceTypeChange = (type: SourceType) => {
    setSourceType(type)
    resetForm()
  }

  return (
    <div className="settings-section">
      <h3>Data Sources & APIs</h3>
      <p className="section-description">Manage all data sources and APIs that the LLM can use to answer questions.</p>

      <div className="form-section">
        <h4>Add New Source</h4>
        
        {/* Source Type Selector */}
        <div className="source-type-selector" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {(['database', 'api', 'file', 'web'] as SourceType[]).map(type => (
              <button
                key={type}
                className={`type-btn ${sourceType === type ? 'active' : ''}`}
                onClick={() => handleSourceTypeChange(type)}
                style={{
                  padding: '0.5rem 1rem',
                  border: sourceType === type ? '2px solid #667eea' : '1px solid #cbd5e0',
                  background: sourceType === type ? '#e6efff' : 'white',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  textTransform: 'capitalize',
                  transition: 'all 0.2s ease',
                }}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {/* Common Fields */}
        <div className="form-group">
          <label>Source Name *</label>
          <input
            type="text"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            placeholder="e.g., Production DB, Weather API, Sales Data"
          />
        </div>

        {/* API-Specific Fields */}
        {sourceType === 'api' && (
          <>
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

            <div className="form-row">
              <div className="form-group">
                <label>HTTP Method</label>
                <select name="method" value={formData.method} onChange={handleInputChange}>
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                  <option value="PUT">PUT</option>
                  <option value="DELETE">DELETE</option>
                </select>
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
            </div>
          </>
        )}

        {/* File-Specific Fields */}
        {sourceType === 'file' && (
          <div className="form-group">
            <label>Upload File *</label>
            <div
              style={{
                border: '2px dashed #cbd5e0',
                borderRadius: '0.375rem',
                padding: '1.5rem',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
              }}
              onDragOver={(e) => {
                e.preventDefault()
                e.currentTarget.style.borderColor = '#667eea'
                e.currentTarget.style.backgroundColor = '#f0f4ff'
              }}
              onDragLeave={(e) => {
                e.currentTarget.style.borderColor = '#cbd5e0'
                e.currentTarget.style.backgroundColor = 'transparent'
              }}
              onDrop={(e) => {
                e.preventDefault()
                e.currentTarget.style.borderColor = '#cbd5e0'
                e.currentTarget.style.backgroundColor = 'transparent'
                const file = e.dataTransfer.files[0]
                if (file) {
                  setUploadedFile(file)
                  setFormData(prev => ({
                    ...prev,
                    file_path: file.name,
                    file_format: file.name.split('.').pop() || '',
                  }))
                }
              }}
            >
              <input
                type="file"
                onChange={handleFileChange}
                style={{ display: 'none' }}
                id="file-input"
              />
              <label htmlFor="file-input" style={{ cursor: 'pointer', display: 'block' }}>
                <FiUpload size={24} style={{ margin: '0 auto 0.5rem', opacity: 0.6 }} />
                <div>
                  {uploadedFile ? (
                    <>
                      <strong>{uploadedFile.name}</strong>
                      <div style={{ fontSize: '0.875rem', color: '#718096' }}>
                        {(uploadedFile.size / 1024).toFixed(2)} KB
                      </div>
                    </>
                  ) : (
                    <>
                      <strong>Click to upload or drag and drop</strong>
                      <div style={{ fontSize: '0.875rem', color: '#718096' }}>
                        CSV, JSON, XML, PDF, TXT or any format
                      </div>
                    </>
                  )}
                </div>
              </label>
            </div>
          </div>
        )}

        {/* Description for all types */}
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

        <button className="btn-primary" onClick={handleAddSource} disabled={loading}>
          <FiPlus style={{ marginRight: '0.5rem' }} />
          Add {sourceType.charAt(0).toUpperCase() + sourceType.slice(1)}
        </button>
      </div>

      {/* Connected Sources List */}
      <div className="sources-list" style={{ marginTop: '2rem' }}>
        <h4>Connected Sources</h4>
        {loading ? (
          <div className="loading">Loading...</div>
        ) : sources.length > 0 ? (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Details</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {sources.map(source => (
                  <tr key={source.id}>
                    <td><strong>{source.name}</strong></td>
                    <td>
                      <span style={{
                        display: 'inline-block',
                        padding: '0.25rem 0.75rem',
                        background: '#e6efff',
                        color: '#667eea',
                        borderRadius: '0.25rem',
                        fontSize: '0.875rem',
                        fontWeight: 500,
                        textTransform: 'capitalize',
                      }}>
                        {source.type}
                      </span>
                    </td>
                    <td>
                      <small style={{ color: '#718096' }}>
                        {source.type === 'api' && source.endpoint && (
                          <>{source.method} {source.endpoint}</>
                        )}
                        {source.type === 'file' && source.file_format && (
                          <>Format: {source.file_format.toUpperCase()}</>
                        )}
                        {source.type === 'database' && (
                          <>DB Connection</>
                        )}
                        {source.type === 'web' && (
                          <>Web Source</>
                        )}
                      </small>
                    </td>
                    <td>
                      {source.is_active ? (
                        <span style={{
                          display: 'inline-block',
                          padding: '0.25rem 0.75rem',
                          background: '#c6f6d5',
                          color: '#22543d',
                          borderRadius: '0.25rem',
                          fontSize: '0.875rem',
                          fontWeight: 500,
                        }}>
                          Active
                        </span>
                      ) : (
                        <span style={{
                          display: 'inline-block',
                          padding: '0.25rem 0.75rem',
                          background: '#fed7d7',
                          color: '#742a2a',
                          borderRadius: '0.25rem',
                          fontSize: '0.875rem',
                          fontWeight: 500,
                        }}>
                          Inactive
                        </span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button
                          style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: '#667eea',
                            padding: '0.25rem 0.5rem',
                          }}
                          title="Edit"
                        >
                          <FiEdit2 size={16} />
                        </button>
                        <button
                          style={{
                            background: 'none',
                            border: 'none',
                            cursor: 'pointer',
                            color: '#f56565',
                            padding: '0.25rem 0.5rem',
                          }}
                          title="Delete"
                        >
                          <FiTrash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{
            textAlign: 'center',
            padding: '2rem',
            color: '#718096',
            background: '#f7fafc',
            borderRadius: '0.5rem',
          }}>
            No data sources or APIs configured yet
          </div>
        )}
      </div>
    </div>
  )
}
