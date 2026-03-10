import axios, { AxiosInstance } from 'axios'
import { API_BASE_URL, ENDPOINTS } from '../constants'

class APIClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // Chat endpoints
  async sendMessage(message: string, conversationId?: string) {
    return this.client.post('/chat/message', {
      message,
      conversation_id: conversationId,
    })
  }

  async confirmAction(action: any, conversationId?: string) {
    return this.client.post('/chat/confirm-action', {
      action,
      conversation_id: conversationId,
    })
  }

  async getConversations() {
    return this.client.get('/conversations')
  }

  async getConversation(id: string) {
    return this.client.get(`/conversations/${id}`)
  }

  async deleteConversation(id: string) {
    return this.client.delete(`/conversations/${id}`)
  }

  // Settings endpoints
  async getDatabaseSettings() {
    return this.client.get('/settings/database')
  }

  async updateDatabaseSettings(settings: any) {
    return this.client.post('/settings/database', settings)
  }

  async deleteDatabaseSetting(id: string) {
    // DELETE /settings/database/<id>
    return this.client.delete(`/settings/database/${id}`)
  }

  async discoverTables(databaseId: string) {
    return this.client.post('/settings/database/discover-tables', { database_id: databaseId })
  }

  async getTableRelationships(databaseId: string, tableName: string) {
    return this.client.post('/settings/database/table-relationships', { database_id: databaseId, table_name: tableName })
  }

  async discoverDatabaseTables(databaseId: string) {
    return this.client.post('/settings/database/discover-tables', { database_id: databaseId })
  }

  async startIngestionJob(databaseId: string) {
    return this.client.post('/settings/database/start-ingestion', { database_id: databaseId })
  }

  async getIngestionJobStatus(jobId: string) {
    return this.client.get(`/settings/database/ingestion-status/${jobId}`)
  }

  // Data Ingestion Endpoints
  async configureTableIngestion(config: any) {
    return this.client.post('/rag/ingest/config', config)
  }

  async startTableIngestion(ingestionData: any) {
    return this.client.post('/rag/ingest/start', ingestionData)
  }

  async deleteIngestedData(databaseId: string) {
    return this.client.delete(`/rag/ingest/delete/${databaseId}`)
  }

  async triggerManualIngestion(databaseId: string) {
    return this.client.post('/rag/ingest/manual', { database_id: databaseId })
  }

  async getIngestionStatus(databaseId: string) {
    return this.client.post('/rag/ingest/status', { database_id: databaseId })
  }

  async getReports() {
    return this.client.get('/reports')
  }

  async deleteReport(id: string) {
    return this.client.delete(`/reports/${id}`)
  }
  
  async post(url: string, data: any) {
    return this.client.post(url, data)
  }

  async delete(url: string, data?: any) {
    return this.client.delete(url, data ? { data } : undefined)
  }

  async getLLMSettings() {
    return this.client.get('/settings/llm')
  }

  async updateLLMSettings(settings: any) {
    return this.client.post('/settings/llm', settings)
  }

  async deleteLLMModel(id: string) {
    return this.client.delete(`/settings/llm/${id}`)
  }

  async probeOllama(host?: string) {
    const params = host ? { host } : {}
    return this.client.get('/settings/llm/ollama/models', { params })
  }

  async getRAGSettings() {
    return this.client.get('/settings/rag')
  }

  async updateRAGSettings(settings: any) {
    return this.client.post('/settings/rag', settings)
  }

  async getSystemSettings() {
    return this.client.get('/settings/system')
  }

  async updateSystemSettings(settings: any) {
    return this.client.post('/settings/system', settings)
  }

  async getAPIConfigs() {
    return this.client.get('/settings/api-configs')
  }

  async createAPIConfig(config: any) {
    return this.client.post('/settings/api-configs', config)
  }

  async updateAPIConfig(id: string, config: any) {
    return this.client.put('/settings/api-configs', { ...config, id })
  }

  async deleteAPIConfig(id: string) {
    return this.client.delete('/settings/api-configs', { data: { id } })
  }

  async getScheduledActivities() {
    return this.client.get('/settings/scheduled-activities')
  }

  async createScheduledActivity(activity: any) {
    return this.client.post('/settings/scheduled-activities', activity)
  }

  async updateScheduledActivity(id: string, activity: any) {
    return this.client.put(`/settings/scheduled-activities/${id}`, activity)
  }

  async deleteScheduledActivity(id: string) {
    return this.client.delete(`/settings/scheduled-activities/${id}`)
  }

  // RAG endpoints
  async populateRAG(databaseId: string) {
    return this.client.post('/rag/populate', { database_id: databaseId })
  }

  async getRAGItems(category?: string) {
    const params = category ? `?category=${category}` : ''
    return this.client.get(`/rag/items${params}`)
  }

  async createRAGItem(item: any) {
    return this.client.post('/rag/items', item)
  }

  async updateRAGItem(itemId: string, item: any) {
    return this.client.put(`/rag/items/${itemId}`, item)
  }

  async deleteRAGItem(itemId: string) {
    return this.client.delete(`/rag/items/${itemId}`)
  }

  async getRAGSchema() {
    return this.client.get('/rag/schema')
  }

  // Business Rules endpoints
  async getBusinessRules() {
    return this.client.get('/rag/business-rules')
  }

  async createBusinessRule(rule: any) {
    return this.client.post('/rag/business-rules', rule)
  }

  async updateBusinessRule(id: string, rule: any) {
    return this.client.put(`/rag/business-rules/${id}`, rule)
  }

  async deleteBusinessRule(id: string) {
    return this.client.delete(`/rag/business-rules/${id}`)
  }

  // DBMS Explorer endpoints
  async getDBMSDatabases() {
    return this.client.get('/dbms/databases')
  }

  async getDBMSTables(databaseId: string) {
    return this.client.get(`/dbms/tables/${databaseId}`)
  }

  async getTableData(databaseId: string, tableName: string, page: number = 1, limit: number = 20) {
    return this.client.get(`/dbms/table-data/${databaseId}/${tableName}?page=${page}&limit=${limit}`)
  }

  async getTableSchema(databaseId: string, tableName: string) {
    return this.client.get(`/dbms/table-schema/${databaseId}/${tableName}`)
  }

  // Data Sources endpoints
  async getDataSources() {
    return this.client.get('/data-sources')
  }

  async searchDatabases(query: string) {
    const params = { q: query }
    return this.client.get('/search/databases', { params })
  }

  async createDataSource(source: any) {
    return this.client.post('/data-sources', source)
  }

  // APIs endpoints
  async getAPIConfigsList() {
    return this.client.get('/api-configs-list')
  }

  async createAPIConfigItem(config: any) {
    return this.client.post('/api-configs-list', config)
  }

  // Health check
  async healthCheck() {
    return this.client.get('/health')
  }
}

export const apiClient = new APIClient()
