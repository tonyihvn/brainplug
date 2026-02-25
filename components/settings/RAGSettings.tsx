import React, { useState, useEffect } from 'react'
import { BusinessRule } from '../../types'
import { apiClient } from '../../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from '../swal'

interface SchemaTable {
  table_name: string
  columns: {
    name: string
    type: string
    nullable: boolean
    sample_values?: string[]
  }[]
  primary_keys?: string[]
  foreign_keys?: any[]
}

interface RAGItem {
  id: string
  category: string
  title: string
  content: string
  source: string
  created_at?: string
}

export default function RAGSettings() {
  const [rules, setRules] = useState<BusinessRule[]>([])
  const [ragItems, setRagItems] = useState<RAGItem[]>([])
  const [schemas, setSchemas] = useState<SchemaTable[]>([])
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'optional',
    content: '',
    category: '',
    is_active: true,
  })
  const [editingId, setEditingId] = useState<string | null>(null)

  useEffect(() => {
    loadRules()
    loadRAGItems()
    loadSchemas()
  }, [])

  const loadRules = async () => {
    try {
      const response = await apiClient.getBusinessRules()
      setRules(response.data.data || [])
    } catch (error) {
      console.error('Error loading business rules:', error)
    }
  }

  const loadRAGItems = async () => {
    try {
      const response = await apiClient.getRAGItems()
      setRagItems(response.data.data || [])
    } catch (error) {
      console.error('Error loading RAG items:', error)
    }
  }

  const loadSchemas = async () => {
    try {
      const response = await apiClient.getRAGSchema()
      const schemaData = response.data.data
      if (schemaData && schemaData.tables) {
        setSchemas(schemaData.tables)
      }
    } catch (error) {
      console.error('Error loading RAG schemas:', error)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target as HTMLInputElement
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value,
    }))
  }

  const handleSave = async () => {
    try {
      if (editingId) {
        await apiClient.updateBusinessRule(editingId, formData)
      } else {
        await apiClient.createBusinessRule(formData)
      }
      await loadRules()
      resetForm()
    } catch (error) {
      console.error('Error saving business rule:', error)
      showAlert('Error', 'Error saving rule', 'error')
    } finally {
      closeSwal()
    }
  }

  const handleEdit = (rule: BusinessRule) => {
    setEditingId(rule.id)
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      content: rule.content,
      category: rule.category || '',
      is_active: rule.is_active,
    })
  }

  const handleDelete = async (id: string) => {
    const ok = await showConfirm('Delete this rule?', 'Are you sure you want to delete this rule?')
    if (!ok) return
    try {
      showLoading('Deleting rule...')
      await apiClient.deleteBusinessRule(id)
      await loadRules()
    } catch (error) {
      console.error('Error deleting rule:', error)
      showAlert('Error', 'Error deleting rule', 'error')
    } finally {
      closeSwal()
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setFormData({
      name: '',
      description: '',
      rule_type: 'optional',
      content: '',
      category: '',
      is_active: true,
    })
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'schema':
        return '#dbeafe'
      case 'relationship':
        return '#dcfce7'
      case 'business_rule':
        return '#fef3c7'
      case 'sample_data':
        return '#f3e8ff'
      default:
        return '#e5e7eb'
    }
  }

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'schema':
        return '📋 Schema'
      case 'relationship':
        return '🔗 Relationship'
      case 'business_rule':
        return '📏 Business Rule'
      case 'sample_data':
        return '📊 Sample Data'
      default:
        return '📝 Custom'
    }
  }

  return (
    <div>
      <h3>RAG & Business Rules Management</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        Define business rules that are automatically included in LLM context. Database schemas are auto-populated when you connect a new database.
      </p>

      {/* Auto-Generated RAG Items Summary */}
      <div style={{ marginBottom: '2rem', padding: '1rem', backgroundColor: '#f0fdf4', borderRadius: '0.5rem', borderLeft: '4px solid #22c55e' }}>
        <h4 style={{ margin: '0 0 0.5rem 0' }}>Auto-Generated RAG Items</h4>
        <p style={{ color: '#718096', margin: '0 0 1rem 0' }}>
          {ragItems.length > 0 
            ? `${ragItems.length} auto-generated items from database schema. Each table gets Schema, Relationship, and Sample Data entries.`
            : 'No auto-generated RAG items yet. Connect a database in the Database Settings to auto-populate.'}
        </p>
        
        {ragItems.length > 0 && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '1rem', marginTop: '1rem' }}>
              {['schema', 'relationship', 'sample_data'].map(category => {
                const items = ragItems.filter(item => item.category === category)
                return (
                  <div key={category} style={{ padding: '1rem', backgroundColor: 'white', borderRadius: '0.375rem', border: '2px solid', borderColor: getCategoryColor(category) }}>
                    <h5 style={{ margin: '0 0 0.5rem 0', color: '#1f2937' }}>{getCategoryLabel(category)}</h5>
                    <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      <strong>{items.length} items</strong>
                      <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem', maxHeight: '150px', overflowY: 'auto' }}>
                        {items.map(item => (
                          <li key={item.id} style={{ wordBreak: 'break-word' }}>
                            {item.title}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}
      </div>

      <form>
        <div className="form-group-row">
          <div className="form-group">
            <label>Rule Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="e.g., Customer Privacy Rule"
            />
          </div>
          <div className="form-group">
            <label>Rule Type</label>
            <select name="rule_type" value={formData.rule_type} onChange={handleInputChange}>
              <option value="compulsory">Compulsory (Always Include)</option>
              <option value="optional">Optional</option>
              <option value="constraint">Constraint</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Description</label>
          <input
            type="text"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Brief description of the rule"
          />
        </div>

        <div className="form-group">
          <label>Category</label>
          <input
            type="text"
            name="category"
            value={formData.category}
            onChange={handleInputChange}
            placeholder="e.g., privacy, security, compliance"
          />
        </div>

        <div className="form-group">
          <label>Rule Content</label>
          <textarea
            name="content"
            value={formData.content}
            onChange={handleInputChange}
            placeholder="Define the business rule text..."
            rows={5}
            style={{ fontFamily: 'monospace' }}
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
            {' '}Activate this Rule
          </label>
        </div>

        <div className="form-actions">
          <button type="button" className="btn-save" onClick={handleSave}>
            {editingId ? 'Update Rule' : 'Add Rule'}
          </button>
          <button type="button" className="btn-cancel" onClick={resetForm}>
            Clear
          </button>
        </div>
      </form>

      <div style={{ marginTop: '2rem' }}>
        <h4>Business Rules</h4>
        {rules.length === 0 ? (
          <p style={{ color: '#718096' }}>No rules defined yet</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Category</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rules.map(rule => (
                <tr key={rule.id}>
                  <td>
                    <strong>{rule.name}</strong>
                    <div style={{ fontSize: '0.875rem', color: '#718096' }}>{rule.description}</div>
                  </td>
                  <td>{rule.rule_type}</td>
                  <td>{rule.category || '-'}</td>
                  <td>
                    <span className={`status-badge ${rule.is_active ? 'status-active' : 'status-inactive'}`}>
                      {rule.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <div className="table-actions">
                      <button className="btn-edit" onClick={() => handleEdit(rule)}>
                        Edit
                      </button>
                      <button className="btn-delete" onClick={() => handleDelete(rule.id)}>
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

      <div style={{ marginTop: '2rem' }}>
        <h4>Schemas</h4>
        {schemas.length === 0 ? (
          <p style={{ color: '#718096' }}>No schemas available</p>
        ) : (
          <table className="table">
            <thead>
              <tr>
                <th>Table</th>
                <th>Columns</th>
                <th>Primary Keys</th>
                <th>Foreign Keys</th>
              </tr>
            </thead>
            <tbody>
              {schemas.map(s => (
                <tr key={s.table_name}>
                  <td>
                    <strong>{s.table_name}</strong>
                  </td>
                  <td>
                    <div style={{ fontSize: '0.9rem', color: '#374151' }}>
                      {s.columns && s.columns.length > 0 ? (
                        <ul style={{ margin: 0, paddingLeft: '1rem', maxHeight: 120, overflowY: 'auto' }}>
                          {s.columns.map((c: any) => (
                            <li key={c.name} style={{ wordBreak: 'break-word' }}>
                              <strong>{c.name}</strong> <span style={{ color: '#6b7280' }}>({c.type})</span>
                            </li>
                          ))}
                        </ul>
                      ) : (
                        <span style={{ color: '#718096' }}>No columns</span>
                      )}
                    </div>
                  </td>
                  <td>{(s.primary_keys && s.primary_keys.length) ? s.primary_keys.join(', ') : '-'}</td>
                  <td>{(s.foreign_keys && s.foreign_keys.length) ? s.foreign_keys.map((fk:any) => `${fk.source_column}→${fk.target_table}.${fk.target_column}`).join('; ') : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
