import React, { useState, useEffect } from 'react'
import { DatabaseSetting } from '../../types'
import { apiClient } from '../../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from '../swal'

export default function DatabaseSettings() {
  const [settings, setSettings] = useState<DatabaseSetting[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    db_type: 'postgresql',
    host: '',
    port: '',
    database: '',
    username: '',
    password: '',
    is_active: false,
  })
  const [envSaved, setEnvSaved] = useState<string[]>([])

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
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleSave = async () => {
    try {
      showLoading('Saving database connection...')
      // Include id if editing existing setting
      const dataToSave = editingId ? { ...formData, id: editingId } : formData
      
      const resp = await apiClient.updateDatabaseSettings(dataToSave)
      const saved = resp.data?.data?.env_saved || []
      setEnvSaved(saved)
      
      // If setting database as active, trigger RAG population
      if (formData.is_active && resp.data?.data?.id) {
        console.log('🔄 Populating RAG from database:', formData.name)
        try {
          await apiClient.populateRAG(resp.data.data.id)
          console.log('✓ RAG populated successfully')
        } catch (error) {
          console.error('Warning: RAG population failed:', error)
          // Don't block the UI if RAG population fails
        }
      }
      
      await loadSettings()
      resetForm()
    } catch (error) {
      console.error('Error saving database settings:', error)
      showAlert('Error', 'Error saving settings', 'error')
    } finally {
      closeSwal()
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
    })
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
    setFormData({
      name: '',
      db_type: 'postgresql',
      host: '',
      port: '',
      database: '',
      username: '',
      password: '',
      is_active: false,
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
