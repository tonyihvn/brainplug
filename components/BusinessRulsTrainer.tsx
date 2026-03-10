import React, { useState, useEffect } from 'react'
import { apiClient } from '../services/geminiService'
import { showAlert, showLoading, showConfirm, closeSwal } from './swal'

interface BusinessRule {
  id: string;
  name: string;
  description?: string;
  rule_type: 'compulsory' | 'optional' | 'constraint';
  content: string;
  category?: string;
  is_active: boolean;
  created_at: string;
}

interface BusinessRulesTrainerProps {
  forDatabaseMode?: 'api' | 'direct';
  onRulesUpdated?: () => void;
}

export default function BusinessRulesTainer({ forDatabaseMode = 'api', onRulesUpdated }: BusinessRulesTrainerProps) {
  const [rules, setRules] = useState<BusinessRule[]>([])
  const [editingId, setEditingId] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    rule_type: 'optional' as 'compulsory' | 'optional' | 'constraint',
    content: '',
    category: 'general'
  })
  const [filterType, setFilterType] = useState<'all' | 'compulsory' | 'optional' | 'constraint'>('all')
  const [expandedRule, setExpandedRule] = useState<string | null>(null)

  useEffect(() => {
    loadRules()
  }, [])

  const loadRules = async () => {
    try {
      const response = await apiClient.getBusinessRules()
      setRules(response.data.data || [])
    } catch (error) {
      console.error('Error loading business rules:', error)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: value
    }))
  }

  const handleSave = async () => {
    try {
      showLoading('Saving business rule...')
      
      if (!formData.name.trim()) {
        closeSwal()
        await showAlert('Validation Error', 'Rule name is required', 'error')
        return
      }

      if (!formData.content.trim()) {
        closeSwal()
        await showAlert('Validation Error', 'Rule content is required', 'error')
        return
      }

      const dataToSave = editingId ? { ...formData, id: editingId } : formData

      if (editingId) {
        await apiClient.updateBusinessRule(editingId, dataToSave)
      } else {
        await apiClient.createBusinessRule(dataToSave)
      }

      closeSwal()
      await showAlert('Success', 'Business rule saved', 'success')
      await loadRules()
      resetForm()
    } catch (error) {
      closeSwal()
      console.error('Error saving business rule:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      await showAlert('Error', `Failed to save rule: ${errorMsg}`, 'error')
    }
  }

  const handleEdit = (rule: BusinessRule) => {
    setEditingId(rule.id)
    setFormData({
      name: rule.name,
      description: rule.description || '',
      rule_type: rule.rule_type,
      content: rule.content,
      category: rule.category || 'general'
    })
  }

  const handleDelete = async (id: string) => {
    try {
      const ok = await showConfirm('Delete this business rule?', 'This rule will no longer be used by the LLM.')
      if (!ok) return

      showLoading('Deleting rule...')
      await apiClient.deleteBusinessRule(id)
      closeSwal()
      await showAlert('Success', 'Business rule deleted', 'success')
      await loadRules()
    } catch (error) {
      closeSwal()
      console.error('Error deleting business rule:', error)
      await showAlert('Error', 'Failed to delete rule', 'error')
    }
  }

  const handleToggleActive = async (rule: BusinessRule) => {
    try {
      showLoading('Updating rule...')
      await apiClient.updateBusinessRule(rule.id, { ...rule, is_active: !rule.is_active })
      closeSwal()
      await loadRules()
    } catch (error) {
      closeSwal()
      console.error('Error toggling rule:', error)
    }
  }

  const resetForm = () => {
    setEditingId(null)
    setFormData({
      name: '',
      description: '',
      rule_type: 'optional',
      content: '',
      category: 'general'
    })
  }

  const filteredRules = filterType === 'all' 
    ? rules 
    : rules.filter(r => r.rule_type === filterType)

  const compulsoryRules = rules.filter(r => r.rule_type === 'compulsory' && r.is_active)

  return (
    <div style={{ padding: '1.5rem', backgroundColor: '#f7fafc', borderRadius: '8px', marginTop: '2rem' }}>
      <h4>Business Rules & LLM Training</h4>
      <p style={{ color: '#718096', marginBottom: '1rem' }}>
        Train the LLM with domain-specific rules that will be included in every conversation.
        <strong> Compulsory rules</strong> are always included; <strong>optional rules</strong> provide additional context.
      </p>

      {compulsoryRules.length > 0 && (
        <div style={{ 
          marginBottom: '1rem', 
          padding: '1rem', 
          backgroundColor: '#fff5f5', 
          borderLeft: '4px solid #f56565',
          borderRadius: '4px'
        }}>
          <strong style={{ color: '#c53030' }}>⚠️ {compulsoryRules.length} Active Compulsory Rule(s)</strong>
          <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: '#742a2a' }}>
            These rules will be enforced in every LLM response:
          </p>
          <ul style={{ margin: '0.5rem 0', paddingLeft: '1.5rem', color: '#742a2a' }}>
            {compulsoryRules.map(rule => (
              <li key={rule.id}>
                <strong>{rule.name}</strong>: {rule.content.substring(0, 80)}...
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Form for creating/editing */}
      <div style={{ 
        padding: '1rem', 
        backgroundColor: '#fff', 
        border: '1px solid #e2e8f0',
        borderRadius: '6px',
        marginBottom: '1.5rem'
      }}>
        <h5 style={{ marginTop: 0 }}>{editingId ? 'Edit Business Rule' : 'Create New Business Rule'}</h5>

        <div className="form-group-row">
          <div className="form-group">
            <label>Rule Name</label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleInputChange}
              placeholder="e.g., Product Availability Check"
            />
          </div>
          <div className="form-group">
            <label>Rule Type</label>
            <select name="rule_type" value={formData.rule_type} onChange={handleInputChange}>
              <option value="optional">Optional</option>
              <option value="compulsory">Compulsory (Always Enforced)</option>
              <option value="constraint">Constraint (Restrict Behavior)</option>
            </select>
          </div>
        </div>

        <div className="form-group">
          <label>Description (Optional)</label>
          <input
            type="text"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Brief description of what this rule does"
          />
        </div>

        <div className="form-group">
          <label>Rule Content</label>
          <textarea
            name="content"
            value={formData.content}
            onChange={handleInputChange}
            placeholder={`Example for compulsory: "Always check product stock levels before recommending items"\nExample for constraint: "Never suggest discontinued products without mentioning alternatives"`}
            style={{ minHeight: '80px' }}
          />
          <small style={{ color: '#718096', display: 'block', marginTop: '0.5rem' }}>
            Write the rule as a clear instruction for the LLM. Use natural language.
          </small>
        </div>

        <div className="form-actions">
          <button className="btn-save" onClick={handleSave}>
            {editingId ? 'Update Rule' : 'Create Rule'}
          </button>
          {editingId && (
            <button className="btn-cancel" onClick={resetForm}>
              Cancel Editing
            </button>
          )}
        </div>
      </div>

      {/* Filters and List */}
      <div style={{ marginBottom: '1rem' }}>
        <label style={{ marginRight: '1.5rem' }}>
          <strong>Filter by Type:</strong>
        </label>
        <button 
          className={filterType === 'all' ? 'btn-active' : ''}
          style={{ marginRight: '0.5rem' }}
          onClick={() => setFilterType('all')}
        >
          All ({rules.length})
        </button>
        <button 
          className={filterType === 'compulsory' ? 'btn-active' : ''}
          style={{ marginRight: '0.5rem' }}
          onClick={() => setFilterType('compulsory')}
        >
          Compulsory ({rules.filter(r => r.rule_type === 'compulsory').length})
        </button>
        <button 
          className={filterType === 'optional' ? 'btn-active' : ''}
          style={{ marginRight: '0.5rem' }}
          onClick={() => setFilterType('optional')}
        >
          Optional ({rules.filter(r => r.rule_type === 'optional').length})
        </button>
        <button 
          className={filterType === 'constraint' ? 'btn-active' : ''}
          onClick={() => setFilterType('constraint')}
        >
          Constraints ({rules.filter(r => r.rule_type === 'constraint').length})
        </button>
      </div>

      {/* Rules List */}
      {filteredRules.length === 0 ? (
        <p style={{ color: '#718096', textAlign: 'center', padding: '2rem' }}>
          No {filterType !== 'all' ? `${filterType} ` : ''}business rules yet
        </p>
      ) : (
        <div style={{ display: 'grid', gap: '1rem' }}>
          {filteredRules.map(rule => (
            <div key={rule.id} style={{
              border: `1px solid ${rule.is_active ? '#cbd5e0' : '#e2e8f0'}`,
              borderRadius: '6px',
              overflow: 'hidden',
              backgroundColor: rule.is_active ? '#fff' : '#f7fafc'
            }}>
              <div 
                style={{
                  padding: '1rem',
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  backgroundColor: rule.is_active ? '#fff' : '#edf2f7'
                }}
                onClick={() => setExpandedRule(expandedRule === rule.id ? null : rule.id)}
              >
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <strong>{rule.name}</strong>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '3px',
                      fontSize: '0.75rem',
                      fontWeight: 'bold',
                      backgroundColor: rule.rule_type === 'compulsory' 
                        ? '#fed7d7' 
                        : rule.rule_type === 'constraint' 
                        ? '#feebc8' 
                        : '#e6fffa',
                      color: rule.rule_type === 'compulsory' 
                        ? '#742a2a' 
                        : rule.rule_type === 'constraint' 
                        ? '#7c2d12' 
                        : '#234e52'
                    }}>
                      {rule.rule_type}
                    </span>
                    {!rule.is_active && (
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '3px',
                        fontSize: '0.75rem',
                        backgroundColor: '#cbd5e0',
                        color: '#2d3748'
                      }}>
                        inactive
                      </span>
                    )}
                  </div>
                  <p style={{ margin: '0.5rem 0 0 0', fontSize: '0.9rem', color: '#718096' }}>
                    {rule.description || rule.content.substring(0, 100)}
                  </p>
                </div>
                <div style={{
                  fontSize: '1.2rem',
                  marginLeft: '1rem',
                  color: expandedRule === rule.id ? '#4299e1' : '#a0aec0'
                }}>
                  {expandedRule === rule.id ? '▼' : '▶'}
                </div>
              </div>

              {expandedRule === rule.id && (
                <div style={{
                  padding: '1rem',
                  borderTop: '1px solid #e2e8f0',
                  backgroundColor: '#f7fafc'
                }}>
                  <div style={{ marginBottom: '1rem' }}>
                    <h6 style={{ marginTop: 0, marginBottom: '0.5rem' }}>Rule Content</h6>
                    <div style={{
                      padding: '0.75rem',
                      backgroundColor: '#fff',
                      border: '1px solid #e2e8f0',
                      borderRadius: '4px',
                      fontFamily: 'monospace',
                      fontSize: '0.85rem',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word'
                    }}>
                      {rule.content}
                    </div>
                  </div>

                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                    <button 
                      className="btn-edit" 
                      onClick={() => handleEdit(rule)}
                      style={{ flex: 1 }}
                    >
                      Edit
                    </button>
                    <button 
                      className={rule.is_active ? 'btn-delete' : 'btn-save'}
                      onClick={() => handleToggleActive(rule)}
                      style={{ flex: 1 }}
                    >
                      {rule.is_active ? 'Deactivate' : 'Activate'}
                    </button>
                    <button 
                      className="btn-delete" 
                      onClick={() => handleDelete(rule.id)}
                      style={{ flex: 1 }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <div style={{
        marginTop: '1.5rem',
        padding: '1rem',
        backgroundColor: '#edf2f7',
        borderRadius: '4px',
        fontSize: '0.9rem',
        color: '#4a5568'
      }}>
        <strong>💡 Best Practices:</strong>
        <ul style={{ marginBottom: 0, marginTop: '0.5rem', paddingLeft: '1.5rem' }}>
          <li>Use <strong>Compulsory</strong> rules for critical compliance requirements</li>
          <li>Use <strong>Optional</strong> rules for domain knowledge and best practices</li>
          <li>Use <strong>Constraints</strong> to restrict dangerous behaviors</li>
          <li>Rules are included in the LLM prompt with vector DB search results</li>
          <li>Compulsory rules override optional ones; the LLM will prioritize safety</li>
        </ul>
      </div>
    </div>
  )
}
