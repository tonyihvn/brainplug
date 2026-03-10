# KEY_DEVELOPER_REFERENCE_GUIDE
## Brainplug: Source Code Developer Reference

**Version**: 2.0
**Last Updated**: February 2026
**Audience**: Backend Developers, Frontend Developers, DevOps Engineers, Contributors

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Tech Stack Overview](#tech-stack-overview)
3. [Backend Architecture](#backend-architecture)
4. [Frontend Architecture](#frontend-architecture)
5. [Key Files & Directories](#key-files--directories)
6. [Core Modules Reference](#core-modules-reference)
7. [API Endpoints](#api-endpoints)
8. [Database Schemas](#database-schemas)
9. [RAG System](#rag-system)
10. [LLM Integration](#llm-integration)
11. [Development Setup](#development-setup)
12. [Building & Deployment](#building--deployment)
13. [Testing](#testing)
14. [Contributing](#contributing)
15. [Troubleshooting](#troubleshooting)

---

## Project Structure

```
brainplug/
├── backend/                          Python Flask backend
│   ├── __init__.py
│   ├── models/                       SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── conversation.py           Conversation & Message models
│   │   ├── action.py                 Action/Query models
│   │   └── user.py                   (Future) User model
│   ├── services/                     Business logic layer
│   │   ├── settings_service.py       ✨ Settings & RAG management
│   │   ├── llm_service.py            ✨ LLM processing & validation
│   │   ├── conversation_service.py   Conversation management
│   │   └── action_service.py         Action execution
│   ├── utils/                        Utilities & helpers
│   │   ├── __init__.py
│   │   ├── database.py               ✨ Database connector & schema extraction
│   │   ├── rag_database.py           ✨ RAG vector store operations
│   │   ├── logger.py                 Structured logging
│   │   ├── conversation_memory.py    ✨ Conversation context tracking
│   │   └── config.py                 Configuration loader
│   └── routes/
│       ├── __init__.py
│       ├── chat.py                   Chat endpoints
│       ├── settings.py               Settings endpoints
│       ├── actions.py                Action execution endpoints
│       └── conversations.py          Conversation management
│
├── components/                       React/TypeScript components
│   ├── ActionBox.tsx                 ✨ SQL editor & action executor
│   ├── ChatView.tsx                  Main chat interface
│   ├── SettingsView.tsx              Settings manager
│   ├── RAGManagementView.tsx          Schema browser
│   ├── DBMSExplorer.tsx              Database explorer
│   ├── DataTable.tsx                 Result table display
│   ├── SearchModal.tsx               Search interface
│   ├── Sidebar.tsx                   Navigation sidebar
│   └── settings/                     Settings sub-components
│       └── (individual setting forms)
│
├── services/                         Frontend services (optional)
│   └── geminiService.ts              (Legacy - consolidated into LLM)
│
├── scripts/                          Utility scripts
│   ├── cleanup_rag_rules.py
│   ├── export_settings_to_env.py
│   ├── fix_rag_llm_settings.py
│   ├── test_db_full_flow.py
│   └── test_rag_integration.py
│
├── instance/                         Runtime data (NOT in git)
│   ├── rag_db/                       RAG database JSON files
│   │   ├── schemas.json
│   │   ├── rules.json
│   │   └── settings.json
│   └── store/                        Conversation storage
│
├── tests/                            Test files
│   ├── test_rag_consolidation_llm_validation.py
│   ├── test_comprehensive_endpoints.py
│   └── test_*.py                     Various test suites
│
├── docs/                             Documentation
│   ├── KEY_APP_FEATURES_AND_ARCHITECTURE.md
│   ├── KEY_SOP_DOCUMENT_USER_GUIDE.md
│   ├── KEY_DEVELOPER_REFERENCE_GUIDE.md
│   ├── RAG_*.md                      RAG system docs
│   └── AUTO_RAG_*.md                 Auto-RAG docs
│
├── app.py                            ✨ Flask application entry point
├── requirements.txt                  Python dependencies
├── .env.example                      Environment variables template
├── .gitignore                        Git ignore rules
│
├── index.tsx                         React entry point
├── index.html                        HTML template
├── App.tsx                           Root React component
├── App.css                           Global styles
├── constants.ts                      Frontend constants
├── types.ts                          TypeScript type definitions
│
├── package.json                      Node dependencies
├── vite.config.ts                    Vite build configuration
├── tsconfig.json                     TypeScript configuration
│
├── README.md                         Project readme
└── environment.yml                   Conda environment (optional)
```

---

## Tech Stack Overview

### Backend Stack

```
Flask (Web Framework)
  ├── Routes: RESTful API endpoints
  ├── Middleware: CORS, error handling
  └── Context: Request/response handling

SQLAlchemy (ORM)
  ├── Models: Conversation, Message entities
  ├── Database: SQLite (dev), MySQL/PostgreSQL (prod)
  └── Transactions: Multi-table operations

Python Utilities
  ├── google-generativeai: Gemini integration
  ├── anthropic: Claude integration
  ├── requests: HTTP for Ollama
  └── sqlalchemy: Database abstraction
```

### Frontend Stack

```
React (UI Framework)
  ├── Components: Reusable pieces
  ├── Hooks: State & effects
  └── Context: Global state

TypeScript (Type Safety)
  ├── Components: .tsx files
  ├── Services: .ts files
  └── Types: type definitions

Vite (Build Tool)
  ├── Development: Fast refresh
  ├── Production: Code splitting
  └── Bundling: Optimized output

Styling
  ├── CSS Modules: Component styles
  ├── Tailwind: Utility classes
  └── Inline: Dynamic styling
```

### Data & Storage

```
RAG Database (Vector Store)
  ├── Type: JSON files (simple vector store)
  ├── Location: instance/rag_db/
  ├── Content: Schemas, Rules, Settings
  └─ Fallback: JSON if vector DB unavailable

SQL Database (Conversation Storage)
  ├── Type: MySQL, PostgreSQL, SQLite
  ├── Models: Conversation, Message
  └─ Future: User, Subscription models
```

---

## Backend Architecture

### Service Layer

#### SettingsService (backend/services/settings_service.py)

**Responsibility**: All application settings stored in RAG only

**Key Methods**:
```python
class SettingsService:
    def get_active_database()                 # Get currently active DB
    def get_all_active_databases()            # Get all active databases
    def get_database_settings()               # Get all database configs
    
    def update_database_settings(data)        # ✨ Create/update DB + auto-RAG
    def delete_database_setting(id)           # Remove database
    
    def _populate_rag_schema(db_setting)      # ✨ Generate RAG items
    def _generate_natural_language_rule()     # ✨ Create business rules
    def _wipe_rag_schema(db_id)              # ✨ Clear old RAG
    
    def update_llm_settings(data)             # Configure LLM models
    def get_llm_settings()                    # Get LLM configurations
    
    def get_rag_schemas()                     # Get all schema items
    def get_business_rules()                  # Get rule definitions
```

**SettingsService Data Flow**:
```
User connects database with is_active=True
    ↓
update_database_settings() called
    ├─ Test connection
    ├─ Deactivate old database
    ├─ Save to RAG
    └─ Trigger _populate_rag_schema()
        ├─ Extract schema from database
        ├─ For each table:
        │  ├─ Generate natural language rule
        │  └─ Create 1 consolidated RAG item
        └─ Result: 1 item per table (not 3)
```

#### LLMService (backend/services/llm_service.py)

**Responsibility**: LLM initialization, prompt processing, SQL validation

**Key Methods**:
```python
class LLMService:
    def __init__()                           # Initialize from RAG settings
    def _ensure_active_model()               # Load active LLM
    
    def process_prompt(prompt, rag_context, business_rules, conversation_id)
                                             # Main entry point
    
    def _build_system_prompt(business_rules)        # ✨ Add constraints
    def _build_enriched_prompt(prompt, rag_context, 
                              business_rules, memory) # Add context
    
    def _extract_schema_from_rag()           # ✨ Get available tables
    def _extract_table_references(sql)       # ✨ Parse SQL for tables
    def _validate_sql_against_schema()       # ✨ Check query validity
    
    def _parse_response(response_text)       # Extract SQL from LLM response
    
    def _try_init_gemini()                   # Initialize Gemini
    def _try_init_claude()                   # Initialize Claude
    def _try_init_ollama()                   # Initialize Ollama
```

**Request Flow**:
```
POST /api/chat/process (user sends message)
    ↓
LLMService.process_prompt(prompt, rag_context, business_rules)
    ├─ Load conversation memory
    ├─ Build system prompt (with DB constraints)
    ├─ Build enriched prompt (with RAG context)
    ├─ Call active LLM (Gemini/Claude/Ollama)
    ├─ Parse response
    ├─ ✨ Validate SQL against schema
    ├─ Add warnings if invalid
    └─ Return {explanation, sql, parameters, confidence}
        ↓
Flask route returns JSON to frontend
```

#### DatabaseConnector (backend/utils/database.py)

**Responsibility**: Database connections and schema extraction

**Key Methods**:
```python
class DatabaseConnector:
    def test_connection(connection_string)   # Verify DB accessible
    def get_schema(connection_string)        # ✨ Extract full schema
    def execute_query(connection_string, sql) # Execute SQL
    
    # Private helpers
    def _extract_table_info(table)          # Get columns, keys
    def _extract_column_info(column)        # Get type, nullable
    def _extract_foreign_keys(table)        # Get relationships
```

**Schema Extraction**:
```
connect to database
    ↓
for each table:
    ├─ Get column definitions
    │  ├─ Name
    │  ├─ Type (INT, VARCHAR, etc)
    │  ├─ Nullable
    │  ├─ Default
    │  └─ Sample value (first row)
    ├─ Get primary key
    └─ Get foreign keys
        └─ Referenced table(s)
```

#### RAGDatabase (backend/utils/rag_database.py)

**Responsibility**: RAG vector store operations (JSON-based)

**Key Methods**:
```python
class RAGDatabase:
    def add_schema(table_name, content, db_id)      # Add table schema
    def get_all_schemas()                           # Get all schemas
    def delete_schema(schema_id)                    # Remove schema
    
    def add_business_rule(rule_name, rule_content, db_id, 
                         rule_type, meta_type)      # ✨ Add rule
    def get_all_rules()                             # Get all rules
    def delete_rule(rule_id)                        # Remove rule
    
    def save_setting(key, data)                     # Store setting
    def get_database_setting(id)                    # Retrieve setting
    
    def health_check()                              # Verify RAG health
```

**RAG Item Structure**:
```json
{
  "id": "unique_id",
  "metadata": {
    "database_id": "db_123",
    "category": "db_123_users",
    "meta_type": "table_comprehensive",
    "rule_type": "mandatory"
  },
  "content": "TABLE: users\n\nSCHEMA DEFINITION\n...",
  "vector": [0.1, 0.2, 0.3, ...]  // For semantic search
}
```

#### ConversationMemory (backend/utils/conversation_memory.py)

**Responsibility**: Track conversation history and provide context

**Key Methods**:
```python
class ConversationMemory:
    def __init__(conversation_id)
    def add_message(role, content)          # Save message
    def get_conversation_context(max=10)    # Get last N messages
    def get_decisions_context()             # Previous decisions made
    def get_schemas_context()               # Schemas mentioned
    def get_context_for_clarification()     # Smart context retrieval
```

**Context Types Tracked**:
- Full message history
- Previous SQL queries
- Table references
- Column references
- Filter conditions used
- Aggregation functions used

---

## Frontend Architecture

### Component Hierarchy

```
App.tsx (Root)
├── Sidebar.tsx (Navigation)
│   ├── Conversation List
│   ├── New Chat button
│   └── Settings link
│
├── ChatView.tsx (Main view)
│   ├── Message List
│   │   ├── UserMessage
│   │   └── AssistantMessage
│   │       └── ActionBox.tsx ✨ (SQL editor)
│   └── Input Area
│       └── Message input box
│
├── SettingsView.tsx (Settings)
│   ├── DatabaseForm
│   │   ├── Connection inputs
│   │   ├── Test button
│   │   └── Save button
│   ├── LLMForm
│   │   ├── Model select
│   │   ├── API key input
│   │   └── Test button
│   └── RAGManagementView.tsx ✨
│       ├── Schema item list
│       ├─ Expandable sections
│       └── Rebuild button
│
└── DBMSExplorer.tsx (Database view)
    ├── Table select
    ├── Column list
    └── Sample data
```

### State Management

**Global State** (App.tsx):
```typescript
interface AppState {
  currentView: 'chat' | 'settings' | 'dbms' | 'rag'
  currentConversationId: string
  conversations: Conversation[]
  activeDatabase: Database | null
  activeLLM: LLM | null
  loading: boolean
  error: string | null
}
```

**Local State** (Components):
```typescript
// ChatView.tsx
const [messages, setMessages] = useState<Message[]>([])
const [inputValue, setInputValue] = useState('')
const [loading, setLoading] = useState(false)

// ActionBox.tsx
const [isEditMode, setIsEditMode] = useState(false)
const [editedSql, setEditedSql] = useState('')
```

### Component Details

#### ActionBox.tsx (Key Component)

**Purpose**: Display and execute SQL suggestions

**Props**:
```typescript
interface Props {
  action: ActionData
  onExecute: (sql: string) => void
  onCancel: () => void
}

interface ActionData {
  type: 'DATABASE_QUERY' | 'EMAIL' | 'API_CALL' | string
  sql_query?: string
  parameters?: Record<string, any>
  confidence?: 'low' | 'medium' | 'high'
}
```

**Features**:
- View SQL in pre-formatted code
- Click Edit → textarea appears
- Modify SQL freely
- Click Confirm → execute
- Click Cancel → revert

**Code**:
```typescript
const [isEditMode, setIsEditMode] = useState(false)
const [editedSql, setEditedSql] = useState('')

const handleEdit = () => {
  setEditedSql(action.sql_query || '')
  setIsEditMode(true)
}

const handleConfirm = () => {
  onExecute(editedSql)
  setIsEditMode(false)
}

return (
  <>
    {isEditMode ? (
      <textarea value={editedSql} onChange={...} />
    ) : (
      <pre>{action.sql_query}</pre>
    )}
    <button onClick={handleEdit}>Edit</button>
    <button onClick={handleConfirm}>Confirm</button>
  </>
)
```

#### ChatView.tsx

**Purpose**: Main chat interface

**Features**:
- Display messages
- Input area
- Scroll to latest message
- Handle loading states

**Integration**:
```typescript
const handleSendMessage = async (text: string) => {
  setLoading(true)
  const response = await fetch('/api/chat/process', {
    method: 'POST',
    body: JSON.stringify({
      prompt: text,
      conversation_id: currentConversationId
    })
  })
  const data = await response.json()
  setMessages([...messages, data])
  setLoading(false)
}
```

---

## Key Files & Directories

### Critical Backend Files (✨ Most Important)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `app.py` | Flask entry point | Initialize Flask, register routes |
| `backend/services/settings_service.py` | Settings management | `update_database_settings()`, `_populate_rag_schema()` |
| `backend/services/llm_service.py` | LLM processing | `process_prompt()`, `_validate_sql_against_schema()` |
| `backend/utils/database.py` | DB operations | `get_schema()`, `execute_query()` |
| `backend/utils/rag_database.py` | RAG operations | `add_business_rule()`, `get_all_rules()` |
| `backend/utils/conversation_memory.py` | Context tracking | `get_conversation_context()` |

### Critical Frontend Files (✨ Most Important)

| File | Purpose | Key Components |
|------|---------|----------------|
| `App.tsx` | Root component | State management, routing |
| `components/ActionBox.tsx` | SQL editor | Edit, confirm, execute SQL |
| `components/ChatView.tsx` | Chat interface | Messages, input |
| `components/SettingsView.tsx` | Settings | Database, LLM config |
| `components/RAGManagementView.tsx` | Schema browser | View RAG items |

### Configuration Files

| File | Purpose |
|------|---------|
| `.env` | Environment variables (API keys, DB config) |
| `.env.example` | Template for `.env` |
| `requirements.txt` | Python dependencies |
| `package.json` | Node.js dependencies |
| `tsconfig.json` | TypeScript configuration |
| `vite.config.ts` | Vite build configuration |

---

## Core Modules Reference

### Connection String Format

```python
# MySQL
mysql+pymysql://user:password@host:3306/database

# PostgreSQL
postgresql://user:password@host:5432/database

# SQLite
sqlite:///path/to/database.db
```

### Schema Extraction Output

```python
{
  'tables': [
    {
      'table_name': 'users',
      'columns': [
        {
          'name': 'id',
          'type': 'INT',
          'nullable': False,
          'default': None,
          'sample_values': ['1', '2', '3']
        },
        # ... more columns
      ],
      'primary_keys': ['id'],
      'foreign_keys': [
        {
          'constrained_columns': ['manager_id'],
          'referred_table': 'users',
          'referred_columns': ['id']
        }
      ]
    },
    # ... more tables
  ]
}
```

### RAG Item Types

```python
# Schema item (consolidated)
{
  'meta_type': 'table_comprehensive',
  'rule_type': 'mandatory',
  'metadata': {
    'category': 'db_id_table_name'
  },
  'content': '''
  TABLE: table_name
  SCHEMA DEFINITION
  ...
  RELATIONSHIPS
  ...
  SAMPLE DATA
  ...
  BUSINESS RULE
  ...
  '''
}

# Business rule (old format, deprecated)
{
  'meta_type': 'relationship',
  'rule_type': 'optional'
}
```

### LLM Response Format

```json
{
  "explanation": "I'll query the users table to...",
  "action": {
    "type": "DATABASE_QUERY",
    "sql_query": "SELECT * FROM users WHERE...",
    "parameters": {"limit": 100},
    "confidence": "high"
  }
}
```

### SQL Validation Output

```python
{
  'valid': True/False,
  'invalid_tables': {'table1', 'table2'},
  'message': 'All tables are valid' or 'SQL references non-existent tables: table1, table2'
}
```

---

## API Endpoints

### Chat Endpoints

#### POST /api/chat/process
**Process natural language prompt and get SQL suggestion**

```
Request:
{
  "prompt": "Show me all users",
  "conversation_id": "conv_123",  // optional
  "rag_context": ["schema info"],  // optional
  "business_rules": [...]          // optional
}

Response:
{
  "explanation": "I'll retrieve all users from the database...",
  "action": {
    "type": "DATABASE_QUERY",
    "sql_query": "SELECT * FROM users",
    "parameters": {},
    "confidence": "high"
  },
  "conversation_id": "conv_123"
}
```

### Settings Endpoints

#### GET /api/settings/database
**Get all database settings**

```
Response:
[
  {
    "id": "db_123",
    "name": "Production",
    "db_type": "mysql",
    "host": "db.example.com",
    "port": 3306,
    "database": "production",
    "username": "user",
    "is_active": true
  },
  ...
]
```

#### PUT /api/settings/database
**Create or update database + trigger auto-RAG**

```
Request:
{
  "id": "db_123",          // optional (POST has none)
  "name": "Production",
  "db_type": "mysql",
  "host": "db.example.com",
  "port": 3306,
  "database": "production",
  "username": "user",
  "password": "secret",
  "is_active": true        // triggers auto-RAG
}

Response:
{
  "id": "db_123",
  "status": "active",
  "rag_generated": true,
  "tables_scanned": 42,
  "items_created": 42
}
```

#### DELETE /api/settings/database/{id}
**Delete database and its RAG items**

```
Response:
{
  "status": "deleted",
  "id": "db_123",
  "rag_wiped": true
}
```

### LLM Endpoints

#### GET /api/settings/llm
**Get all LLM configurations**

#### PUT /api/settings/llm
**Create or update LLM configuration**

```
Request:
{
  "id": "llm_1",
  "name": "Gemini",
  "model_type": "gemini",
  "model_id": "gemini-2.0-flash",
  "api_key": "***",
  "is_active": true,
  "priority": 1
}
```

### RAG Endpoints

#### GET /api/rag/schemas
**Get all RAG schema items**

```
Response:
[
  {
    "id": "schema_1",
    "metadata": {
      "meta_type": "table_comprehensive",
      "category": "db_1_users"
    },
    "content": "TABLE: users\n...",
    "vector": [...]
  },
  ...
]
```

#### GET /api/rag/rules
**Get all business rules**

#### POST /api/rag/rebuild
**Rebuild RAG schema from database**

```
Request:
{
  "database_id": "db_1"
}

Response:
{
  "status": "rebuilding",
  "tables_found": 42,
  "items_created": 42
}
```

### Action Endpoints

#### POST /api/actions/execute
**Execute suggested SQL action**

```
Request:
{
  "action": {
    "type": "DATABASE_QUERY",
    "sql_query": "SELECT * FROM users LIMIT 10"
  },
  "conversation_id": "conv_1"
}

Response:
{
  "status": "success",
  "rows": 10,
  "columns": ["id", "name", "email"],
  "data": [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    ...
  ]
}
```

### Conversation Endpoints

#### GET /api/conversations
**Get all conversations**

#### GET /api/conversations/{id}
**Get specific conversation**

#### POST /api/conversations
**Create new conversation**

#### DELETE /api/conversations/{id}
**Delete conversation**

---

## Database Schemas

### Conversation Model

```python
class Conversation(db.Model):
    id = db.Column(db.String, primary_key=True)
    title = db.Column(db.String)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    messages = relationship('Message', cascade='delete')
```

### Message Model

```python
class Message(db.Model):
    id = db.Column(db.String, primary_key=True)
    conversation_id = db.Column(db.String, ForeignKey('conversation.id'))
    role = db.Column(db.String)  # 'user' or 'assistant'
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime)
    action = db.Column(db.JSON)  # SQL, parameters, etc
```

---

## RAG System

### RAG File Structure

```
instance/rag_db/
├── schemas.json           # Schema items
├── rules.json            # Business rules
├── settings.json         # App settings
└── metadata.json         # Version, timestamps
```

### RAG Item Format

```json
{
  "id": "unique_hash",
  "type": "business_rule|schema|setting",
  "metadata": {
    "database_id": "db_123",
    "table_name": "users",
    "meta_type": "table_comprehensive",
    "category": "db_123_users",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "content": "Full text content...",
  "vector": [0.1, 0.2, 0.3, ...]  // Semantic embedding
}
```

### RAG Operations

```python
rag_db = RAGDatabase()

# Add schema
rag_db.add_schema(
  table_name='users',
  schema_content='Table: users\nColumns: ...',
  db_id='db_1'
)

# Add business rule
rag_db.add_business_rule(
  rule_name='users_comprehensive',
  rule_content='...',
  db_id='db_1',
  rule_type='mandatory',
  meta_type='table_comprehensive'
)

# Get items
schemas = rag_db.get_all_schemas()
rules = rag_db.get_all_rules()

# Delete by ID
rag_db.delete_schema('schema_id')
rag_db.delete_rule('rule_id')
```

---

## LLM Integration

### Gemini Integration

```python
import google.generativeai as genai

# Initialize
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

# Call
response = model.generate_content(prompt)
print(response.text)
```

### Claude Integration

```python
from anthropic import Anthropic

# Initialize
client = Anthropic(api_key=api_key)

# Call
response = client.messages.create(
  model='claude-3-5-haiku-20241022',
  max_tokens=1024,
  messages=[{"role": "user", "content": prompt}]
)
print(response.content[0].text)
```

### Ollama Integration

```python
import requests

# Call
response = requests.post(
  'http://localhost:11434/api/generate',
  json={
    'model': 'llama2',
    'prompt': prompt,
    'stream': False
  }
)
result = response.json()['response']
```

### System Prompt Template

```
You are an intelligent database assistant.

DATABASE CONSTRAINTS (⚠️ CRITICAL):
You MUST ONLY suggest SQL queries that use the following tables:
{available_tables}

BUSINESS RULES (MANDATORY):
{business_rules}

CONVERSATION HISTORY:
{conversation_context}

CURRENT REQUEST:
{user_prompt}

Respond in this format:
UNDERSTANDING: [What you understand]
ACTION_TYPE: [Type of action]
SQL_QUERY: [SQL if applicable]
PARAMETERS: [Required parameters]
CONFIDENCE: [low|medium|high]
NEXT_STEP: [What will happen next]
```

---

## Development Setup

### Prerequisites

```
Python 3.8+ with pip
Node.js 16+ with npm
MySQL/PostgreSQL (optional, can use SQLite)
Git for version control
```

### Backend Setup

```bash
# 1. Clone repository
git clone https://github.com/yourorg/brainplug.git
cd brainplug

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Unix
.\.venv\Scripts\Activate.ps1  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit .env with your API keys and database config

# 5. Initialize database
python -c "from backend.models import db; db.create_all()"

# 6. Run Flask development server
python app.py
```

### Frontend Setup

```bash
# In another terminal

# 1. Install Node dependencies
npm install

# 2. Run Vite dev server
npm run dev

# 3. Open browser
# http://localhost:5173
```

### Environment Variables (.env)

```bash
# LLM API Keys
GEMINI_API_KEY=your_gemini_key
LLM_CLAUDE_HAIKU_3.5_API_KEY=your_claude_key

# Database (optional, for testing)
DB_TYPE=sqlite
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=brainplug

# Flask
FLASK_ENV=development
FLASK_DEBUG=True

# Ollama (if using local LLM)
OLLAMA_HOST=http://localhost:11434
```

---

## Building & Deployment

### Frontend Build

```bash
# Build optimized frontend
npm run build

# Output: dist/
# Serve with: python -m http.server -d dist 8080
```

### Backend Production

```bash
# Using Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# Using uWSGI
pip install uwsgi
uwsgi --http :5000 --wsgi-file app.py --callable app
```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.11-slim
FROM node:18-alpine

# Multi-stage build...
WORKDIR /app
COPY . .

RUN pip install -r requirements.txt
RUN npm install && npm run build

EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

### Deployment Checklist

- [ ] Set FLASK_ENV=production
- [ ] Disable FLASK_DEBUG
- [ ] Use strong SECRET_KEY
- [ ] Set up proper logging
- [ ] Configure database (MySQL/PostgreSQL, not SQLite)
- [ ] Set up RAG database persistence
- [ ] Configure LLM API keys in environment
- [ ] Set up reverse proxy (Nginx/Apache)
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring/alerts
- [ ] Configure backups

---

## Testing

### Unit Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_rag_consolidation_llm_validation.py

# Run with coverage
pytest --cov=backend tests/
```

### Test Files

| File | Coverage |
|------|----------|
| `test_rag_consolidation_llm_validation.py` | RAG consolidation, SQL validation (17 tests) |
| `test_comprehensive_endpoints.py` | API endpoints |
| `test_rag_database_switching.py` | Database switching, RAG wipe |
| `test_auto_rag_system.py` | Auto-RAG generation |

### Writing Tests

```python
import unittest
from backend.services.llm_service import LLMService

class TestSQLValidation(unittest.TestCase):
    def setUp(self):
        self.llm = LLMService()
    
    def test_valid_sql(self):
        result = self.llm._validate_sql_against_schema(
            "SELECT * FROM users",
            ['users', 'orders']
        )
        self.assertTrue(result['valid'])
    
    def test_invalid_table(self):
        result = self.llm._validate_sql_against_schema(
            "SELECT * FROM nonexistent",
            ['users', 'orders']
        )
        self.assertFalse(result['valid'])
        self.assertIn('nonexistent', result['invalid_tables'])
```

---

## Contributing

### Code Style

**Python**:
- Follow PEP 8
- Use `black` for formatting
- Use `flake8` for linting

```bash
black backend/
flake8 backend/
```

**TypeScript/React**:
- Use `prettier` for formatting
- Use `eslint` for linting

```bash
npx prettier --write components/
npx eslint components/ --fix
```

### Git Workflow

```bash
# 1. Create feature branch
git checkout -b feature/description

# 2. Make changes and commit
git add .
git commit -m "Clear description of changes"

# 3. Push branch
git push origin feature/description

# 4. Create pull request on GitHub
# 5. Wait for code review
# 6. Merge after approval
```

### Adding New LLM Provider

```python
# In llm_service.py

def _try_init_new_provider(self):
    """Initialize new LLM provider"""
    try:
        from new_provider import NewClient
        api_key = self.active.get('api_key')
        self.new_client = NewClient(api_key=api_key)
        self.model_type = 'new_provider'
        logger.info("✓ Initialized New Provider")
        return self.active
    except Exception as e:
        logger.warning(f"Failed to init New Provider: {e}")
        return None
```

### Adding New Database Type

```python
# In database.py

def _get_driver_for_type(self, db_type):
    drivers = {
        'mysql': 'pymysql',
        'postgresql': 'psycopg2',
        'sqlite': 'sqlite3',
        'oracle': 'cx_Oracle',  # NEW
    }
    return drivers.get(db_type.lower())
```

---

## Troubleshooting

### Common Issues

#### Issue: ModuleNotFoundError: No module named 'backend'
**Solution**: Run from project root, ensure .venv activated

#### Issue: LLM API timeouts
**Solution**: Increase timeout in llm_service.py, check API status

#### Issue: RAG database corrupted
**Solution**: Delete `instance/rag_db/`, next run will regenerate

#### Issue: SQL validation always fails
**Solution**: Check if database is active, rebuild RAG schema

#### Issue: Frontend doesn't update after code changes
**Solution**: Clear browser cache or use incognito mode

#### Issue: Database connection refused
**Solution**: Verify host, port, credentials in .env

### Debug Mode

**Enable verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Check RAG database**:
```bash
python -c "from backend.utils.rag_database import RAGDatabase; \
rag = RAGDatabase(); \
print(f'Schemas: {len(rag.get_all_schemas())}'); \
print(f'Rules: {len(rag.get_all_rules())}')"
```

**Test LLM**:
```bash
python -c "from backend.services.llm_service import LLMService; \
llm = LLMService(); \
print(f'Model type: {llm.model_type}')"
```

---

## Key Concepts for Developers

### 1. RAG Consolidation (v2.0 Feature)
- **What**: 1 RAG item per table instead of 3
- **Why**: Cleaner UX, faster retrieval
- **Where**: `_populate_rag_schema()` in `settings_service.py`
- **How**: Create 1 `table_comprehensive` item with all info

### 2. SQL Validation (v2.0 Feature)
- **What**: Check SQL uses valid tables
- **Why**: Prevent "table not found" errors
- **Where**: `_validate_sql_against_schema()` in `llm_service.py`
- **How**: Extract table names, compare against RAG schema

### 3. Conversation Memory
- **What**: Track context across messages
- **Why**: Understand pronouns, references
- **Where**: `ConversationMemory` in `conversation_memory.py`
- **How**: Store messages, extract context when needed

### 4. System Prompt Engineering
- **What**: Constrain LLM to database structure
- **Why**: Ensure generated SQL is valid
- **Where**: `_build_system_prompt()` in `llm_service.py`
- **How**: Include DB constraints, business rules, examples

### 5. Auto-RAG Generation
- **What**: Automatic documentation on database connect
- **Why**: No manual schema entry needed
- **Where**: `_populate_rag_schema()` in `settings_service.py`
- **How**: Extract schema, create items, index for search

---

## Performance Optimization Tips

### Backend
- Use connection pooling (10-100 connections)
- Cache RAG schema in memory
- Implement result pagination
- Add database indexes for common queries
- Use async for long-running tasks

### Frontend
- Lazy load conversations
- Virtualize long lists
- Memoize expensive components
- Code split with Vite
- Compress images

### Database
- Add indexes on foreign keys
- Limit result set size (max 1000 rows)
- Use EXPLAIN to optimize queries
- Archive old logs/conversations
- Regular maintenance (VACUUM, ANALYZE)

---

## Security Best Practices

1. **Never commit .env file**: Add to .gitignore
2. **Use environment variables**: For all secrets
3. **Validate all inputs**: On frontend AND backend
4. **Escape SQL parameters**: In database operations
5. **Log safely**: Don't log passwords/keys
6. **HTTPS only**: In production
7. **CORS configuration**: Restrict origins
8. **Rate limiting**: Prevent abuse

---

## Useful Commands

```bash
# Backend
python app.py                               # Run Flask
pytest -v                                   # Run tests
python -m pdb app.py                       # Debug mode
python -c "from backend.models import db; db.create_all()"

# Frontend
npm run dev                                 # Dev server
npm run build                               # Production build
npm run preview                             # Preview build
npm run lint                                # Check code

# Database
mysql -h host -u user -p database < dump.sql  # Restore backup
mysqldump database > backup.sql             # Create backup
psql database < dump.sql                    # PostgreSQL restore

# Git
git log --oneline -10                       # Recent commits
git diff branch1..branch2                   # Compare branches
git stash                                   # Save changes temporarily
```

---

**Status**: ✅ Complete for v2.0
**Last Updated**: February 2026
**Next Update**: August 2026 (v3.0)

For user documentation, see [KEY_SOP_DOCUMENT_USER_GUIDE.md](KEY_SOP_DOCUMENT_USER_GUIDE.md)

For architecture overview, see [KEY_APP_FEATURES_AND_ARCHITECTURE.md](KEY_APP_FEATURES_AND_ARCHITECTURE.md)
