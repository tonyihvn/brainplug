import Swal from 'sweetalert2'

export interface RAGStatistics {
  status: string
  database_name: string
  tables_scanned: number
  items_created: number
  mapping: string
  storage: string
}

export const showRAGPopulationModal = (stats: RAGStatistics) => {
  const html = `
    <div style="text-align: left; margin: 1rem 0;">
      <div style="padding: 1rem; background: #f0fdf4; border-radius: 0.5rem; margin-bottom: 1rem;">
        <h4 style="margin: 0 0 1rem 0; color: #22c55e; font-size: 1.2rem;">✓ RAG Auto-Generation Complete!</h4>
        
        <div style="display: grid; gap: 1rem;">
          <div style="padding: 1rem; background: white; border-left: 4px solid #3b82f6;">
            <div style="font-size: 0.875rem; color: #6b7280; margin-bottom: 0.25rem;">Database</div>
            <div style="font-size: 1.1rem; font-weight: bold; color: #1f2937;">${stats.database_name}</div>
          </div>
          
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
            <div style="padding: 0.75rem; background: #dbeafe; border-radius: 0.375rem;">
              <div style="font-size: 0.75rem; color: #0369a1; text-transform: uppercase; font-weight: bold;">Tables Scanned</div>
              <div style="font-size: 1.5rem; color: #1e40af;">${stats.tables_scanned}</div>
            </div>
            
            <div style="padding: 0.75rem; background: #dcfce7; border-radius: 0.375rem;">
              <div style="font-size: 0.75rem; color: #166534; text-transform: uppercase; font-weight: bold;">Items Created</div>
              <div style="font-size: 1.5rem; color: #15803d;">${stats.items_created}</div>
            </div>
          </div>
          
          <div style="padding: 1rem; background: #fef3c7; border-radius: 0.375rem;">
            <div style="font-size: 0.875rem; color: #92400e; margin-bottom: 0.5rem;">
              <strong>Mapping:</strong> ${stats.mapping}
            </div>
            <div style="font-size: 0.875rem; color: #92400e;">
              <strong>Storage:</strong> ${stats.storage}
            </div>
          </div>
          
          <div style="padding: 1rem; background: #f3e8ff; border-radius: 0.375rem;">
            <div style="font-size: 0.875rem; color: #3f0f63; line-height: 1.5;">
              ✓ Each table has been auto-documented with:
              <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
                <li>Complete schema definition</li>
                <li>Foreign key relationships</li>
                <li>Sample data examples</li>
                <li>Business rule documentation</li>
              </ul>
            </div>
          </div>
          
          <div style="padding: 1rem; background: #e0e7ff; border-radius: 0.375rem; border-left: 4px solid #6366f1;">
            <div style="font-size: 0.875rem; color: #3730a3;">
              📋 View all generated items in <strong>Settings → RAG</strong> tab to review and edit if needed.
            </div>
          </div>
        </div>
      </div>
    </div>
  `

  return Swal.fire({
    title: 'RAG Schema Generated',
    html,
    icon: 'success',
    confirmButtonText: 'View in RAG Settings',
    cancelButtonText: 'Close',
    showCancelButton: true,
    confirmButtonColor: '#22c55e',
  })
}

export const showRAGErrorModal = (error: string | { error?: string, [key:string]: any }) => {
  const errorMsg = typeof error === 'string' ? error : error?.error || 'Unknown error'
  
  // Determine helpful suggestions based on error message
  let suggestions = [
    'Check your database connection credentials',
    'Ensure the database server is running',
    'Try connecting again',
  ]
  
  if (errorMsg.includes('Cannot connect') || errorMsg.includes('connection')) {
    suggestions = [
      'Verify the database server is running',
      'Check the host and port are correct',
      'Ensure no firewall is blocking the connection',
    ]
  } else if (errorMsg.includes('authentication') || errorMsg.includes('credentials')) {
    suggestions = [
      'Double-check your username and password',
      'Ensure the user has database access',
      'Try with a different database user account',
    ]
  } else if (errorMsg.includes('does not exist') || errorMsg.includes('database')) {
    suggestions = [
      'Verify the database name is correct',
      'Check the database exists on the server',
      'Create the database if it does not exist',
    ]
  }
  
  return Swal.fire({
    title: 'RAG Generation Failed',
    html: `<div style="text-align: left; color: #dc2626;">
      <p style="margin: 1rem 0; line-height: 1.5; font-weight: bold; color: #991b1b;">${errorMsg}</p>
      <div style="padding: 1rem; background: #fee2e2; border-radius: 0.375rem; margin-top: 1rem;">
        <strong>What to do:</strong>
        <ul style="margin: 0.5rem 0 0 0; padding-left: 1.5rem;">
          ${suggestions.map(s => `<li>${s}</li>`).join('')}
        </ul>
      </div>
    </div>`,
    icon: 'error',
    confirmButtonText: 'OK',
    confirmButtonColor: '#dc2626',
  })
}
