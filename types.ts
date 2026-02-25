export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: Message[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  action_data?: ActionData;
  action_executed: boolean;
  action_result?: any;
  created_at: string;
}

export interface ActionData {
  type: string;
  sql_query?: string;
  parameters?: string;
  confidence?: string;
  data?: any;
}

export interface DatabaseSetting {
  id: string;
  name: string;
  db_type: string;
  host?: string;
  port?: number;
  database: string;
  username?: string;
  is_active: boolean;
  created_at: string;
}

export interface LLMModel {
  id: string;
  name: string;
  model_type: string;
  model_id: string;
  api_key?: string;
  api_endpoint?: string;
  priority: number;
  is_active: boolean;
  config?: any;
  created_at: string;
}

export interface BusinessRule {
  id: string;
  name: string;
  description?: string;
  rule_type: string;
  content: string;
  category?: string;
  is_active: boolean;
  created_at: string;
}

export interface ScheduledActivity {
  id: string;
  title: string;
  action_type: string;
  action_data: ActionData;
  scheduled_for: string;
  recurrence?: string;
  is_active: boolean;
  last_executed?: string;
  next_execution?: string;
  created_at: string;
}

export interface Report {
  id: string;
  title: string;
  description?: string;
  report_type: string;
  data: any;
  action_ids?: string[];
  created_at: string;
}

export interface ApiConfig {
  id: string;
  name: string;
  api_type: string;
  endpoint: string;
  method: string;
  headers?: any;
  auth_type?: string;
  params_template?: any;
  created_at: string;
}
