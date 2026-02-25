import React, { useState, useEffect } from 'react'
import { apiClient } from '../services/geminiService'
import DataTable from './DataTable'
import './DBMS.css'

interface Database {
  id: string
  name: string
  db_type: string
  host: string
  database: string
  is_active: boolean
}

interface Table {
  name: string
  column_count: number
  has_primary_key: boolean
  has_foreign_keys: boolean
}

interface Column {
  name: string
  type: string
  nullable: boolean
  default?: string
}

interface ForeignKey {
  constrained_columns: string[]
  referred_table: string
}

export default function DBMSExplorer() {
  const [databases, setDatabases] = useState<Database[]>([])
  const [selectedDb, setSelectedDb] = useState<string | null>(null)
  const [tables, setTables] = useState<Table[]>([])
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [tableData, setTableData] = useState<any[]>([])
  const [tableSchema, setTableSchema] = useState<any>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadDatabases()
  }, [])

  const loadDatabases = async () => {
    try {
      const response = await apiClient.getDBMSDatabases()
      setDatabases(response.data.data || [])
      
      // Auto-select first active database
      const active = response.data.data?.find((db: Database) => db.is_active)
      if (active) {
        setSelectedDb(active.id)
        loadTables(active.id)
      }
    } catch (error) {
      console.error('Error loading databases:', error)
    }
  }

  const loadTables = async (dbId: string) => {
    try {
      setLoading(true)
      const response = await apiClient.getDBMSTables(dbId)
      setTables(response.data.data || [])
      setSelectedTable(null)
      setTableData([])
      setTableSchema(null)
    } catch (error) {
      console.error('Error loading tables:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTableData = async (dbId: string, tableName: string, page = 1) => {
    try {
      setLoading(true)
      const response = await apiClient.getTableData(dbId, tableName, page, 20)
      setTableData(response.data.data || [])
      setCurrentPage(response.data.page)
      setTotalPages(response.data.total_pages)
    } catch (error) {
      console.error('Error loading table data:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadTableSchema = async (dbId: string, tableName: string) => {
    try {
      setLoading(true)
      const response = await apiClient.getTableSchema(dbId, tableName)
      setTableSchema(response.data.data)
    } catch (error) {
      console.error('Error loading table schema:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSelectTable = async (tableName: string) => {
    if (!selectedDb) return
    
    setSelectedTable(tableName)
    await loadTableData(selectedDb, tableName)
    await loadTableSchema(selectedDb, tableName)
  }

  const handleDatabaseChange = (dbId: string) => {
    setSelectedDb(dbId)
    loadTables(dbId)
  }

  const columns = tableData.length > 0 ? Object.keys(tableData[0]) : []

  return (
    <div className="dbms-explorer">
      <div className="dbms-sidebar">
        <h3>Databases</h3>
        <div className="db-list">
          {databases.map(db => (
            <div
              key={db.id}
              className={`db-item ${selectedDb === db.id ? 'active' : ''} ${db.is_active ? 'is-active' : ''}`}
              onClick={() => handleDatabaseChange(db.id)}
            >
              <div className="db-name">{db.name}</div>
              <div className="db-type">{db.db_type}</div>
              {db.is_active && <span className="active-badge">● Active</span>}
            </div>
          ))}
        </div>

        <h3>Tables</h3>
        <div className="table-list">
          {loading ? (
            <div className="loading">Loading tables...</div>
          ) : tables.length > 0 ? (
            tables.map(table => (
              <div
                key={table.name}
                className={`table-item ${selectedTable === table.name ? 'active' : ''}`}
                onClick={() => handleSelectTable(table.name)}
              >
                <div className="table-name">{table.name}</div>
                <div className="table-info">
                  {table.column_count} cols
                  {table.has_primary_key && ' • PK'}
                  {table.has_foreign_keys && ' • FK'}
                </div>
              </div>
            ))
          ) : (
            <div className="empty">No tables</div>
          )}
        </div>
      </div>

      <div className="dbms-main">
        {selectedTable && tableSchema ? (
          <>
            <div className="table-header">
              <h2>{selectedTable}</h2>
              <div className="table-stats">
                {columns.length} columns • {tableData.length} rows displayed
              </div>
            </div>

            {/* Data Table */}
            <div className="data-section">
              <h3>Data</h3>
              {tableData.length > 0 ? (
                <>
                  <DataTable 
                    columns={columns.map((col: string) => ({ key: col, label: col }))} 
                    data={tableData} 
                  />
                  <div className="pagination">
                    <button
                      onClick={() => loadTableData(selectedDb!, selectedTable, currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      Previous
                    </button>
                    <span>{currentPage} / {totalPages}</span>
                    <button
                      onClick={() => loadTableData(selectedDb!, selectedTable, currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Next
                    </button>
                  </div>
                </>
              ) : (
                <div className="empty">No data in table</div>
              )}
            </div>

            {/* Schema Section */}
            <div className="schema-section">
              {/* Columns */}
              <div className="schema-part">
                <h3>Columns</h3>
                <div className="columns-list">
                  {tableSchema.columns?.map((col: Column) => (
                    <div key={col.name} className="column-item">
                      <strong>{col.name}</strong>
                      <span className="col-type">{col.type}</span>
                      {!col.nullable && <span className="not-null">NOT NULL</span>}
                    </div>
                  ))}
                </div>
              </div>

              {/* Primary Keys */}
              {tableSchema.primary_keys?.length > 0 && (
                <div className="schema-part">
                  <h3>Primary Keys</h3>
                  <div className="keys-list">
                    {tableSchema.primary_keys.map((key: string) => (
                      <div key={key} className="key-item">🔑 {key}</div>
                    ))}
                  </div>
                </div>
              )}

              {/* Foreign Keys */}
              {tableSchema.foreign_keys?.length > 0 && (
                <div className="schema-part">
                  <h3>Foreign Keys</h3>
                  <div className="keys-list">
                    {tableSchema.foreign_keys.map((fk: ForeignKey, idx: number) => (
                      <div key={idx} className="fk-item">
                        <div>{fk.constrained_columns.join(', ')}</div>
                        <div className="fk-arrow">→</div>
                        <div>{fk.referred_table}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <p>Select a database and table to explore</p>
          </div>
        )}
      </div>
    </div>
  )
}
