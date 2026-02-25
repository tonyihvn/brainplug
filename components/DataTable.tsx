import React, { useState, useMemo } from 'react'
import './DataTable.css'

interface Column {
  key: string
  label: string
}

interface DataTableProps {
  columns: Column[]
  data: any[]
  title?: string
  onView?: (row: any) => void
}

export default function DataTable({ columns, data, title, onView }: DataTableProps) {
  const [searchTerms, setSearchTerms] = useState<Record<string, string>>({})
  const [sortColumn, setSortColumn] = useState<string | null>(null)
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const filteredAndSortedData = useMemo(() => {
    let result = [...data]

    // Apply search filters
    result = result.filter(row =>
      columns.every(col => {
        const searchTerm = searchTerms[col.key] || ''
        if (!searchTerm) return true
        const cellValue = String(row[col.key] || '').toLowerCase()
        return cellValue.includes(searchTerm.toLowerCase())
      })
    )

    // Apply sorting
    if (sortColumn) {
      result.sort((a, b) => {
        const aVal = a[sortColumn]
        const bVal = b[sortColumn]
        let comparison = 0

        if (aVal < bVal) comparison = -1
        else if (aVal > bVal) comparison = 1

        return sortOrder === 'asc' ? comparison : -comparison
      })
    }

    return result
  }, [data, searchTerms, sortColumn, sortOrder, columns])

  const handleColumnSort = (columnKey: string) => {
    if (sortColumn === columnKey) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(columnKey)
      setSortOrder('asc')
    }
  }

  const handleSearchChange = (columnKey: string, value: string) => {
    setSearchTerms(prev => ({
      ...prev,
      [columnKey]: value,
    }))
  }

  return (
    <div className="datatable-container">
      {title && <h3 className="datatable-title">{title}</h3>}
      <div className="datatable-info">
        {data.length > 0 && (
          <p className="datatable-stats">
            Showing {filteredAndSortedData.length} of {data.length} rows
          </p>
        )}
      </div>
      <div className="datatable-wrapper">
        <table className="datatable">
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col.key}>
                  <div className="column-header">
                    <button
                      className="sort-button"
                      onClick={() => handleColumnSort(col.key)}
                      title="Click to sort"
                    >
                      {col.label}
                      {sortColumn === col.key && (
                        <span className="sort-icon">
                          {sortOrder === 'asc' ? ' ↑' : ' ↓'}
                        </span>
                      )}
                    </button>
                  </div>
                  <input
                    type="text"
                    className="search-input"
                    placeholder={`Search ${col.label.toLowerCase()}...`}
                    value={searchTerms[col.key] || ''}
                    onChange={e =>
                      handleSearchChange(col.key, e.target.value)
                    }
                  />
                </th>
              ))}
              {/** Actions column header if view enabled */}
              {typeof onView === 'function' && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (typeof onView === 'function' ? 1 : 0)} className="empty-cell">
                  No results found
                </td>
              </tr>
            ) : (
              filteredAndSortedData.map((row, rowIdx) => (
                <tr key={rowIdx}>
                  {columns.map(col => (
                    <td key={`${rowIdx}-${col.key}`}>
                      <span title={String(row[col.key] || '')}>
                        {row[col.key] !== null && row[col.key] !== undefined
                          ? (String(row[col.key]).length > 50 ? String(row[col.key]).substring(0, 50) + '...' : String(row[col.key]))
                          : '-'}
                      </span>
                    </td>
                  ))}
                  {typeof onView === 'function' && (
                    <td>
                      <button
                        className="btn-view"
                        onClick={() => onView(row)}
                        style={{ padding: '0.35rem 0.6rem', borderRadius: 4 }}
                      >
                        View
                      </button>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
