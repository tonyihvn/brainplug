import React, { useState, useEffect } from 'react'
import { TableConfig, ForeignKey, Index } from '../types'
import { apiClient } from '../services/geminiService'
import { showAlert, showLoading, closeSwal } from './swal'

interface APIQueryConfigProps {
  databaseId: string;
  databaseName: string;
  initialConfig?: Record<string, TableConfig>;
  onConfigSave: (config: Record<string, TableConfig>) => void;
}

interface RelatedTable {
  table: string;
  local_column: string;
  remote_column: string;
}

interface TableRelationships {
  table: string;
  referenced_by: RelatedTable[];
  references: RelatedTable[];
  all_tables: string[];
}

export default function APIQueryConfig({ databaseId, databaseName, initialConfig = {}, onConfigSave }: APIQueryConfigProps) {
  const [tables, setTables] = useState<Map<string, TableConfig>>(new Map(Object.entries(initialConfig)))
  const [discoveringTables, setDiscoveringTables] = useState(false)
  const [editingTable, setEditingTable] = useState<string | null>(null)
  const [editQuery, setEditQuery] = useState('')
  const [editInterval, setEditInterval] = useState(60)
  const [expandedRow, setExpandedRow] = useState<string | null>(null)
  const [queryTextareaRef, setQueryTextareaRef] = useState<HTMLTextAreaElement | null>(null)
  const [restrictedKeywords, setRestrictedKeywords] = useState<string[]>([])
  const [tableRelationships, setTableRelationships] = useState<Map<string, TableRelationships>>(new Map())

  useEffect(() => {
    loadRestrictedKeywords()
  }, [])

  const loadRestrictedKeywords = async () => {
    try {
      const response = await apiClient.getSystemSettings()
      const data = response.data.data
      if (data.restricted_keywords) {
        const restricted = Object.entries(data.restricted_keywords)
          .filter(([_, isRestricted]) => isRestricted)
          .map(([keyword, _]) => keyword)
        setRestrictedKeywords(restricted)
      }
    } catch (error) {
      console.error('Error loading restricted keywords:', error)
    }
  }

  const loadTableRelationships = async (tableName: string) => {
    try {
      const response = await apiClient.getTableRelationships(databaseId, tableName)
      const relationships = response.data.data
      setTableRelationships(prev => new Map(prev).set(tableName, relationships))
      return relationships
    } catch (error) {
      console.error(`Error loading relationships for ${tableName}:`, error)
      return null
    }
  }

  const validateQuery = (query: string): { valid: boolean; message?: string } => {
    const upperQuery = query.toUpperCase()
    
    for (const keyword of restrictedKeywords) {
      // Check if keyword appears as a complete word (not as part of another word)
      const regex = new RegExp(`\\b${keyword}\\b`, 'i')
      if (regex.test(upperQuery)) {
        return {
          valid: false,
          message: `The SQL keyword "${keyword}" is restricted and cannot be used in extraction queries. Your query was blocked for security.`
        }
      }
    }
    
    return { valid: true }
  }

  const insertFieldName = (fieldName: string) => {
    if (!queryTextareaRef) return
    
    const textarea = queryTextareaRef
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    
    const newQuery = editQuery.substring(0, start) + fieldName + editQuery.substring(end)
    setEditQuery(newQuery)
    
    // Move cursor after inserted text
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + fieldName.length
      textarea.focus()
    }, 0)
  }

  const handleDiscoverTables = async () => {
    try {
      setDiscoveringTables(true)
      showLoading('Discovering tables...')
      
      const response = await apiClient.discoverTables(databaseId)
      const discoveredTables = response.data.data || []
      
      // Convert to TableConfig format
      const newTables = new Map<string, TableConfig>()
      for (const table of discoveredTables) {
        newTables.set(table.name, {
          name: table.name,
          enabled: false,
          columns: table.columns,
          query_template: table.query_template,
          sync_interval: 60,
          conditions: {},
          sample_count: table.sample_count,
          foreign_keys: table.foreign_keys || [],
          indexes: table.indexes || [],
          primary_keys: table.primary_keys || []
        })
      }
      
      setTables(newTables)
      closeSwal()
      await showAlert('Success', `Discovered ${discoveredTables.length} tables`, 'success')
    } catch (error) {
      closeSwal()
      console.error('Error discovering tables:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      await showAlert('Error', `Failed to discover tables: ${errorMsg}`, 'error')
    } finally {
      setDiscoveringTables(false)
    }
  }

  const autoCheckRelatedTables = async (tableName: string, isEnabled: boolean) => {
    if (!isEnabled) return // Only auto-check when enabling, not disabling
    
    const relationships = await loadTableRelationships(tableName)
    if (!relationships) return
    
    const updatedTables = new Map(tables)
    const currentTable = updatedTables.get(tableName)
    if (!currentTable) return
    
    // Auto-check tables that reference this table (referenced_by)
    for (const relation of relationships.referenced_by) {
      const relatedTable = updatedTables.get(relation.table)
      if (relatedTable && !relatedTable.enabled) {
        relatedTable.enabled = true
        
        // Auto-generate WHERE clause for the related table
        const whereClause = `WHERE ${relation.local_column} IN (SELECT ${relation.remote_column} FROM ${tableName})`
        relatedTable.query_template = `SELECT * FROM ${relation.table} ${whereClause}`
        
        updatedTables.set(relation.table, relatedTable)
      }
    }
    
    // Auto-check tables this table references (references)
    for (const relation of relationships.references) {
      const relatedTable = updatedTables.get(relation.table)
      if (relatedTable && !relatedTable.enabled) {
        relatedTable.enabled = true
        updatedTables.set(relation.table, relatedTable)
      }
    }
    
    setTables(updatedTables)
  }

  const handleToggleTable = (tableName: string) => {
    const updatedTables = new Map(tables)
    const config = updatedTables.get(tableName)
    if (config) {
      config.enabled = !config.enabled
      updatedTables.set(tableName, config)
      setTables(updatedTables)
      
      // Auto-check related tables if enabling
      if (config.enabled) {
        autoCheckRelatedTables(tableName, true)
      }
    }
  }

  const handleEditQuery = (tableName: string) => {
    const config = tables.get(tableName)
    if (config) {
      setEditingTable(tableName)
      setEditQuery(config.query_template)
      setEditInterval(config.sync_interval)
      
      // Pre-load relationships for this table
      if (!tableRelationships.has(tableName)) {
        loadTableRelationships(tableName)
      }
    }
  }

  const handleSaveQuery = () => {
    if (editingTable) {
      // Validate query for restricted keywords
      const validation = validateQuery(editQuery)
      if (!validation.valid) {
        showAlert('Query Blocked', validation.message || 'Query contains restricted keywords', 'error')
        return
      }

      const updatedTables = new Map(tables)
      const config = updatedTables.get(editingTable)
      if (config) {
        config.query_template = editQuery
        config.sync_interval = editInterval
        updatedTables.set(editingTable, config)
        setTables(updatedTables)
      }
      setEditingTable(null)
      showAlert('Success', 'Query saved successfully', 'success')
    }
  }

  const handleSaveAll = async () => {
    try {
      showLoading('Saving table configuration...')
      
      // Give React time to render the loading modal
      await new Promise(resolve => setTimeout(resolve, 100))
      
      const configObject = Object.fromEntries(tables)
      
      // Call the callback (might be async for parent state update)
      try {
        await Promise.resolve(onConfigSave(configObject))
      } catch (err) {
        // onConfigSave might not be async, that's okay
        console.debug('Config save callback completed')
      }
      
      // Close loading modal
      closeSwal()
      
      // Wait a bit before showing success
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Show success alert
      await showAlert('Success', `Table configuration saved with ${Array.from(tables.values()).filter(t => t.enabled).length} tables enabled`, 'success')
    } catch (error) {
      closeSwal()
      console.error('Error saving configuration:', error)
      await showAlert('Error', 'Failed to save configuration', 'error')
    }
  }

  const enabledCount = Array.from(tables.values()).filter(t => t.enabled).length
  const relationships = editingTable ? tableRelationships.get(editingTable) : null

  return (
    <div style={{ marginTop: '2rem', padding: '1rem', backgroundColor: '#f7fafc', borderRadius: '8px' }}>
      <h4>API Query Configuration</h4>
      <p style={{ color: '#718096', marginBottom: '1rem' }}>
        Select tables to be synced into a local vector database. Data will be pulled at specified intervals
        and made available to the LLM via semantic search without direct database access.
      </p>

      <div style={{ marginBottom: '1.5rem' }}>
        <button 
          className="btn-save"
          onClick={handleDiscoverTables}
          disabled={discoveringTables}
          style={{ marginRight: '1rem' }}
        >
          {discoveringTables ? 'Discovering...' : 'Discover Tables'}
        </button>
        
        {tables.size > 0 && (
          <span style={{ marginLeft: '1rem', color: '#2d3748' }}>
            <strong>{enabledCount}</strong> of <strong>{tables.size}</strong> tables selected
          </span>
        )}
      </div>

      {tables.size === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#718096' }}>
          <p>No tables discovered yet. Click "Discover Tables" to get started.</p>
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="table" style={{ marginBottom: '1.5rem' }}>
            <thead>
              <tr>
                <th style={{ width: '40px' }}>
                  <input 
                    type="checkbox" 
                    checked={Array.from(tables.values()).every(t => t.enabled)}
                    onChange={(e) => {
                      const newTables = new Map(tables)
                      newTables.forEach((config) => {
                        config.enabled = e.target.checked
                      })
                      setTables(newTables)
                    }}
                  />
                </th>
                <th>Table Name</th>
                <th>Columns</th>
                <th>Sync Interval</th>
                <th>Sample Count</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {Array.from(tables.entries()).map(([tableName, config]) => (
                <React.Fragment key={tableName}>
                  <tr style={{ backgroundColor: config.enabled ? '#edf2f7' : 'transparent' }}>
                    <td>
                      <input 
                        type="checkbox" 
                        checked={config.enabled}
                        onChange={() => handleToggleTable(tableName)}
                      />
                    </td>
                    <td><strong>{tableName}</strong></td>
                    <td>{config.columns.length}</td>
                    <td>{config.sync_interval} min</td>
                    <td>{config.sample_count || 'N/A'}</td>
                    <td>
                      <button 
                        className="btn-edit"
                        onClick={() => {
                          if (expandedRow === tableName) {
                            setExpandedRow(null)
                          } else {
                            setExpandedRow(tableName)
                            handleEditQuery(tableName)
                          }
                        }}
                        disabled={!config.enabled}
                      >
                        {expandedRow === tableName ? 'Close' : 'Configure'}
                      </button>
                    </td>
                  </tr>
                  
                  {expandedRow === tableName && config.enabled && editingTable === tableName && (
                    <tr>
                      <td colSpan={6} style={{ padding: '1rem', backgroundColor: '#edf2f7' }}>
                        <div style={{ marginBottom: '1rem' }}>
                          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                            Extraction Query
                          </label>
                          <textarea
                            ref={setQueryTextareaRef}
                            value={editQuery}
                            onChange={(e) => setEditQuery(e.target.value)}
                            style={{
                              width: '100%',
                              minHeight: '100px',
                              padding: '0.5rem',
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              borderColor: restrictedKeywords.length > 0 ? '#fed7d7' : undefined,
                              backgroundColor: restrictedKeywords.length > 0 ? '#fff5f5' : undefined
                            }}
                            placeholder="Enter SQL query to extract data from this table"
                          />
                          <small style={{ color: '#718096', display: 'block', marginTop: '0.5rem' }}>
                            Tip: Click column names below to insert them. This query will be executed periodically to pull data into the vector database.
                            {restrictedKeywords.length > 0 && (
                              <span style={{ display: 'block', color: '#c53030', marginTop: '0.5rem', fontWeight: 'bold' }}>
                                WARNING: The following keywords are restricted and cannot be used: {restrictedKeywords.join(', ')}
                              </span>
                            )}
                          </small>
                        </div>

                        <div style={{ marginBottom: '1rem' }}>
                          <label>
                            Sync Interval (minutes):
                            <input
                              type="number"
                              min="5"
                              max="1440"
                              value={editInterval}
                              onChange={(e) => setEditInterval(parseInt(e.target.value))}
                              style={{ marginLeft: '0.5rem', width: '100px' }}
                            />
                          </label>
                          <small style={{ color: '#718096', display: 'block', marginTop: '0.5rem' }}>
                            How often to sync this table (minimum 5 minutes)
                          </small>
                        </div>

                        <div style={{ marginBottom: '1rem' }}>
                          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                            Columns ({config.columns.length})
                          </label>
                          <div style={{ 
                            display: 'flex', 
                            flexWrap: 'wrap', 
                            gap: '0.5rem',
                            padding: '0.5rem',
                            backgroundColor: '#fff',
                            borderRadius: '4px'
                          }}>
                            {config.columns.map((col) => (
                              <span 
                                key={col}
                                onClick={() => insertFieldName(col)}
                                style={{
                                  padding: '0.25rem 0.75rem',
                                  backgroundColor: config.primary_keys?.includes(col) ? '#bee3f8' : '#cbd5e0',
                                  borderRadius: '4px',
                                  fontSize: '0.85rem',
                                  cursor: 'pointer',
                                  userSelect: 'none',
                                  transition: 'all 0.2s',
                                  border: config.primary_keys?.includes(col) ? '2px solid #2b6cb0' : 'none'
                                }}
                                onMouseEnter={(e) => {
                                  e.currentTarget.style.backgroundColor = '#4299e1'
                                  e.currentTarget.style.color = '#fff'
                                }}
                                onMouseLeave={(e) => {
                                  e.currentTarget.style.backgroundColor = config.primary_keys?.includes(col) ? '#bee3f8' : '#cbd5e0'
                                  e.currentTarget.style.color = 'inherit'
                                }}
                                title={`Click to insert "${col}" into query${config.primary_keys?.includes(col) ? ' (Primary Key)' : ''}`}
                              >
                                {col}
                              </span>
                            ))}
                          </div>
                          <small style={{ color: '#718096', display: 'block', marginTop: '0.5rem', fontStyle: 'italic' }}>
                            Click any column name above to insert it at your cursor position. Primary keys are highlighted in blue.
                          </small>
                        </div>

                        {/* Foreign Keys Section */}
                        {config.foreign_keys && config.foreign_keys.length > 0 && (
                          <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', color: '#2d3748' }}>
                              Foreign Keys ({config.foreign_keys.length})
                            </label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              {config.foreign_keys.map((fk: ForeignKey, idx: number) => (
                                <div key={idx} style={{ 
                                  padding: '0.5rem', 
                                  backgroundColor: '#edf2f7', 
                                  borderRadius: '4px',
                                  fontSize: '0.85rem',
                                  borderLeft: '3px solid #4299e1'
                                }}>
                                  <strong>{fk.column}</strong> → <span style={{ color: '#2b6cb0' }}>{fk.references_table}.{fk.references_column}</span>
                                </div>
                              ))}
                            </div>
                            <small style={{ color: '#718096', display: 'block', marginTop: '0.5rem' }}>
                              These columns link this table to other tables. When you enable this table, related tables are automatically checked with proper WHERE conditions.
                            </small>
                          </div>
                        )}

                        {/* Indexes Section */}
                        {config.indexes && config.indexes.length > 0 && (
                          <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', color: '#2d3748' }}>
                              Indexes ({config.indexes.length})
                            </label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                              {config.indexes.map((idx: Index, i: number) => (
                                <div key={i} style={{ 
                                  padding: '0.5rem', 
                                  backgroundColor: '#edf2f7', 
                                  borderRadius: '4px',
                                  fontSize: '0.85rem',
                                  borderLeft: '3px solid #48bb78'
                                }}>
                                  <strong>{idx.name}</strong> {idx.type && `(${idx.type})`}
                                  <div style={{ fontSize: '0.8rem', color: '#4a5568', marginTop: '0.25rem' }}>
                                    Columns: {idx.columns.join(', ')}
                                  </div>
                                </div>
                              ))}
                            </div>
                            <small style={{ color: '#718096', display: 'block', marginTop: '0.5rem' }}>
                              Indexes optimize queries on these columns. Consider using them in your WHERE conditions.
                            </small>
                          </div>
                        )}

                        {/* Related Tables Section */}
                        {relationships && (relationships.referenced_by.length > 0 || relationships.references.length > 0) && (
                          <div style={{ marginBottom: '1rem', padding: '0.75rem', backgroundColor: '#f0fff4', borderRadius: '4px', border: '1px solid #9ae6b4' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold', color: '#22543d' }}>
                              Related Tables (Auto-Sync)
                            </label>
                            
                            {relationships.referenced_by.length > 0 && (
                              <div style={{ marginBottom: '0.5rem' }}>
                                <strong style={{ fontSize: '0.9rem', color: '#22543d' }}>Tables Referencing This Table:</strong>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.25rem' }}>
                                  {relationships.referenced_by.map((rel: RelatedTable, i: number) => (
                                    <div key={i} style={{ 
                                      fontSize: '0.85rem', 
                                      color: '#22543d',
                                      paddingLeft: '1rem'
                                    }}>
                                      {rel.table} ({rel.local_column} = {tableName}.{rel.remote_column})
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            {relationships.references.length > 0 && (
                              <div>
                                <strong style={{ fontSize: '0.9rem', color: '#22543d' }}>Tables This Table References:</strong>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', marginTop: '0.25rem' }}>
                                  {relationships.references.map((rel: RelatedTable, i: number) => (
                                    <div key={i} style={{ 
                                      fontSize: '0.85rem', 
                                      color: '#22543d',
                                      paddingLeft: '1rem'
                                    }}>
                                      {rel.table} ({rel.local_column} = {rel.remote_column})
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            
                            <small style={{ color: '#22543d', display: 'block', marginTop: '0.5rem', fontStyle: 'italic' }}>
                              Related tables are automatically enabled when you select this table, with WHERE conditions applied to link the data.
                            </small>
                          </div>
                        )}

                        <div style={{ marginTop: '1rem' }}>
                          <button className="btn-save" onClick={handleSaveQuery} style={{ marginRight: '0.5rem' }}>
                            Save Configuration
                          </button>
                          <button 
                            className="btn-cancel" 
                            onClick={() => setEditingTable(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>

          {enabledCount > 0 && (
            <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: '#f0fff4', borderRadius: '4px', borderLeft: '4px solid #48bb78' }}>
              <p style={{ marginBottom: '1rem', color: '#22543d' }}>
                <strong>{enabledCount} table(s) selected for ingestion</strong>. 
                When you save the database connection, the selected tables will be:
              </p>
              <ul style={{ color: '#22543d', marginLeft: '1.5rem', marginBottom: '1rem' }}>
                <li>Automatically queried at specified intervals</li>
                <li>Converted to natural language chunks</li>
                <li>Stored in a local vector database</li>
                <li>Made available to the LLM for context via semantic search</li>
                <li>Related tables will be synced together with proper foreign key conditions</li>
              </ul>
              <p style={{ marginBottom: '0', color: '#22543d', fontSize: '0.9rem' }}>
                ⚠️ The LLM will search this data instead of querying the raw database directly.
              </p>
            </div>
          )}

          {enabledCount > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <button className="btn-save" onClick={handleSaveAll}>
                Save All Configurations
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
