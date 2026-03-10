import React, { useState } from 'react'
import { Conversation } from '../types'
import { FiPlus, FiSettings, FiTrash2 } from 'react-icons/fi'
import { FiSearch, FiChevronLeft } from 'react-icons/fi'

interface SidebarProps {
  conversations: Conversation[]
  currentConversationId?: string
  onNewConversation: () => void
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => void
  onClearAll: () => void
  onViewSettings: () => void
  onViewRAG: () => void
  onViewChat?: () => void
  currentView: 'chat' | 'settings' | 'rag' | 'search'
  onToggleCollapse?: () => void
  onSearch?: (q: string) => void
  onMobileSelect?: () => void
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onNewConversation,
  onSelectConversation,
  onDeleteConversation,
  onClearAll,
  onViewSettings,
  onViewRAG,
  onViewChat,
  currentView,
  onToggleCollapse,
  onSearch,
  onMobileSelect,
}: SidebarProps) {
  const [query, setQuery] = useState('')
  
  const handleNewConversation = () => {
    onNewConversation()
    if (onViewChat) onViewChat()
  }
  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    const { showConfirm } = await import('./swal')
    const ok = await showConfirm('Delete this conversation?', 'Are you sure you want to delete this conversation?')
    if (ok) onDeleteConversation(id)
  }

  const handleClearAll = async () => {
    const { showConfirm } = await import('./swal')
    const ok = await showConfirm('Delete ALL conversations?', 'This cannot be undone. Are you sure?')
    if (ok) onClearAll()
  }

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (onSearch) onSearch(query)
  }

  return (
    <div className="app-sidebar">
      <div className="app-sidebar-header" style={{ position: 'relative' }}>
        <h1>Gemini MCP</h1>
        <p>AI Assistant & RAG System</p>
        <button
          onClick={onToggleCollapse}
          title="Collapse sidebar"
          style={{ position: 'absolute', right: 8, top: 8, border: 'none', background: 'transparent', cursor: 'pointer' }}
        >
          <FiChevronLeft />
        </button>
      </div>

      {/* Database search inside the sidebar (moved from header) */}
      <div style={{ padding: '0.75rem 1rem' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', gap: 8 }}>
          <input
            aria-label="Search databases"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search databases..."
            style={{ flex: 1, padding: '0.45rem 0.6rem', borderRadius: 6, border: '1px solid #e2e8f0' }}
          />
          <button type="submit" className="btn-primary">Search</button>
        </form>
      </div>

      <div className="app-sidebar-content">
        {conversations.length === 0 ? (
          <div style={{ padding: '1rem', textAlign: 'center', color: '#cbd5e0', fontSize: '0.875rem' }}>
            No conversations yet
          </div>
        ) : (
          (
            <>
                  <div style={{ padding: '0 1rem 0.5rem 1rem' }}>
                    <div style={{ color: '#a0aec0', fontSize: '0.85rem', marginBottom: 6 }}>History</div>
                  </div>

                  {conversations.map(conv => (
                <div
                  key={conv.id}
                  className={`conversation-item ${currentConversationId === conv.id && currentView === 'chat' ? 'active' : ''}`}
                  onClick={() => { onSelectConversation(conv.id); if (onMobileSelect && window.innerWidth < 768) onMobileSelect() }}
                >
                  <span>{conv.title}</span>
                  <button
                    className="conversation-item-delete"
                    onClick={(e) => handleDelete(e, conv.id)}
                    title="Delete conversation"
                  >
                    ✕
                  </button>
                </div>
              ))}
            </>
          )
        )}
      </div>

      <div className="app-sidebar-actions">
        {conversations.length > 0 && (
          <button 
            className="btn-clear-all"
            onClick={handleClearAll}
            title="Delete all conversations"
          >
            <FiTrash2 style={{ marginRight: '0.5rem' }} />
            Clear All
          </button>
        )}
      </div>

      <div className="app-sidebar-footer">
        <div style={{ display: 'flex', gap: '0.5rem', width: '100%' }}>
          <button className="btn-primary" onClick={handleNewConversation} style={{ flex: 1 }}>
            <FiPlus style={{ marginRight: '0.5rem' }} />
            New Chat
          </button>
          <button className="btn-secondary" onClick={onViewSettings} title="Settings">
            <FiSettings />
          </button>
        </div>
      </div>
    </div>
  )
}
