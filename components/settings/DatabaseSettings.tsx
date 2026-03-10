import React, { useState, useEffect } from 'react'
import { DatabaseSetting, TableConfig } from '../../types'
import { apiClient } from '../../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from '../swal'
import { showRAGPopulationModal, showRAGErrorModal, RAGStatistics } from '../RAGPopulationModal'
import APIQueryConfig from '../APIQueryConfig'

export default function DatabaseSettings() {
  const [settings, setSettings] = useState<DatabaseSetting[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState<any>({
    name: '',
    db_type: 'postgresql',
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
    is_active: false,
    query_mode: 'direct', // 'direct' or 'api'
    selected_tables: {},
    sync_interval: 60,
  })
  const [envSaved, setEnvSaved] = useState<string[]>([])
  const [showAPIConfig, setShowAPIConfig] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const response = await apiClient.getDatabaseSettings()
      setSettings(response.data.data || [])
    } catch (error) {
      console.error('Error loading database settings:', error)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target as HTMLInputElement
    setFormData((prev: any) => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleSave = async () => {
    try {
      showLoading('Saving database connection...')
      
      // Prepare data for saving - ensure port is a number
      const dataToSave = {
        ...formData,
        port: formData.port ? parseInt(formData.port, 10) : null,  // Convert port to number
      }
      
      // Include id if editing existing setting
      if (editingId) {
        dataToSave.id = editingId
      }
      
      console.log('[DB-FORM] Submitting database settings:', {
        name: dataToSave.name,
        query_mode: dataToSave.query_mode,
        is_active: dataToSave.is_active,
        db_type: dataToSave.db_type,
      })
      
      const resp = await apiClient.updateDatabaseSettings(dataToSave)
      const saved = resp.data?.data?.env_saved || []
      setEnvSaved(saved)
      
      console.log('[DB-FORM] Response received:', {
        query_mode: resp.data?.data?.query_mode,
        is_active: resp.data?.data?.is_active,
        rag_statistics: resp.data?.data?.rag_statistics?.status,
      })
      
      // If setting database as active, show RAG population result
      if (formData.is_active && resp.data?.data?.id) {
        const ragStats = resp.data?.data?.rag_statistics
        if (ragStats && ragStats.status === 'success') {
          closeSwal()
          const result = await showRAGPopulationModal(ragStats)
          if (result.isConfirmed) {
            console.log('User wants to view RAG items')
          }
        } else if (ragStats && ragStats.status === 'failed') {
          closeSwal()
          await showRAGErrorModal(ragStats.error || 'Unknown error occurred during RAG generation')
        } else {
          closeSwal()
          await showRAGErrorModal('Failed to generate RAG schema. Check console for details.')
        }
      } else {
        closeSwal()
      }
      
      await loadSettings()
      resetForm()
    } catch (error) {
      console.error('Error saving database settings:', error)
      closeSwal()
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      await showRAGErrorModal(errorMsg)
    }
    
  }

  const handleEdit = (setting: DatabaseSetting) => {
    setEditingId(setting.id)
    setFormData({
      name: setting.name,
      db_type: setting.db_type,
      host: setting.host || '',
      port: setting.port?.toString() || '',
      database: setting.database,
      username: setting.username || '',
      password: '',
      is_active: setting.is_active,
      query_mode: setting.query_mode || 'direct',
      selected_tables: setting.selected_tables || {},
      sync_interval: setting.sync_interval || 60,
    })
    if (setting.query_mode === 'api') {
      setShowAPIConfig(true)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const ok = await showConfirm('Delete this database connection?', 'This will remove any RAG schema/rules generated from it.')
      if (!ok) return
      showLoading('Deleting...')
      await apiClient.deleteDatabaseSetting(id)
      await loadSettings()
    } catch (error) {
      console.error('Error deleting database setting:', error)
      showAlert('Error', 'Error deleting database setting', 'error')
    } finally {
      closeSwal()
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setShowAPIConfig(false)
    setFormData({
      name: '',
      db_type: 'postgresql',
      host: '',
      port: '',
      database: '',
      username: '',
      password: '',
      is_active: false,
      query_mode: 'direct',
      selected_tables: {},
      sync_interval: 60,
    })
  }

  return (
    <div>
      <h3>Database Connection Settings</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        Configure database connections for data querying and schema extraction.
      </p>

      <form>
        <div className="form-group-row">
          <div className="form-group">
            <label>Database Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="e.g., Main Database"
            />
          </div>
          <div className="form-group">
            <label>Database Type</label>
            <select name="db_type" value={formData.db_type} onChange={handleInputChange}>
              <option value="postgresql">PostgreSQL</option>
              <option value="mysql">MySQL</option>
              <option value="sqlite">SQLite</option>
              <option value="mssql">MSSQL</option>
            </select>
          </div>
        </div>

        {formData.db_type !== 'sqlite' && (
          <>
            <div className="form-group-row">
              <div className="form-group">
                <label>Host</label>
                <input
                  type="text"
                  name="host"
                  value={formData.host}
                  onChange={handleInputChange}
                  placeholder="localhost"
                />
              </div>
              <div className="form-group">
                <label>Port</label>
                <input
                  type="number"
                  name="port"
                  value={formData.port}
                  onChange={handleInputChange}
                  placeholder="5432"
                />
              </div>
            </div>

            <div className="form-group-row">
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  name="username"
                  value={formData.username}
                  onChange={handleInputChange}
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                />
              </div>
            </div>
          </>
        )}

        <div className="form-group">
          <label>Database / File Path</label>
          <input
            type="text"
            name="database"
            value={formData.database}
            onChange={handleInputChange}
            placeholder={formData.db_type === 'sqlite' ? '/path/to/database.db' : 'database_name'}
          />
        </div>

        <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: '#edf2f7', borderRadius: '8px' }}>
          <h4 style={{ marginTop: 0 }}>Query Mode</h4>
          <p style={{ color: '#718096', marginBottom: '1rem', fontSize: '0.9rem' }}>
            Choose how the LLM will access this database:
          </p>
          
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="radio"
                name="query_mode"
                value="direct"
                checked={formData.query_mode === 'direct'}
                onChange={(e) => {
                  handleInputChange(e as any)
                  setShowAPIConfig(false)
                }}
              />
              <span style={{ marginLeft: '0.5rem' }}>
                <strong>Database Direct Query</strong>
                <br />
                <small style={{ color: '#718096' }}>LLM queries the database directly (current behavior)</small>
              </span>
            </label>
          </div>
          
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
              <input
                type="radio"
                name="query_mode"
                value="api"
                checked={formData.query_mode === 'api'}
                onChange={(e) => {
                  handleInputChange(e as any)
                  setShowAPIConfig(true)
                }}
              />
              <span style={{ marginLeft: '0.5rem' }}>
                <strong>API Query (Vector DB)</strong>
                <br />
                <small style={{ color: '#718096' }}>
                  Data is pulled into a vector database for secure, semantic search access
                </small>
              </span>
            </label>
          </div>

          {formData.query_mode === 'api' && (
            <div style={{ 
              marginTop: '1rem', 
              padding: '1rem', 
              backgroundColor: '#f0fff4', 
              borderLeft: '4px solid #48bb78',
              borderRadius: '4px'
            }}>
              <p style={{ marginTop: 0, color: '#22543d' }}>
                <strong>Security Benefits:</strong> The LLM cannot access your raw database directly. 
                Instead, you select which tables to sync into a local vector database. 
                The LLM only searches that vector database for context.
              </p>
            </div>
          )}
        </div>

        <div className="form-group">
          <label>
            <input
              type="checkbox"
              name="is_active"
              checked={formData.is_active}
              onChange={handleInputChange}
            />
            {' '}Set as Active Connection
          </label>
        </div>

        <div className="form-actions">
          <button type="button" className="btn-save" onClick={handleSave}>
            Save Settings
          </button>
          {envSaved.length > 0 && (
            <div style={{ marginLeft: '1rem', color: '#2f855a', alignSelf: 'center' }}>
              Saved to .env: {envSaved.join(', ')}
            </div>
          )}
          <button type="button" className="btn-cancel" onClick={resetForm}>
            Cancel
          </button>
        </div>
      </form>

      {showAPIConfig && formData.query_mode === 'api' && editingId && (
        <APIQueryConfig
          databaseId={editingId}
          databaseName={formData.name}
          initialConfig={formData.selected_tables}
          onConfigSave={(config) => {
            setFormData((prev: any) => ({
              ...prev,
              selected_tables: config
            }))
          }}
        />
      )}

      <div style={{ marginTop: '2rem' }}>
        <h4>Connected Databases</h4>
        {settings.length === 0 ? (
          <p style={{ color: '#718096' }}>No databases configured yet</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Query Mode</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {settings.map(setting => (
                <tr key={setting.id}>
                  <td>{setting.name}</td>
                  <td>{setting.db_type}</td>
                  <td>
                    <span style={{
                      padding: '0.25rem 0.75rem',
                      borderRadius: '4px',
                      fontSize: '0.85rem',
                      backgroundColor: setting.query_mode === 'api' ? '#c3dafe' : '#e2e8f0',
                      color: setting.query_mode === 'api' ? '#1e3a8a' : '#2d3748'
                    }}>
                      {setting.query_mode === 'api' ? '🔒 Vector DB' : '⚡ Direct Query'}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${setting.is_active ? 'status-active' : 'status-inactive'}`}>
                      {setting.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <div className="table-actions">
                      <button className="btn-edit" onClick={() => handleEdit(setting)}>
                        Edit
                      </button>
                      <button className="btn-delete" onClick={() => handleDelete(setting.id)}>
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
