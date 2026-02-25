import React, { useState, useEffect, useRef } from 'react'
import { apiClient } from '../services/geminiService'
import { showAlert, showConfirm, showLoading, closeSwal } from './swal'
import './RAGManagementView.css'

interface RAGItem {
  id: string
  category: string
  title: string
  content: string
  source: string
  created_at?: string
}

interface BusinessRule {
  id: string
  name: string
  category: string
  content: string
  rule_type: string
  type?: string
}

interface RAGManagementViewProps {
  onBack: () => void
  databaseId?: string
}

export default function RAGManagementView({ onBack, databaseId }: RAGManagementViewProps) {
  const [items, setItems] = useState<RAGItem[]>([])
  const [schemas, setSchemas] = useState<any[]>([])
  const [businessRules, setBusinessRules] = useState<BusinessRule[]>([])
  const [relationships, setRelationships] = useState<BusinessRule[]>([])
  const [sampleData, setSampleData] = useState<BusinessRule[]>([])
  const [expandedIds, setExpandedIds] = useState<string[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState<Partial<RAGItem>>({
    category: 'custom',
    title: '',
    content: '',
  })
  const [loading, setLoading] = useState(false)
  const [filter, setFilter] = useState<string>('')
  const formRef = useRef<HTMLDivElement | null>(null)
  const titleRef = useRef<HTMLInputElement | null>(null)

  useEffect(() => {
    loadItems()
    loadSchemas()
    loadBusinessRules()
  }, [filter])

  const refreshAllData = async () => {
    showLoading('Refreshing RAG data...')
    await loadItems()
    await loadSchemas()
    await loadBusinessRules()
    closeSwal()
    showAlert('✓', 'RAG data refreshed', 'success')
  }

  const loadItems = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getRAGItems(filter)
      setItems(response.data.data || [])
    } catch (error) {
      console.error('Error loading RAG items:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSchemas = async () => {
    try {
      const resp = await apiClient.getRAGSchema()
      const data = resp.data?.data || []
      console.log('📊 Loaded schemas:', { count: data.length, data })
      setSchemas(data)
    } catch (err) {
      console.error('Error loading RAG schemas:', err)
      setSchemas([])
    }
  }

  const loadBusinessRules = async () => {
    try {
      const resp = await apiClient.getBusinessRules()
      const rules = resp.data?.data || []
      console.log('📝 Loaded business rules:', { count: rules.length, rules })

      const businessRulesList = rules.filter((r: BusinessRule) => !r.type || r.type === 'rule')
      const relationshipsList = rules.filter((r: BusinessRule) => r.type === 'relationship')
      const sampleDataList = rules.filter((r: BusinessRule) => r.type === 'sample_data')

      console.log('📋 Filtered rules:', { businessRulesList: businessRulesList.length, relationshipsList: relationshipsList.length, sampleDataList: sampleDataList.length })

      setBusinessRules(businessRulesList)
      setRelationships(relationshipsList)
      setSampleData(sampleDataList)
    } catch (err) {
      console.error('Error loading business rules:', err)
      setBusinessRules([])
      setRelationships([])
      setSampleData([])
    }
  }

  const toggleExpand = (id: string) => {
    setExpandedIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    )
  }

  const handleEdit = (item: RAGItem) => {
    setEditingId(item.id)
    setFormData(item)
  }

  // When editing starts, scroll the form into view and focus the title
  useEffect(() => {
    if (editingId) {
      // small timeout to allow DOM to update
      setTimeout(() => {
        if (formRef.current) {
          formRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
        }
        if (titleRef.current) {
          try { titleRef.current.focus() } catch (e) { /* ignore */ }
        }
      }, 120)
    }
  }, [editingId])

  const truncate = (value: any, length = 50) => {
    if (value === null || value === undefined) return ''
    const s = String(value)
    return s.length > length ? s.substring(0, length) + '...' : s
  }

  const handleSave = async () => {
    try {
      showLoading(editingId ? 'Updating item...' : 'Saving item...')
      if (editingId) {
        await apiClient.updateRAGItem(editingId, formData)
      } else {
        await apiClient.createRAGItem(formData)
      }
      setEditingId(null)
      setFormData({ category: 'custom', title: '', content: '' })
      await loadItems()
    } catch (error) {
      console.error('Error saving item:', error)
      showAlert('Error', 'Error saving item', 'error')
    } finally {
      closeSwal()
    }
  }

  const handleDelete = async (id: string) => {
    const ok = await showConfirm('Delete this RAG item?', 'Are you sure you want to delete this item?')
    if (!ok) return
    try {
      showLoading('Deleting...')
      await apiClient.deleteRAGItem(id)
      await loadItems()
    } catch (error) {
      console.error('Error deleting item:', error)
      showAlert('Error', 'Error deleting item', 'error')
    } finally {
      closeSwal()
    }
  }

  const handleCancel = () => {
    setEditingId(null)
    setFormData({ category: 'custom', title: '', content: '' })
  }

  const groupedItems = items.reduce((acc, item) => {
    if (!acc[item.category]) acc[item.category] = []
    acc[item.category].push(item)
    return acc
  }, {} as Record<string, RAGItem[]>)

  const categories = Object.keys(groupedItems).sort()

  return (
    <div className="rag-management">
      <div className="rag-header">
        <h2>RAG Knowledge Base</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={onBack} className="btn-back">← Back to Chat</button>
          <button
            onClick={async () => {
              try {
                // call backend probe for local Ollama models
                const resp = await apiClient.probeOllama();
                const payload = resp.data?.data || resp.data?.diagnostics || {};
                const models = Array.isArray(payload.models) ? payload.models : (Array.isArray(resp.data?.data) ? resp.data.data : []);
                // normalize models into strings
                const modelIds = (models || []).map((m: any) => String(m));

                // create or update datalists in the document so other pages can use them
                const nameListId = 'local-model-names';
                const idListId = 'local-model-ids';

                // helper to create datalist
                const ensureDatalist = (id: string) => {
                  let dl = document.getElementById(id) as HTMLDataListElement | null
                  if (!dl) {
                    dl = document.createElement('datalist') as HTMLDataListElement
                    dl.id = id
                    document.body.appendChild(dl)
                  }
                  return dl
                }

                const namesDL = ensureDatalist(nameListId)
                const idsDL = ensureDatalist(idListId)

                // clear existing
                namesDL.innerHTML = ''
                idsDL.innerHTML = ''

                modelIds.forEach((m: string) => {
                  // normalized id without 'ollama:' prefix
                  const normalized = m && m.toLowerCase().startsWith('ollama:') ? m.split(':', 2)[1] : m
                  const nameOpt = document.createElement('option')
                  nameOpt.value = normalized
                  namesDL.appendChild(nameOpt)

                  const idOpt = document.createElement('option')
                  idOpt.value = normalized
                  idsDL.appendChild(idOpt)
                })

                // show feedback
                showAlert('OK', `Loaded ${modelIds.length} local models`, 'success')
              } catch (err) {
                console.error('Error probing local models:', err)
                showAlert('Error', 'Could not probe local models', 'error')
              }
            }}
            className="btn-secondary"
          >
            Load Local Models
          </button>
          <button
            onClick={refreshAllData}
            className="btn-secondary"
            style={{ paddingLeft: '1rem', paddingRight: '1rem' }}
          >
            🔄 Refresh RAG Data
          </button>
        </div>
      </div>

      <div className="rag-controls">
        <input
          type="text"
          placeholder="Filter by category..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          className="rag-filter"
        />
      </div>

      <div className="rag-form" ref={formRef}>
        <h3>{editingId ? 'Edit Item' : 'Add New Item'}</h3>
        <select
          name="category"
          value={formData.category || 'custom'}
          onChange={e =>
            setFormData(prev => ({ ...prev, category: e.target.value }))
          }
          className="form-input"
        >
          <option value="custom">Custom</option>
          <option value="schema">Database Schema</option>
          <option value="relationship">Relationships</option>
          <option value="business_rule">Business Rule</option>
          <option value="sample_data">Sample Data</option>
        </select>

        <input
          type="text"
          name="title"
          placeholder="Title"
          value={formData.title || ''}
          onChange={e =>
            setFormData(prev => ({ ...prev, title: e.target.value }))
          }
          ref={titleRef}
          className="form-input"
        />

        <textarea
          name="content"
          placeholder="Content"
          value={formData.content || ''}
          onChange={e =>
            setFormData(prev => ({ ...prev, content: e.target.value }))
          }
          className="form-textarea"
          rows={4}
        />

        <div className="form-buttons">
          <button onClick={handleSave} className="btn-primary">
            {editingId ? 'Update' : 'Add'}
          </button>
          {editingId && (
            <button onClick={handleCancel} className="btn-secondary">
              Cancel
            </button>
          )}
        </div>
      </div>

      <div className="rag-items">
        {loading ? (
          <p className="loading-text">Loading...</p>
        ) : categories.length === 0 ? (
          <p className="empty-text">No RAG items yet. Add one above!</p>
        ) : (
          categories.map(category => (
            <div key={category} className="category-section">
              <div className="category-header">
                <span className="category-badge">{category}</span>
                <span className="item-count">({groupedItems[category].length})</span>
              </div>

              {groupedItems[category].map(item => (
                <div key={item.id} className="rag-item">
                  <div
                    className="item-header"
                    onClick={() => toggleExpand(item.id)}
                  >
                    <span className="expand-icon">
                      {expandedIds.includes(item.id) ? '▼' : '▶'}
                    </span>
                    <span className="item-title">{truncate(item.title, 50)}</span>
                    <span className="item-source">({truncate(item.source, 40)})</span>
                  </div>

                  {expandedIds.includes(item.id) && (
                    <div className="item-content">
                      <p>{truncate(item.content, 50)}</p>
                      <div className="item-actions">
                        <button
                          onClick={() => handleEdit(item)}
                          className="btn-edit"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="btn-delete"
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))
        )}
      </div>

      <div style={{ marginTop: '2rem' }}>
        <h3>📊 Database Schemas ({schemas.length})</h3>
        {schemas.length === 0 ? (
          <p style={{ color: '#718096' }}>No database schemas available. Connect a database to auto-populate.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem' }}>
            {schemas.map(s => (
              <div key={s.id} className="schema-item" style={{ border: '1px solid #cbd5e0', padding: '1rem', borderRadius: '8px', backgroundColor: '#f7fafc', cursor: 'pointer' }}
                onClick={() => toggleExpand(s.id)}>
                <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{s.metadata?.table_name || s.title}</span>
                  <span style={{ fontSize: '0.85rem', color: '#4a5568', backgroundColor: '#edf2f7', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>Schema</span>
                </div>
                {expandedIds.includes(s.id) && (
                  <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem', fontSize: '0.85rem', backgroundColor: '#fff', padding: '0.5rem', borderRadius: '4px', maxHeight: '200px', overflowY: 'auto' }}>{s.content}</pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: '2rem' }}>
        <h3>🔗 Relationships ({relationships.length})</h3>
        {relationships.length === 0 ? (
          <p style={{ color: '#718096' }}>No relationships found.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem' }}>
            {relationships.map(r => (
              <div key={r.id} className="rule-item" style={{ border: '1px solid #c6f6d5', padding: '1rem', borderRadius: '8px', backgroundColor: '#f0fff4', cursor: 'pointer' }}
                onClick={() => toggleExpand(r.id)}>
                <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{r.name}</span>
                  <span style={{ fontSize: '0.85rem', color: '#22543d', backgroundColor: '#c6f6d5', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>Relationship</span>
                </div>
                {expandedIds.includes(r.id) && (
                  <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem', fontSize: '0.85rem', backgroundColor: '#fff', padding: '0.5rem', borderRadius: '4px', maxHeight: '200px', overflowY: 'auto' }}>{r.content}</pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: '2rem' }}>
        <h3>📋 Sample Data ({sampleData.length})</h3>
        {sampleData.length === 0 ? (
          <p style={{ color: '#718096' }}>No sample data available.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem' }}>
            {sampleData.map(sd => (
              <div key={sd.id} className="sample-item" style={{ border: '1px solid #bee3f8', padding: '1rem', borderRadius: '8px', backgroundColor: '#ebf8ff', cursor: 'pointer' }}
                onClick={() => toggleExpand(sd.id)}>
                <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{sd.name}</span>
                  <span style={{ fontSize: '0.85rem', color: '#2c5aa0', backgroundColor: '#bee3f8', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>Sample Data</span>
                </div>
                {expandedIds.includes(sd.id) && (
                  <pre style={{ whiteSpace: 'pre-wrap', marginTop: '0.5rem', fontSize: '0.85rem', backgroundColor: '#fff', padding: '0.5rem', borderRadius: '4px', maxHeight: '200px', overflowY: 'auto' }}>{sd.content}</pre>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ marginTop: '2rem' }}>
        <h3>📝 Business Rules ({businessRules.length})</h3>
        {businessRules.length === 0 ? (
          <p style={{ color: '#718096' }}>No business rules defined.</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1rem' }}>
            {businessRules.map(br => (
              <div key={br.id} className="rule-item" style={{ border: '1px solid #fbd38d', padding: '1rem', borderRadius: '8px', backgroundColor: '#fffff0', cursor: 'pointer' }}
                onClick={() => toggleExpand(br.id)}>
                <div style={{ fontWeight: 'bold', marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span>{br.name}</span>
                  <span style={{ fontSize: '0.85rem', color: '#7c2d12', backgroundColor: '#fbd38d', padding: '0.25rem 0.5rem', borderRadius: '4px' }}>{br.rule_type}</span>
                </div>
                {expandedIds.includes(br.id) && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.85rem', backgroundColor: '#fff', padding: '0.5rem', borderRadius: '4px', maxHeight: '200px', overflowY: 'auto' }}>{br.content}</pre>
                    <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          setEditingId(br.id)
                          setFormData({
                            category: 'business_rule',
                            title: br.name,
                            content: br.content,
                          })
                        }}
                        className="btn-edit"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
                      >
                        Edit
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}