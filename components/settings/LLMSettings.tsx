import React, { useState, useEffect } from 'react'
import { LLMModel } from '../../types'
import { apiClient } from '../../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from '../swal'

export default function LLMSettings() {
  const [models, setModels] = useState<LLMModel[]>([])
  const [formData, setFormData] = useState({
    name: '',
    model_type: 'gemini',
    model_id: '',
    api_key: '',
    api_endpoint: '',
    priority: 0,
    is_active: true,
  })
  const [envSavedKeys, setEnvSavedKeys] = useState<string[]>([])
  const [localModels, setLocalModels] = useState<string[]>([])
  const [loadingLocal, setLoadingLocal] = useState(false)

  useEffect(() => {
    loadModels()
  }, [])

  useEffect(() => {
    // Auto-load local models when switching to local model type
    if (formData.model_type === 'local') {
      loadLocalModels()
    }
  }, [formData.model_type])

  const loadModels = async () => {
    try {
      const response = await apiClient.getLLMSettings()
      setModels(response.data.data || [])
    } catch (error) {
      console.error('Error loading LLM settings:', error)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target as HTMLInputElement
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : name === 'priority' ? parseInt(value) : value,
    }))
  }

  const handleSave = async () => {
    try {
      showLoading('Saving LLM settings...')
      const resp = await apiClient.updateLLMSettings(formData)
      const saved = resp.data?.data?.env_saved || []
      setEnvSavedKeys(saved)
      await loadModels()
      resetForm()
    } catch (error) {
      console.error('Error saving LLM settings:', error)
      showAlert('Error', 'Error saving LLM settings', 'error')
    } finally {
      closeSwal()
    }
  }

  const resetForm = () => {
    setFormData({
      name: '',
      model_type: 'gemini',
      model_id: '',
      api_key: '',
      api_endpoint: '',
      priority: 0,
      is_active: true,
    })
  }

  const handleToggleActive = async (model: LLMModel) => {
    try {
      await apiClient.updateLLMSettings({
        ...model,
        is_active: !model.is_active,
      })
      await loadModels()
    } catch (error) {
      console.error('Error updating model status:', error)
    }
  }

  const handleEdit = (model: LLMModel) => {
    setFormData({
      name: model.name,
      model_type: model.model_type,
      model_id: model.model_id,
      api_key: model.api_key || '',
      api_endpoint: model.api_endpoint || '',
      priority: model.priority || 0,
      is_active: model.is_active,
      id: model.id,
    } as any)
  }

  const loadLocalModels = async () => {
    try {
      setLoadingLocal(true)
      const resp = await apiClient.probeOllama()
      // response may be { success: true, data: { models: [...], host, endpoint } }
      const data = resp.data?.data || resp.data
      let models: string[] = []
      if (data) {
        if (Array.isArray(data)) {
          models = data.map((m: any) => String(m))
        } else if (data.models && Array.isArray(data.models)) {
          models = data.models.map((m: any) => String(m))
        } else if (Array.isArray(resp.data)) {
          models = resp.data.map((m: any) => String(m))
        }
      }
      setLocalModels(models)
    } catch (error) {
      console.error('Error loading local models:', error)
      setLocalModels([])
    } finally {
      setLoadingLocal(false)
    }
  }

  const handleDelete = async (model: LLMModel) => {
    const ok = await showConfirm(`Delete model ${model.name}?`, 'This action cannot be undone.')
    if (!ok) return
    try {
      showLoading('Deleting model...')
      await apiClient.deleteLLMModel(model.id)
      await loadModels()
    } catch (error) {
      console.error('Error deleting model:', error)
      showAlert('Error', 'Error deleting model', 'error')
    } finally {
      closeSwal()
    }
  }

  return (
    <div>
      <h3>LLM Model Configuration</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        Configure LLM models in order of priority. The first active model will be used.
      </p>

      <form>
        <div className="form-group-row">
          <div className="form-group">
            <label>Model Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleInputChange}
                list={formData.model_type === 'local' ? 'local-model-names' : undefined}
                placeholder="e.g., Gemini Pro"
              />
          </div>
          <div className="form-group">
            <label>Model Type</label>
            <select name="model_type" value={formData.model_type} onChange={handleInputChange}>
              <option value="gemini">Google Gemini</option>
              <option value="gpt">OpenAI GPT</option>
              <option value="claude">Anthropic Claude</option>
              <option value="llama">Meta Llama</option>
              <option value="local">Local Model</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Model ID</label>
          <input
            type="text"
            name="model_id"
            value={formData.model_id}
            onChange={handleInputChange}
            list={formData.model_type === 'local' ? 'local-model-ids' : undefined}
            placeholder={
              formData.model_type === 'claude'
                ? 'e.g., claude-3-5-haiku-20241022'
                : formData.model_type === 'gemini'
                ? 'e.g., gemini-pro'
                : 'e.g., gpt-4, llama2'
            }
          />
          {formData.model_type === 'claude' && (
            <div style={{ fontSize: '0.875rem', color: '#718096', marginTop: '0.5rem' }}>
              💡 For Claude Haiku 3.5, use: <code>claude-3-5-haiku-20241022</code>
            </div>
          )}
        </div>

        <div className="form-group-row">
          <div className="form-group">
            <label>API Key (if applicable)</label>
            <input
              type="password"
              name="api_key"
              value={formData.api_key}
              onChange={handleInputChange}
            />
          </div>
          <div className="form-group">
            <label>Priority (0 = highest)</label>
            <input
              type="number"
              name="priority"
              value={formData.priority}
              onChange={handleInputChange}
              min="0"
            />
          </div>
        </div>

        <div className="form-group">
          <label>API Endpoint (for custom/local models)</label>
            <input
              type="text"
              name="api_endpoint"
              value={formData.api_endpoint}
              onChange={handleInputChange}
              placeholder="http://localhost:8000/v1"
              list={formData.model_type === 'local' ? 'local-model-ids' : undefined}
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
            {' '}Activate this Model
          </label>
        </div>

        <div className="form-actions">
          <button type="button" className="btn-save" onClick={handleSave}>
            Add / Update Model
          </button>
          <button type="button" className="btn-cancel" onClick={resetForm}>
            Clear
          </button>
        </div>
      </form>

      <div style={{ marginTop: '2rem' }}>
        <h4>Configured Models (by Priority)</h4>
        {models.length === 0 ? (
          <p style={{ color: '#718096' }}>No models configured yet</p>
        ) : (
          <ul className="priority-list">
            {models.map((model, index) => (
              <li key={model.id} className="priority-item">
                <div className="priority-number">{index + 1}</div>
                <div style={{ flex: 1 }}>
                  <strong>{model.name}</strong>
                  <div style={{ fontSize: '0.875rem', color: '#718096' }}>
                    {model.model_id} ({model.model_type})
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button
                  type="button"
                    onClick={() => handleToggleActive(model)}
                    style={{
                      padding: '0.5rem 1rem',
                      background: model.is_active ? '#48bb78' : '#cbd5e0',
                      color: model.is_active ? 'white' : '#2d3748',
                      border: 'none',
                      borderRadius: '0.375rem',
                      cursor: 'pointer',
                    }}
                  >
                    {model.is_active ? '✓ Active' : 'Inactive'}
                  </button>

                  <button
                    type="button"
                    onClick={() => handleEdit(model)}
                    className="btn-secondary"
                  >
                    Edit
                  </button>

                  {envSavedKeys.includes(`LLM_${model.name.toUpperCase().replace(/ /g, '_')}_API_KEY`) && (
                    <div style={{ color: '#2f855a', alignSelf: 'center', marginLeft: '0.5rem' }}>
                      Saved to .env
                    </div>
                  )}

                  <button
                    type="button"
                    onClick={() => handleDelete(model)}
                    className="btn-danger"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {formData.model_type === 'local' && (
        <div style={{ marginTop: 20 }}>
          <h4>Installed Local Models</h4>
          <div style={{ marginBottom: 8 }}>
            <button className="btn-secondary" type="button" onClick={loadLocalModels} disabled={loadingLocal}>
              {loadingLocal ? 'Loading...' : 'Refresh Local Models'}
            </button>
          </div>
          {localModels.length === 0 ? (
            <div style={{ color: '#718096' }}>{loadingLocal ? 'Loading local models...' : 'No local models detected'}</div>
          ) : (
            <div style={{ overflowX: 'auto', border: '1px solid #e2e8f0', borderRadius: 6 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Model String</th>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Normalized ID</th>
                    <th style={{ textAlign: 'left', padding: 8, borderBottom: '1px solid #eee' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {localModels.map((m, i) => {
                    const normalized = (m && String(m).toLowerCase().startsWith('ollama:')) ? String(m).split(':', 2)[1] : String(m)
                    return (
                      <tr key={i}>
                        <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>{String(m)}</td>
                        <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>{normalized}</td>
                        <td style={{ padding: 8, borderBottom: '1px solid #f3f4f6' }}>
                          <button
                            type="button"
                            className="btn-secondary"
                            onClick={() => {
                              setFormData(prev => ({ ...prev, model_id: normalized, name: normalized }))
                            }}
                          >
                            Use
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
