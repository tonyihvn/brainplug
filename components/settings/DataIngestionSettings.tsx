import React, { useState, useEffect } from 'react'
import { apiClient } from '../../services/geminiService'
import { showAlert, showLoading, closeSwal } from '../swal'
import './DataIngestionSettings.css'

interface TableConfig {
  name: string
  columns: string[]
  query_template: string
  auto_join_related_tables: boolean
  embedding_method: 'raw' | 'semantic'
  sync_interval: number
  enabled: boolean
}

interface IngestionConfig {
  database_id: string
  tables: TableConfig[]
  processing_method: 'raw' | 'semantic'
  auto_detect_relationships: boolean
}

interface Database {
  id: string
  name: string
  host?: string
  port?: number
}

export default function DataIngestionSettings() {
  const [databases, setDatabases] = useState<Database[]>([])
  const [databaseId, setDatabaseId] = useState<string>('')
  const [discoveredTables, setDiscoveredTables] = useState<any[]>([])
  const [selectedTables, setSelectedTables] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [processingMethod, setProcessingMethod] = useState<'raw' | 'semantic'>('semantic')
  const [autoDetectRelationships, setAutoDetectRelationships] = useState(true)
  const [tableConfigs, setTableConfigs] = useState<Record<string, TableConfig>>({})
  const [expandedTables, setExpandedTables] = useState<Set<string>>(new Set())
  const [ingestedDataCount, setIngestedDataCount] = useState<number>(0)
  const [embeddingsSample, setEmbeddingsSample] = useState<any[]>([])
  const [sampleRules, setSampleRules] = useState<any[]>([])

  // Load databases
  const loadDatabases = async () => {
    try {
      const response = await apiClient.getDatabaseSettings()
      const dbs = response.data.data || []
      setDatabases(dbs)
      
      if (dbs.length > 0) {
        setDatabaseId(dbs[0].id)
      }
    } catch (error) {
      console.error('Error loading databases:', error)
    }
  }

  // Discover tables
  const discoverTables = async () => {
    if (!databaseId) {
      showAlert('Error', 'Please select a database', 'error')
      return
    }

    try {
      setLoading(true)
      showLoading('Discovering tables...')
      
      const response = await apiClient.discoverDatabaseTables(databaseId)
      const tables = response.data.data || []
      
      setDiscoveredTables(tables)
      
      // Initialize table configs
      const configs: Record<string, TableConfig> = {}
      tables.forEach((table: any) => {
        configs[table.name] = {
          name: table.name,
          columns: table.columns || [],
          query_template: table.query_template || `SELECT * FROM ${table.name}`,
          auto_join_related_tables: autoDetectRelationships,
          embedding_method: processingMethod,
          sync_interval: 3600,
          enabled: false
        }
      })
      setTableConfigs(configs)
      
      closeSwal()
      showAlert('Success', `Discovered ${tables.length} tables`, 'success')
    } catch (error) {
      closeSwal()
      console.error('Error discovering tables:', error)
      showAlert('Error', 'Failed to discover tables', 'error')
    } finally {
      setLoading(false)
    }
  }

  // Toggle table selection
  const toggleTable = (tableName: string) => {
    const newSelected = new Set(selectedTables)
    if (newSelected.has(tableName)) {
      newSelected.delete(tableName)
    } else {
      newSelected.add(tableName)
    }
    setSelectedTables(newSelected)
  }

  // Toggle table expansion
  const toggleTableExpanded = (tableName: string) => {
    const newExpanded = new Set(expandedTables)
    if (newExpanded.has(tableName)) {
      newExpanded.delete(tableName)
    } else {
      newExpanded.add(tableName)
    }
    setExpandedTables(newExpanded)
  }

  // Update table config
  const updateTableConfig = (tableName: string, updates: Partial<TableConfig>) => {
    setTableConfigs(prev => ({
      ...prev,
      [tableName]: { ...prev[tableName], ...updates }
    }))
  }

  // Configure ingestion
  const configureIngestion = async () => {
    if (selectedTables.size === 0) {
      showAlert('Error', 'Please select at least one table', 'error')
      return
    }

    try {
      showLoading('Configuring ingestion...')
      
      const selectedConfigs = Array.from(selectedTables).map(name => tableConfigs[name])
      
      const response = await apiClient.post('/api/rag/ingest/config', {
        database_id: databaseId,
        tables: selectedConfigs,
        processing_method: processingMethod,
        auto_detect_relationships: autoDetectRelationships
      })
      
      closeSwal()
      const configId = response.data.config_id
      showAlert('Success', `Configuration saved for ${selectedTables.size} tables`, 'success')
      
      return configId
    } catch (error) {
      closeSwal()
      console.error('Error configuring ingestion:', error)
      showAlert('Error', 'Failed to configure ingestion', 'error')
      return null
    }
  }

  // Start ingestion
  const startIngestion = async () => {
    if (selectedTables.size === 0) {
      showAlert('Error', 'Please select at least one table', 'error')
      return
    }

    try {
      setIngesting(true)
      showLoading('Starting data ingestion...')
      
      // First configure
      const configId = await configureIngestion()
      
      if (!configId) {
        setIngesting(false)
        return
      }
      
      // Then ingest
      showLoading('Ingesting data and generating embeddings...')
      
      const response = await apiClient.post('/api/rag/ingest/start', {
        database_id: databaseId,
        tables: Array.from(selectedTables),
        config_id: configId
      })
      
      closeSwal()
      
      const result = response.data
      showAlert(
        'Success',
        `Ingestion complete!\n\n` +
        `Tables: ${result.successful_tables}/${result.tables_processed}\n` +
        `Records: ${result.total_records}\n` +
        `Embeddings: ${result.total_embeddings}`,
        'success'
      )
    } catch (error) {
      closeSwal()
      console.error('Error starting ingestion:', error)
      showAlert('Error', 'Failed to start ingestion', 'error')
    } finally {
      setIngesting(false)
    }
  }

  // Delete ingested data
  const deleteIngestedData = async () => {
    const confirmed = await (window as any).Swal?.fire({
      title: 'Delete Ingested Data?',
      text: 'This will remove all ingested data and embeddings for this database',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      confirmButtonText: 'Yes, Delete All'
    })

    if (!confirmed?.isConfirmed) return

    try {
      showLoading('Deleting ingested data...')
      
      await apiClient.delete(`/api/rag/ingest/delete/${databaseId}`)
      
      closeSwal()
      showAlert('Success', 'All ingested data deleted', 'success')
      setIngestedDataCount(0)
    } catch (error) {
      closeSwal()
      console.error('Error deleting ingested data:', error)
      showAlert('Error', 'Failed to delete ingested data', 'error')
    }
  }

  // Manual ingestion trigger using configured tables
  const triggerManualIngestion = async () => {
    try {
      setIngesting(true)
      showLoading('Starting manual data ingestion from configured tables...')
      
      const response = await apiClient.post('/api/rag/ingest/manual', {
        database_id: databaseId
      })
      
      closeSwal()
      
      const result = response.data
      
      // Update the ingested data count
      if (result.total_records) {
        setIngestedDataCount(result.total_records)
      }
      
      showAlert(
        'Success',
        `Manual ingestion complete!\n\n` +
        `Tables: ${result.successful_tables || 0}/${result.tables_processed || 0}\n` +
        `Records: ${result.total_records || 0}\n` +
        `Embeddings: ${result.total_embeddings || 0}`,
        'success'
      )
    } catch (error: any) {
      closeSwal()
      console.error('Error triggering manual ingestion:', error)
      const errorMsg = error?.response?.data?.error || 'Failed to start ingestion'
      showAlert('Error', errorMsg, 'error')
    } finally {
      setIngesting(false)
    }
  }

  // Check ingested data status
  const checkIngestedDataStatus = async () => {
    try {
      showLoading('Loading ingested data information...')
      
      const response = await apiClient.post('/api/rag/ingest/status', {
        database_id: databaseId
      })
      
      closeSwal()
      
      const data = response.data.data
      let message = 'Ingested Data Summary:\n\n'
      
      if (data.total_records) {
        message += `Total Records: ${data.total_records}\n`
        setIngestedDataCount(data.total_records)
      }
      
      if (data.tables_ingested) {
        message += `Tables Ingested: ${data.tables_ingested}\n`
      }
      
      if (data.last_ingestion) {
        const date = new Date(data.last_ingestion).toLocaleString()
        message += `Last Ingestion: ${date}\n`
      }
      
      if (data.ingested_tables && data.ingested_tables.length > 0) {
        message += `\nTables:\n`
        data.ingested_tables.forEach((table: any) => {
          message += `  • ${table.name}: ${table.records_ingested || 0} records\n`
        })
      }
      
      if (data.storage_path) {
        message += `\nStorage: ${data.storage_path}\n`
      }
      
      // Store sample embeddings if available
      if (data.sample_embeddings && data.sample_embeddings.length > 0) {
        setEmbeddingsSample(data.sample_embeddings)
      }
      
      // Store sample rules if available
      if (data.sample_rules && data.sample_rules.length > 0) {
        setSampleRules(data.sample_rules)
      }
      
      showAlert('Ingested Data Status', message, 'info')
    } catch (error: any) {
      closeSwal()
      console.error('Error checking ingested data status:', error)
      showAlert('Info', 'No ingested data found yet. Run ingestion first.', 'info')
    }
  }

  useEffect(() => {
    loadDatabases()
  }, [])

  return (
    <div className="data-ingestion-settings">
      <h3>📊 Data Ingestion Pipeline</h3>
      <p style={{ marginBottom: '1.5rem', color: '#718096' }}>
        Configure and manage data ingestion from your source database to the local vector database.
        Automatically detect relationships, generate embeddings, and maintain raw data backups.
      </p>

      {/* Database Selection */}
      <div className="setting-section">
        <h4>1️⃣ Select Source Database</h4>
        <select 
          value={databaseId}
          onChange={(e) => setDatabaseId(e.target.value)}
          style={{
            width: '100%',
            padding: '0.75rem',
            marginBottom: '1rem',
            borderRadius: '4px',
            border: '1px solid #e5e7eb',
            fontSize: '1rem'
          }}
        >
          <option value="">Choose a database...</option>
          {databases.map(db => (
            <option key={db.id} value={db.id}>
              {db.name}
            </option>
          ))}
        </select>
        
        <button 
          onClick={discoverTables}
          disabled={!databaseId || loading}
          className="btn-primary"
          style={{ width: '100%' }}
        >
          {loading ? '🔍 Discovering...' : '🔍 Discover Tables'}
        </button>
      </div>

      {/* Processing Method */}
      <div className="setting-section">
        <h4>⚙️ Processing Configuration</h4>
        
        <div style={{ marginBottom: '1rem' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
            Embedding Method
          </label>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <label style={{ cursor: 'pointer' }}>
              <input
                type="radio"
                value="semantic"
                checked={processingMethod === 'semantic'}
                onChange={(e) => setProcessingMethod(e.target.value as any)}
              />
              {' '}Semantic (Recommended) - Uses natural language embeddings
            </label>
            <label style={{ cursor: 'pointer' }}>
              <input
                type="radio"
                value="raw"
                checked={processingMethod === 'raw'}
                onChange={(e) => setProcessingMethod(e.target.value as any)}
              />
              {' '}Raw - Direct vector embedding
            </label>
          </div>
          <p style={{ fontSize: '0.85rem', color: '#718096', marginTop: '0.5rem' }}>
            Semantic method converts database records to natural language before embedding.
            Raw method embeds column values directly.
          </p>
        </div>

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={autoDetectRelationships}
            onChange={(e) => setAutoDetectRelationships(e.target.checked)}
          />
          <span>Auto-detect and ingest related tables</span>
        </label>
        <p style={{ fontSize: '0.85rem', color: '#718096', marginTop: '0.5rem' }}>
          Automatically fetch records from related tables based on foreign keys.
        </p>
      </div>

      {/* Table Selection */}
      {discoveredTables.length > 0 && (
        <div className="setting-section">
          <h4>2️⃣ Select Tables to Ingest</h4>
          
          <div style={{ marginBottom: '1rem' }}>
            <button
              onClick={() => setSelectedTables(new Set(discoveredTables.map(t => t.name)))}
              className="link-button"
            >
              ✓ Select All
            </button>
            <span> | </span>
            <button
              onClick={() => setSelectedTables(new Set())}
              className="link-button"
            >
              ✗ Clear Selection
            </button>
          </div>

          <div style={{ display: 'grid', gap: '0.75rem' }}>
            {discoveredTables.map(table => {
              const config = tableConfigs[table.name] || {}
              const isExpanded = expandedTables.has(table.name)
              const isSelected = selectedTables.has(table.name)

              return (
                <div
                  key={table.name}
                  style={{
                    border: isSelected ? '2px solid #3b82f6' : '1px solid #e5e7eb',
                    borderRadius: '6px',
                    overflow: 'hidden',
                    backgroundColor: isSelected ? '#eff6ff' : '#fff'
                  }}
                >
                  <div
                    style={{
                      padding: '1rem',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '1rem',
                      cursor: 'pointer',
                      backgroundColor: isSelected ? '#eff6ff' : '#fff'
                    }}
                    onClick={() => toggleTable(table.name)}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      onClick={(e) => e.stopPropagation()}
                    />
                    <div style={{ flex: 1 }}>
                      <strong style={{ color: '#1f2937' }}>{table.name}</strong>
                      <span style={{ color: '#6b7280', marginLeft: '0.5rem' }}>
                        {table.columns?.length || 0} columns
                      </span>
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleTableExpanded(table.name)
                      }}
                      style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}
                    >
                      {isExpanded ? '▼' : '▶'}
                    </button>
                  </div>

                  {isExpanded && (
                    <div style={{
                      padding: '1rem',
                      borderTop: '1px solid #e5e7eb',
                      backgroundColor: '#f9fafb'
                    }}>
                      <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                          Query Template
                        </label>
                        <textarea
                          value={config.query_template || `SELECT * FROM ${table.name}`}
                          onChange={(e) => updateTableConfig(table.name, { query_template: e.target.value })}
                          rows={3}
                          className="form-textarea"
                        />
                      </div>

                      <div style={{ marginBottom: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                          Sync Interval (seconds)
                        </label>
                        <input
                          type="number"
                          value={config.sync_interval || 3600}
                          onChange={(e) => updateTableConfig(table.name, { sync_interval: parseInt(e.target.value) })}
                          min={300}
                          step={300}
                          className="form-input"
                        />
                      </div>

                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={config.auto_join_related_tables !== false}
                          onChange={(e) => updateTableConfig(table.name, { auto_join_related_tables: e.target.checked })}
                        />
                        <span>Auto-join related tables</span>
                      </label>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Actions */}
      {selectedTables.size > 0 && (
        <div className="setting-section">
          <h4>3️⃣ Ingestion Actions</h4>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <button
              onClick={startIngestion}
              disabled={ingesting}
              className="btn-success"
              style={{ width: '100%' }}
            >
              {ingesting ? '⏳ Ingesting...' : '🚀 Start Ingestion'}
            </button>
            
            <button
              onClick={deleteIngestedData}
              disabled={ingesting}
              className="btn-danger"
              style={{ width: '100%' }}
            >
              🗑️ Delete All Data
            </button>
          </div>

          <p style={{
            marginTop: '1rem',
            padding: '0.75rem',
            backgroundColor: '#fef3c7',
            borderLeft: '4px solid #f59e0b',
            borderRadius: '4px',
            fontSize: '0.9rem',
            color: '#92400e'
          }}>
            <strong>ℹ️ Note:</strong> Ingestion will pull {selectedTables.size} table(s),
            detect {autoDetectRelationships ? 'and fetch' : 'but skip'} related records,
            generate {processingMethod} embeddings, and backup raw data.
          </p>
        </div>
      )}

      {/* Manual Ingestion Trigger */}
      <div className="setting-section">
        <h4>⚡ Manual Ingestion Trigger</h4>
        <p style={{ color: '#718096', marginBottom: '1rem', fontSize: '0.9rem' }}>
          Trigger ingestion immediately for all configured tables in this database without re-selecting them.
        </p>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem' }}>
          <button
            onClick={triggerManualIngestion}
            disabled={ingesting || !databaseId}
            className="btn-success"
            title="Ingest all pre-configured tables"
            style={{
              backgroundColor: ingesting ? '#9ca3af' : '#10b981',
              padding: '0.75rem'
            }}
          >
            {ingesting ? 'Ingesting...' : 'Manual Ingest Now'}
          </button>
          
          <button
            onClick={checkIngestedDataStatus}
            disabled={ingesting || !databaseId}
            className="btn-info"
            title="View ingested data summary"
            style={{
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            View Data Info
          </button>
          
          <button
            onClick={() => {
              showAlert(
                'View Embedded Data',
                'Embedded data is stored at:\n\n' +
                'Vectors: ./chroma_data/\n' +
                'Raw Data: instance/ingested_data/{database_id}/\n\n' +
                'Use Python script (view_ingested_data.py) or File Explorer to browse.\n\n' +
                'See VIEW_INGESTED_DATA_GUIDE.md for detailed instructions.',
                'info'
              )
            }}
            className="btn-info"
            title="Show where embedded data is stored"
            style={{
              backgroundColor: '#6366f1',
              color: 'white',
              border: 'none',
              padding: '0.75rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            View Stored Data
          </button>
        </div>
        
        {ingestedDataCount > 0 && (
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem',
            backgroundColor: '#dbeafe',
            border: '1px solid #0ea5e9',
            borderRadius: '4px',
            fontSize: '0.9rem',
            color: '#0c4a6e'
          }}>
            [OK] <strong>{ingestedDataCount} records</strong> are currently ingested for this database
          </div>
        )}
        
        {embeddingsSample.length > 0 && (
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: '#f0fdf4',
            border: '1px solid #86efac',
            borderRadius: '4px',
            fontSize: '0.85rem',
            color: '#166534'
          }}>
            <strong>📊 Sample Ingested Data ({embeddingsSample.length}):</strong>
            <div style={{ marginTop: '0.5rem', maxHeight: '200px', overflowY: 'auto' }}>
              {embeddingsSample.map((emb, i) => (
                <div key={i} style={{ marginBottom: '0.5rem', padding: '0.5rem', backgroundColor: 'rgba(255,255,255,0.7)', borderRadius: '3px' }}>
                  <strong>ID:</strong> {emb.id?.substring(0, 30)}...<br/>
                  <strong>Table:</strong> {emb.table || 'N/A'}<br/>
                  <strong>Content:</strong> {emb.content?.substring(0, 80)}...
                </div>
              ))}
            </div>
          </div>
        )}
        
        {sampleRules.length > 0 && (
          <div style={{
            marginTop: '1rem',
            padding: '1rem',
            backgroundColor: '#fef3c7',
            border: '1px solid #fcd34d',
            borderRadius: '4px',
            fontSize: '0.85rem',
            color: '#78350f'
          }}>
            <strong>📚 Sample Business Rules with Embeddings ({sampleRules.length}):</strong>
            <div style={{ marginTop: '0.5rem', maxHeight: '250px', overflowY: 'auto' }}>
              {sampleRules.map((rule, i) => (
                <div key={i} style={{ marginBottom: '0.75rem', padding: '0.75rem', backgroundColor: 'rgba(255,255,255,0.8)', borderRadius: '3px', border: '1px solid #fde68a' }}>
                  <strong>Rule:</strong> {rule.id?.substring(0, 35)}...<br/>
                  <strong>Content:</strong> {rule.content?.substring(0, 100)}...<br/>
                  <strong>Embedding:</strong> {rule.has_embedding ? (
                    <span style={{ color: '#059669', fontWeight: 'bold' }}>✓ Yes ({rule.embedding_dims} dimensions)</span>
                  ) : (
                    <span style={{ color: '#dc2626', fontWeight: 'bold' }}>✗ Not generated yet</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Info */}
      <div style={{
        marginTop: '2rem',
        padding: '1rem',
        backgroundColor: '#e0f2fe',
        border: '1px solid #0ea5e9',
        borderRadius: '6px',
        fontSize: '0.9rem',
        color: '#0c4a6e'
      }}>
        <strong>📚 How Ingestion Works:</strong>
        <ul style={{ marginTop: '0.5rem', marginBottom: 0 }}>
          <li><strong>Extract:</strong> Query source database with your custom SQL</li>
          <li><strong>Transform:</strong> Convert records to natural language (if semantic)</li>
          <li><strong>Relate:</strong> Fetch related records from linked tables</li>
          <li><strong>Embed:</strong> Generate vector embeddings for semantic search</li>
          <li><strong>Store:</strong> Save embeddings in vector DB + raw data backup</li>
          <li><strong>Query:</strong> Use RAG mode to query this ingested data</li>
        </ul>
      </div>
    </div>
  )
}
