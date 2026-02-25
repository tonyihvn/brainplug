import React, { useState, useEffect, useRef } from 'react'
import { Message as MessageType } from '../types'
import { apiClient } from '../services/geminiService'
import DataTable from './DataTable'
import { showAlert } from './swal'
import { FiSend, FiMaximize2, FiX, FiChevronDown, FiChevronUp } from 'react-icons/fi'
import './ChatView.css'

interface ChatViewProps {
  conversationId?: string
  onActionSuggested: (action: any) => void
  actionResult?: any
}

export default function ChatView({ conversationId, onActionSuggested, actionResult }: ChatViewProps) {
  const [messages, setMessages] = useState<MessageType[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isResultExpanded, setIsResultExpanded] = useState(false)
  const [resultDisplayType, setResultDisplayType] = useState<'datatable' | 'chart' | 'summary'>('summary')
  const [sidebarWidth, setSidebarWidth] = useState(350)
  const [isDragging, setIsDragging] = useState(false)
  const [expandedSummaryLevel, setExpandedSummaryLevel] = useState<1 | 2 | 3>(1)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const dragStartX = useRef(0)
  const startWidth = useRef(0)

  useEffect(() => {
    // Load conversation messages if ID provided
    if (conversationId) {
      loadConversation()
    } else {
      setMessages([])
    }
  }, [conversationId])

  useEffect(() => {
    // When actionResult changes, use its display_format if available
    if (actionResult && actionResult.display_format) {
      setResultDisplayType(actionResult.display_format)
    }
  }, [actionResult])

  useEffect(() => {
    // Scroll to bottom when messages change
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true)
    dragStartX.current = e.clientX
    startWidth.current = sidebarWidth
  }

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      const diff = dragStartX.current - e.clientX
      const newWidth = Math.max(250, Math.min(startWidth.current + diff, window.innerWidth - 100))
      setSidebarWidth(newWidth)
    }

    const handleMouseUp = () => {
      setIsDragging(false)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging])

  const loadConversation = async () => {
    try {
      if (!conversationId) return
      const response = await apiClient.getConversation(conversationId)
      setMessages(response.data.data.messages || [])
    } catch (error) {
      console.error('Error loading conversation:', error)
    }
  }

  const handleSendMessage = async () => {
    if (!input.trim()) return

    const userMessage: MessageType = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input,
      action_executed: false,
      created_at: new Date().toISOString(),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await apiClient.sendMessage(input, conversationId)
      const { explanation, action, conversation_id } = response.data.data

      const assistantMessage: MessageType = {
        id: `msg_${Date.now()}_ai`,
        role: 'assistant',
        content: explanation,
        action_data: action,
        action_executed: false,
        created_at: new Date().toISOString(),
      }

      setMessages(prev => [...prev, assistantMessage])
      onActionSuggested(action)

      // Update conversation ID if it's a new one
      if (!conversationId && conversation_id) {
        window.history.replaceState(null, '', `?conv=${conversation_id}`)
      }
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage: MessageType = {
        id: `msg_${Date.now()}_err`,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request. Please try again.',
        action_executed: false,
        created_at: new Date().toISOString(),
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  const renderResultPanel = () => {
    if (!actionResult) {
      return (
        <div className="result-panel-empty">
          <div className="result-empty-icon">📊</div>
          <div className="result-empty-text">No results yet</div>
          <p>Execute an action to see results here</p>
        </div>
      )
    }

    const { row_count, rows, summary_levels, columns, column_count } = actionResult

    // Show 3-level summaries
    if (summary_levels) {
      return (
        <div className="result-panel">
          <div className="result-controls">
            <h3 className="result-title">
              {row_count ? `${row_count} Results` : 'Results'}
              {columns && ` • ${column_count} Columns`}
            </h3>
            <div className="result-format-selector">
              <button
                className={`format-btn ${resultDisplayType === 'summary' ? 'active' : ''}`}
                onClick={() => setResultDisplayType('summary')}
                title="Show summaries"
              >
                📝
              </button>
              {rows && rows.length > 0 && (
                <button
                  className={`format-btn ${resultDisplayType === 'datatable' ? 'active' : ''}`}
                  onClick={() => setResultDisplayType('datatable')}
                  title="Display as table"
                >
                  📊
                </button>
              )}
            </div>
          </div>

          {resultDisplayType === 'summary' ? (
            <div className="result-summaries">
              {/* Level 1: Overview */}
              <div className="summary-level">
                <button
                  className="summary-level-header"
                  onClick={() => setExpandedSummaryLevel(expandedSummaryLevel === 1 ? 2 : 1)}
                >
                  <span className="summary-level-title">
                    {expandedSummaryLevel === 1 ? <FiChevronUp /> : <FiChevronDown />}
                    <strong>Level 1: Overview</strong>
                  </span>
                </button>
                {expandedSummaryLevel === 1 && (
                  <div className="summary-level-content level-1">
                    <p>{summary_levels.level_1}</p>
                  </div>
                )}
              </div>

              {/* Level 2: Column Analysis */}
              <div className="summary-level">
                <button
                  className="summary-level-header"
                  onClick={() => setExpandedSummaryLevel(expandedSummaryLevel === 2 ? 3 : 2)}
                >
                  <span className="summary-level-title">
                    {expandedSummaryLevel === 2 ? <FiChevronUp /> : <FiChevronDown />}
                    <strong>Level 2: Column Details</strong>
                  </span>
                </button>
                {expandedSummaryLevel === 2 && (
                  <div className="summary-level-content level-2">
                    <p>{summary_levels.level_2}</p>
                  </div>
                )}
              </div>

              {/* Level 3: Insights */}
              <div className="summary-level">
                <button
                  className="summary-level-header"
                  onClick={() => setExpandedSummaryLevel(expandedSummaryLevel === 3 ? 1 : 3)}
                >
                  <span className="summary-level-title">
                    {expandedSummaryLevel === 3 ? <FiChevronUp /> : <FiChevronDown />}
                    <strong>Level 3: Data Insights</strong>
                  </span>
                </button>
                {expandedSummaryLevel === 3 && (
                  <div className="summary-level-content level-3">
                    <p>{summary_levels.level_3}</p>
                  </div>
                )}
              </div>
            </div>
          ) : resultDisplayType === 'datatable' && rows && rows.length > 0 ? (
            <DataTable
              columns={Object.keys(rows[0]).map(key => ({
                key,
                label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
              }))}
              data={rows}
              onView={(row) => {
                // Pick a representative text field from the row
                const keys = Object.keys(row || {})
                let chosen = ''
                for (const k of keys) {
                  const v = row[k]
                  if (v && typeof v === 'string' && v.trim().length > 0) {
                    chosen = v
                    break
                  }
                }
                if (!chosen && keys.length > 0) chosen = String(row[keys[0]] || '')
                showAlert('Row detail', chosen || '(no text fields available)', 'info')
              }}
            />
          ) : (
            <pre className="result-json">
              {JSON.stringify(rows || actionResult, null, 2)}
            </pre>
          )}
        </div>
      )
    }

    // Fallback for non-formatted results
    if (rows && Array.isArray(rows) && rows.length > 0) {
      const columns = Object.keys(rows[0]).map(key => ({
        key,
        label: key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' '),
      }))

      return (
        <div className="result-panel">
          <div className="result-controls">
            <h3 className="result-title">{rows.length} Results</h3>
            <div className="result-format-selector">
              <button
                className={`format-btn ${resultDisplayType === 'datatable' ? 'active' : ''}`}
                onClick={() => setResultDisplayType('datatable')}
                title="Display as table"
              >
                📊
              </button>
            </div>
          </div>

          <DataTable
            columns={columns}
            data={rows}
            onView={(row) => {
              const keys = Object.keys(row || {})
              let chosen = ''
              for (const k of keys) {
                const v = row[k]
                if (v && typeof v === 'string' && v.trim().length > 0) {
                  chosen = v
                  break
                }
              }
              if (!chosen && keys.length > 0) chosen = String(row[keys[0]] || '')
              showAlert('Row detail', chosen || '(no text fields available)', 'info')
            }}
          />
          {/* Add view handler for fallback table rendering */}
        </div>
      )
    }

    // Generic result display - show as summary if available
    if (actionResult.summary_levels) {
      return (
        <div className="result-panel">
          <h3 className="result-title">Result Summary</h3>
          <div className="result-summary">
            <p>{actionResult.summary_levels.level_1}</p>
          </div>
        </div>
      )
    }

    // Fallback: show as summary text
    return (
      <div className="result-panel">
        <h3 className="result-title">Action Result</h3>
        <div className="result-summary">
          <p>{JSON.stringify(actionResult, null, 2).substring(0, 500)}...</p>
        </div>
      </div>
    )
  }

  return (
    <div className={`chat-view-layout ${isResultExpanded ? 'result-fullscreen' : ''}`}>
      {/* Main Chat Area */}
      {!isResultExpanded && (
        <div className="chat-container">
          <div className="messages-container">
            {messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">💬</div>
                <div className="empty-state-text">No messages yet</div>
                <p>Start a conversation with the AI assistant</p>
              </div>
            ) : (
              messages.map(message => (
                <div key={message.id} className={`message ${message.role}`}>
                  <div className="message-content">
                    {message.content}
                    {message.action_data && (
                      <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', opacity: 0.8 }}>
                        <strong>Action: </strong> {message.action_data.type}
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            {loading && (
              <div className="message assistant">
                <div className="message-content">
                  <span>Thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-section">
            <div className="chat-input-group">
              <input
                type="text"
                placeholder="Ask me anything... e.g., 'Get the last 50 records from inventories table'"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleSendMessage()}
                disabled={loading}
              />
            </div>
            <div className="chat-buttons">
              <button
                className="btn-send"
                onClick={handleSendMessage}
                disabled={loading || !input.trim()}
              >
                <FiSend style={{ marginRight: '0.5rem' }} />
                Send
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Result Sidebar with Draggable Divider */}
      {isResultExpanded ? (
        <div className="result-fullscreen-container">
          <div className="result-fullscreen-header">
            <h2>Query Results</h2>
            <button
              className="btn-close-fullscreen"
              onClick={() => setIsResultExpanded(false)}
              title="Close fullscreen"
            >
              <FiX />
            </button>
          </div>
          {renderResultPanel()}
        </div>
      ) : (
        <>
          <div
            className={`result-sidebar-divider ${isDragging ? 'dragging' : ''}`}
            onMouseDown={handleMouseDown}
            style={{ cursor: isDragging ? 'col-resize' : 'col-resize' }}
          />
          <div className="result-sidebar" style={{ width: `${sidebarWidth}px` }}>
            <div className="result-sidebar-header">
              <h3>Results</h3>
              {actionResult && (
                <button
                  className="btn-expand"
                  onClick={() => setIsResultExpanded(true)}
                  title="Expand to fullscreen"
                >
                  <FiMaximize2 size={18} />
                </button>
              )}
            </div>
            {renderResultPanel()}
          </div>
        </>
      )}
    </div>
  )
}
