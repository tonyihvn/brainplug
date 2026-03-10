import React, { useState, useEffect } from 'react'
import { apiClient } from './services/geminiService'
import Sidebar from './components/Sidebar'
import ChatView from './components/ChatView'
import ActionBox from './components/ActionBox'
import SettingsView from './components/SettingsView'
import RAGManagementView from './components/RAGManagementView'
import SearchModal from './components/SearchModal'
import { FiMenu, FiX } from 'react-icons/fi'
import './App.css'

type ConversationType = any

interface AppState {
  currentView: 'chat' | 'settings' | 'rag' | 'search'
  currentConversationId?: string
  conversations: ConversationType[]
  currentAction?: any
  activeModel?: any
  activeDatabase?: any
  searchResults?: any[]
  searchQuery?: string
}

function App() {
  const [state, setState] = useState<AppState>({
    currentView: 'chat',
    conversations: [],
  })
  const [loading, setLoading] = useState(true)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [searchDiagnostics, setSearchDiagnostics] = useState<any>(null)
  const [modalOpen, setModalOpen] = useState(false)
  const [modalData, setModalData] = useState<any>(null)
  const [headerSearch, setHeaderSearch] = useState<string>('')

  useEffect(() => {
    loadDefaults()

    // Set default sidebar collapse state for mobile
    const handleResize = () => {
      if (window.innerWidth < 768) {
        setSidebarCollapsed(true)
      }
    }

    // Initial check
    handleResize()

    // Listen for resize
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const loadDefaults = async () => {
    try {
      setLoading(true)

      // Load conversations
      const convResponse = await apiClient.getConversations()
      setState(prev => ({
        ...prev,
        conversations: convResponse.data.data || []
      }))

      // Load active LLM model
      const llmResponse = await apiClient.getLLMSettings()
      const models = llmResponse.data?.data || []
      const active = models.find((m: any) => m.is_active)
      if (active) {
        setState(prev => ({ ...prev, activeModel: active }))
        console.log('✓ Active LLM loaded:', active.name)
      }

      // Load active database setting
      const dbResponse = await apiClient.getDatabaseSettings()
      const databases = dbResponse.data?.data || []
      const activeDb = databases.find((db: any) => db.is_active)
      if (activeDb) {
        setState(prev => ({ ...prev, activeDatabase: activeDb }))
        console.log('✓ Active database loaded:', activeDb.name)

        // Populate RAG on first connection
        await populateRAGIfNeeded(activeDb.id)
      }

      // Health check
      await apiClient.healthCheck()

    } catch (error) {
      console.error('Error loading defaults:', error)
    } finally {
      setLoading(false)
    }
  }

  const populateRAGIfNeeded = async (databaseId: string) => {
    try {
      const response = await apiClient.populateRAG(databaseId)
      console.log('✓ RAG populated:', response.data)
    } catch (error) {
      console.error('Error populating RAG:', error)
    }
  }

  const handleLoadConversations = async () => {
    try {
      const response = await apiClient.getConversations()
      setState(prev => ({
        ...prev,
        conversations: response.data.data || []
      }))
    } catch (error) {
      console.error('Error loading conversations:', error)
    }
  }

  const handleNewConversation = () => {
    setState(prev => ({
      ...prev,
      currentConversationId: undefined,
      currentAction: undefined
    }))
  }

  const handleSelectConversation = (id: string) => {
    setState(prev => ({
      ...prev,
      currentConversationId: id
    }))
  }

  const handleDeleteConversation = async (id: string) => {
    try {
      await apiClient.deleteConversation(id)
      await handleLoadConversations()
      if (state.currentConversationId === id) {
        handleNewConversation()
      }
    } catch (error) {
      console.error('Error deleting conversation:', error)
    }
  }

  const handleClearAllConversations = async () => {
    try {
      // Delete all conversations
      const conversationIds = state.conversations.map(c => c.id)
      for (const id of conversationIds) {
        await apiClient.deleteConversation(id)
      }
      await handleLoadConversations()
      handleNewConversation()
      console.log('✓ All conversations cleared')
    } catch (error) {
      console.error('Error clearing conversations:', error)
    }
  }

  const handleViewSettings = () => {
    setState(prev => ({
      ...prev,
      currentView: 'settings'
    }))
  }

  const handleViewChat = () => {
    setState(prev => ({
      ...prev,
      currentView: 'chat'
    }))
  }

  const handleViewRAG = () => {
    setState(prev => ({
      ...prev,
      currentView: 'rag'
    }))
  }

  const handleSearch = async (q: string) => {
    try {
      setSearchQuery(q)
      const resp = await apiClient.searchDatabases(q)
      const data = resp.data?.results || []
      setSearchResults(data)
      setSearchDiagnostics(resp.data?.diagnostics || null)
      setState(prev => ({ ...prev, currentView: 'search' }))
    } catch (error) {
      console.error('Search error:', error)
    }
  }

  const handleActionSuggested = (action: any) => {
    setState(prev => ({
      ...prev,
      currentAction: action
    }))
  }

  const handleActionConfirmed = async (action: any) => {
    try {
      const result = await apiClient.confirmAction(action, state.currentConversationId)
      setState(prev => ({
        ...prev,
        currentAction: { ...action, result: result.data.result }
      }))
      await handleLoadConversations()
    } catch (error) {
      console.error('Error confirming action:', error)
    }
  }

  const [actionBoxHeight, setActionBoxHeight] = React.useState(250)
  const [isDraggingActionDivider, setIsDraggingActionDivider] = React.useState(false)
  const [actionBoxPoppedOut, setActionBoxPoppedOut] = React.useState(false)
  const actionDragStartY = React.useRef(0)
  const actionStartHeight = React.useRef(0)

  const handleActionDividerMouseDown = (e: React.MouseEvent) => {
    setIsDraggingActionDivider(true)
    actionDragStartY.current = e.clientY
    actionStartHeight.current = actionBoxHeight
  }

  const toggleActionBoxPopout = () => {
    setActionBoxPoppedOut(prev => !prev)
  }

  React.useEffect(() => {
    if (!isDraggingActionDivider) return

    const handleMouseMove = (e: MouseEvent) => {
      // Calculate the difference: negative when dragging up, positive when dragging down
      const diff = actionDragStartY.current - e.clientY
      // When dragging down, we want to reduce height (negative diff increases height, so we negate)
      // When dragging up, we want to increase height (positive diff, negate to make it decrease)
      const newHeight = Math.max(80, Math.min(actionStartHeight.current + diff, window.innerHeight - 200))
      setActionBoxHeight(newHeight)
    }

    const handleMouseUp = () => {
      setIsDraggingActionDivider(false)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDraggingActionDivider])

  if (loading) {
    return <div className="app-loading">Loading configuration...</div>
  }

  return (
    <div className="app">
      {sidebarCollapsed && (
        <button
          className="btn-sidebar-toggle"
          onClick={() => setSidebarCollapsed(false)}
          title={'Show sidebar'}
          style={{ left: '1rem', right: 'auto' }}
        >
          <FiMenu size={20} />
        </button>
      )}

      {/* Search moved to sidebar for consistent UX */}

      {!sidebarCollapsed && (
        <Sidebar
          conversations={state.conversations}
          currentConversationId={state.currentConversationId}
          onNewConversation={handleNewConversation}
          onSelectConversation={handleSelectConversation}
          onDeleteConversation={handleDeleteConversation}
          onClearAll={handleClearAllConversations}
          onViewSettings={handleViewSettings}
          onViewChat={handleViewChat}
          onViewRAG={handleViewRAG}
          currentView={state.currentView}
          onToggleCollapse={() => setSidebarCollapsed(true)}
          onSearch={handleSearch}
          onMobileSelect={() => setSidebarCollapsed(true)}
        />
      )}

      <div className="app-main">

        {state.currentView === 'chat' ? (
          <>
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
              <ChatView
                conversationId={state.currentConversationId}
                onActionSuggested={handleActionSuggested}
                actionResult={state.currentAction?.result}
              />
              <div
                className={`resizer-divider ${isDraggingActionDivider ? 'dragging' : ''}`}
                onMouseDown={handleActionDividerMouseDown}
                title="Drag to resize action panel"
              />
              <div style={{ height: `${actionBoxHeight}px`, overflow: 'hidden', flexShrink: 0 }}>
                {!actionBoxPoppedOut && (
                  <ActionBox
                    action={state.currentAction}
                    onConfirm={handleActionConfirmed}
                    onTogglePopout={toggleActionBoxPopout}
                  />
                )}
              </div>
            </div>
            {actionBoxPoppedOut && (
              <div className="actionbox-modal-backdrop" style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1200 }}>
                <div style={{ width: '80%', maxWidth: 1000, maxHeight: '80%', overflow: 'auto', background: 'white', borderRadius: 8, boxShadow: '0 10px 40px rgba(0,0,0,0.3)', padding: 12 }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button className="btn-secondary" onClick={toggleActionBoxPopout}>Close</button>
                  </div>
                  <ActionBox action={state.currentAction} onConfirm={handleActionConfirmed} onTogglePopout={toggleActionBoxPopout} />
                </div>
              </div>
            )}
          </>
        ) : state.currentView === 'settings' ? (
          <SettingsView onBack={handleViewChat} />
        ) : state.currentView === 'search' ? (
          <div style={{ padding: '1rem', height: '100%', overflow: 'auto' }}>
            <h2>Search Results for "{searchQuery}"</h2>
            <div style={{ marginTop: '1rem' }}>
              {searchResults.length === 0 ? (
                <div>
                  <div>No results</div>
                  {searchDiagnostics ? (
                    <div style={{ marginTop: 12, padding: 12, background: '#fff7ed', border: '1px solid #fce8c3', borderRadius: 6 }}>
                      <div style={{ fontWeight: 600, marginBottom: 6 }}>Diagnostics</div>
                      <div>Databases checked: {searchDiagnostics.databases_checked}</div>
                      {Array.isArray(searchDiagnostics.db_diagnostics) && searchDiagnostics.db_diagnostics.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                          {searchDiagnostics.db_diagnostics.map((d: any, i: number) => (
                            <div key={i} style={{ marginBottom: 6 }}>
                              <div style={{ fontWeight: 600 }}>{d.database_name || d.database_id}</div>
                              <div>Tables checked: {d.tables_checked}</div>
                              {d.errors && d.errors.length > 0 && (
                                <div style={{ marginTop: 4 }}>
                                  <div style={{ fontWeight: 600 }}>Errors:</div>
                                  <ul style={{ margin: '4px 0 0 18px' }}>
                                    {d.errors.map((e: string, ei: number) => <li key={ei} style={{ color: '#c05621' }}>{e}</li>)}
                                  </ul>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="search-results">
                  {searchResults.map((r, idx) => (
                    <div key={idx} className="search-result-item" style={{ borderBottom: '1px solid #eee', padding: '0.5rem 0' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div>
                          <div style={{ fontWeight: 600 }}>{r.database_name}{r.table ? ` · ${r.table}` : ''}</div>
                          <div style={{ color: '#666', fontSize: '0.9rem' }}>Matched: {Array.isArray(r.matched_columns) ? r.matched_columns.join(', ') : ''}</div>
                        </div>
                        <div>
                          <button onClick={() => { setModalData(r); setModalOpen(true) }} className="btn-secondary">View</button>
                        </div>
                      </div>
                      <div style={{ marginTop: '0.5rem' }}>
                        {/* Show a compact preview: one representative value only. Rest available in modal via View button. */}
                        {r && r.row && typeof r.row === 'object' ? (
                          (() => {
                            // Prefer showing matched column(s) first
                            const matched = Array.isArray(r.matched_columns) && r.matched_columns.length > 0 ? r.matched_columns : []
                            let previewKey = ''
                            if (matched.length > 0) previewKey = matched[0]
                            else {
                              // fallback: first non-empty string field
                              const keys = Object.keys(r.row)
                              for (const k of keys) {
                                const v = r.row[k]
                                if (v && typeof v === 'string' && v.trim().length > 0) {
                                  previewKey = k
                                  break
                                }
                              }
                              if (!previewKey) previewKey = Object.keys(r.row)[0] || ''
                            }

                            const v = previewKey ? r.row[previewKey] : ''
                            const display = v && typeof v === 'object' ? JSON.stringify(v) : String(v === null || v === undefined ? '' : v)

                            return (
                              <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
                                <div style={{ flex: 1, background: '#f6f8fa', padding: '0.5rem', borderRadius: 6, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>
                                  <div style={{ fontSize: '0.85rem', color: '#444', fontWeight: 600 }}>{previewKey}</div>
                                  <div style={{ marginTop: 4, color: '#333' }}>{display}</div>
                                </div>
                                <div style={{ minWidth: 80 }}>
                                  <button onClick={() => { setModalData(r); setModalOpen(true) }} className="btn-secondary">View</button>
                                </div>
                              </div>
                            )
                          })()
                        ) : (
                          <pre style={{ maxHeight: 120, overflow: 'auto', background: '#f6f8fa', padding: '0.5rem' }}>{JSON.stringify(r.row, null, 2)}</pre>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <SearchModal visible={modalOpen} onClose={() => setModalOpen(false)} title={`Result from ${modalData?.database_name || ''}`} data={modalData} />
          </div>
        ) : (
          <RAGManagementView
            onBack={handleViewChat}
            databaseId={state.activeDatabase?.id}
          />
        )}
      </div>
    </div>
  )
}

export default App
