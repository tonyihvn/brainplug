export const API_BASE_URL = '/api'

export const ENDPOINTS = {
  // Chat
  CHAT_MESSAGE: `${API_BASE_URL}/chat/message`,
  CONFIRM_ACTION: `${API_BASE_URL}/chat/confirm-action`,
  CONVERSATIONS: `${API_BASE_URL}/conversations`,
  
  // Settings
  DATABASE_SETTINGS: `${API_BASE_URL}/settings/database`,
  LLM_SETTINGS: `${API_BASE_URL}/settings/llm`,
  RAG_SETTINGS: `${API_BASE_URL}/settings/rag`,
  SYSTEM_SETTINGS: `${API_BASE_URL}/settings/system`,
  API_CONFIGS: `${API_BASE_URL}/settings/api-configs`,
  SCHEDULED_ACTIVITIES: `${API_BASE_URL}/settings/scheduled-activities`,
  
  // Reports
  REPORTS: `${API_BASE_URL}/reports`,
  
  // RAG
  RAG_SCHEMA: `${API_BASE_URL}/rag/schema`,
  BUSINESS_RULES: `${API_BASE_URL}/rag/business-rules`,
  
  // Health
  HEALTH: `${API_BASE_URL}/health`,
}

export const ACTION_TYPES = {
  DATABASE_QUERY: 'database_query',
  RAG_QUERY: 'rag_query',
  EMAIL: 'email',
  URL_READ: 'url_read',
  API_CALL: 'api_call',
  SCHEDULE: 'schedule',
  REPORT: 'report',
}

export const DISPLAY_FORMATS = [
  { value: 'table', label: 'Table' },
  { value: 'chart', label: 'Chart' },
  { value: 'summary', label: 'Summary' },
  { value: 'json', label: 'JSON' },
]
