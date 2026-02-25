# Gemini MCP - AI Assistant with RAG & LLM

A comprehensive web application that combines RAG (Retrieval Augmented Generation), LLM integration, and Flask backend to provide an intelligent AI assistant that can:

1. **Respond with Explanations** - Understand user prompts and explain what actions will be taken
2. **Execute Database Queries** - Run SQL queries on connected databases and display results
3. **Send/Read Emails** - Use connected data to send emails and read mailbox
4. **URL Reading & Summarization** - Read and summarize web content
5. **API Integration** - Call external APIs and process responses
6. **Scheduled Tasks** - Schedule activities for automatic execution
7. **Report Generation** - Create and export reports from accumulated data
8. **Conversation Management** - Engage users in conversations until actions are confirmed

## Architecture

### Backend (Flask)
- **Framework**: Flask with Flask-CORS
- **Database**: SQLAlchemy ORM (supports PostgreSQL, MySQL, SQLite)
- **Vector Store**: ChromaDB for RAG
- **LLM**: Google Generative AI (Gemini)
- **Task Scheduling**: APScheduler for scheduled activities

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Charts**: Recharts for data visualization
- **Icons**: React Icons
- **HTTP Client**: Axios

## Project Structure

```
gemini-mcp/
├── backend/
│   ├── models/
│   │   ├── conversation.py      # Chat history models
│   │   ├── settings.py          # Configuration models
│   │   ├── rag.py               # RAG & business rules models
│   │   └── action.py            # Actions & reports models
│   ├── services/
│   │   ├── llm_service.py       # LLM processing
│   │   ├── rag_service.py       # RAG retrieval & management
│   │   ├── action_service.py    # Action execution
│   │   └── settings_service.py  # Settings management
│   └── utils/
│       ├── logger.py            # Logging setup
│       ├── database.py          # Database utilities
│       └── url_reader.py        # URL reading utilities
├── components/
│   ├── Sidebar.tsx              # Navigation sidebar
│   ├── ChatView.tsx             # Chat interface
│   ├── ActionBox.tsx            # Action display & confirmation
│   ├── SettingsView.tsx         # Settings container
│   └── settings/
│       ├── DatabaseSettings.tsx  # Database configuration (Page 1)
│       ├── LLMSettings.tsx        # LLM models config (Page 2)
│       ├── RAGSettings.tsx        # RAG management (Page 3)
│       ├── SystemSettings.tsx     # SMTP/IMAP/POP (Page 4)
│       ├── ScheduledActivities.tsx # Task scheduling (Page 5)
│       ├── ReportsSettings.tsx    # Reports management (Page 6)
│       └── OtherSettings.tsx      # API integrations (Page 7)
├── services/
│   └── geminiService.ts         # API client
├── app.py                       # Flask main application
├── App.tsx                      # React main component
├── index.tsx                    # React entry point
├── styles.css                   # Global styles
├── types.ts                     # TypeScript type definitions
├── constants.ts                 # Application constants
├── package.json                 # npm dependencies
├── requirements.txt             # Python dependencies
├── vite.config.ts               # Vite configuration
├── tsconfig.json                # TypeScript configuration
└── README.md                    # This file
```

## Installation

### Prerequisites
- Python 3.8+
- Node.js 16+
- npm or yarn

### Backend Setup

1. **Create and activate virtual environment**:
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\Activate.ps1
# On macOS/Linux:
source .venv/bin/activate
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables** (create `.env` file):
```bash
GEMINI_API_KEY=your_google_api_key_here
DATABASE_URL=sqlite:///gemini_mcp.db
FLASK_ENV=development
```

### Frontend Setup

1. **Install npm dependencies**:
```bash
npm install
```

2. **Build TypeScript (optional)**:
```bash
npm run type-check
```

## Running the Application

### Start Backend (Terminal 1)
```bash
# Make sure venv is activated
python app.py
```
Backend will run on `http://localhost:5000`

### Start Frontend (Terminal 2)
```bash
npm run dev
```
Frontend will run on `http://localhost:5173`

### Build for Production
```bash
# Frontend
npm run build

# Backend is ready as-is, just ensure production settings in .env
```

## Key Features

### 1. Intelligent Conversation System
- AI understands user intent
- Suggests actions before execution
- Requires confirmation before running actions
- Maintains conversation history

### 2. Multi-Action Support
- **Database Queries**: Execute SQL on connected databases
- **Email**: Send emails using SMTP, read using IMAP/POP
- **URL Reading**: Scrape and summarize web content
- **API Calls**: Integrate with external APIs
- **Scheduling**: Schedule activities for later execution
- **Reports**: Generate reports from accumulated data

### 3. RAG (Retrieval Augmented Generation)
- Automatic database schema extraction and embedding
- Business rules management (compulsory rules always included)
- Context retrieval from vector database
- Improves LLM responses with relevant data

### 4. Comprehensive Settings (7 Pages)
1. **Database Connection Settings**: Configure database sources
2. **LLM Model Settings**: Manage multiple LLM models with priority
3. **RAG Settings**: Define and manage business rules
4. **System Settings**: Email (SMTP/IMAP/POP) configuration
5. **Scheduled Activities**: View and manage scheduled tasks
6. **Reports**: Generate and export reports
7. **Other Settings**: External API configuration

### 5. User-Friendly Interface
- Modern, responsive design
- Sidebar navigation
- Real-time message updates
- Conversation history management
- Form validation and error handling

## API Endpoints

### Chat
- `POST /api/chat/message` - Send message and get AI response
- `POST /api/chat/confirm-action` - Confirm and execute suggested action
- `GET /api/conversations` - List all conversations
- `GET /api/conversations/<id>` - Get specific conversation
- `DELETE /api/conversations/<id>` - Delete conversation

### Settings
- `GET/POST /api/settings/database` - Database settings
- `GET/POST /api/settings/llm` - LLM model settings
- `GET/POST /api/settings/rag` - RAG settings
- `GET/POST /api/settings/system` - System settings
- `GET/POST /api/settings/api-configs` - API configurations
- `GET/POST /api/settings/scheduled-activities` - Scheduled tasks
- `PUT/DELETE /api/settings/scheduled-activities/<id>` - Manage specific task

### Reports
- `GET /api/reports` - List all reports
- `GET /api/reports/<id>` - Get specific report
- `POST /api/reports` - Create report
- `DELETE /api/reports/<id>` - Delete report

### RAG
- `GET/POST /api/rag/schema` - Database schema management
- `GET/POST/PUT/DELETE /api/rag/business-rules` - Business rules management

### Health
- `GET /api/health` - Health check

## Usage Examples

### Example 1: Send Email with Database Context
**User**: "Send email to customer John about their latest order"

**AI**:
1. Queries customers table to get John's email
2. Queries orders table to get his latest order
3. Composes email with order details
4. Displays suggested action
5. Sends email on confirmation

### Example 2: Generate Report
**User**: "Create a report of all orders from last month"

**AI**:
1. Executes database query for monthly orders
2. Formats results as chart and summary
3. Creates report record
4. Makes available for download

### Example 3: Scheduled URL Monitoring
**User**: "Check this website daily and alert me if anything changes"

**AI**:
1. Schedules daily URL check
2. Creates automated task
3. Sets up comparison logic
4. Confirms when setup is complete

## Configuration Guide

### Adding a New Database

1. Go to Settings → Database
2. Fill in connection details
3. Click "Save Settings"
4. Schema is automatically extracted and added to RAG

### Adding a New LLM Model

1. Go to Settings → LLM Models
2. Select model type (Gemini, GPT, Claude, Llama, Local)
3. Enter API key (if cloud-based)
4. Set priority (0 = highest)
5. Add API endpoint for local models
6. Click "Add Model"

### Defining Business Rules

1. Go to Settings → RAG
2. Click "Add Rule"
3. Mark as "Compulsory" for rules that apply to all prompts
4. Click "Add Rule"
5. Rules are automatically included in LLM context

## Database Schema

### Conversations
- `id` (PK)
- `title` - Conversation title
- `created_at`, `updated_at` - Timestamps
- Foreign key to Messages

### Messages
- `id` (PK)
- `conversation_id` (FK)
- `role` - 'user' or 'assistant'
- `content` - Message text
- `action_data` - Suggested action JSON
- `action_executed` - Boolean
- `action_result` - Execution result

### DatabaseSetting
- `id` (PK)
- `name` - Connection name
- `db_type` - postgresql, mysql, sqlite, etc.
- `host`, `port`, `database`, `username`, `password`
- `is_active` - Currently active connection

### LLMModel
- `id` (PK)
- `name`, `model_type`, `model_id`
- `api_key`, `api_endpoint`
- `priority` - Model priority order
- `is_active` - Enabled/disabled

### BusinessRule
- `id` (PK)
- `name`, `description`, `content`
- `rule_type` - compulsory, optional, constraint
- `category`
- `is_active`

### ScheduledActivity
- `id` (PK)
- `title`, `action_type`, `action_data`
- `scheduled_for`, `recurrence`
- `is_active`, `last_executed`, `next_execution`

### Report
- `id` (PK)
- `title`, `description`, `report_type`
- `data` (JSON), `action_ids`
- `created_at`

## Troubleshooting

### Backend doesn't start
- Check if port 5000 is available
- Verify all Python dependencies installed: `pip list`
- Check `.env` file exists and has valid API keys

### Frontend build fails
- Clear node_modules: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (requires 16+)

### Database connection fails
- Verify database credentials in Settings
- Check if database server is running
- Test connection URL in database settings

### LLM not responding
- Verify `GEMINI_API_KEY` in `.env`
- Check API key is valid and not expired
- Ensure model is activated in settings

### RAG context not working
- Connect a database first to extract schema
- Define some business rules
- Restart the application to refresh RAG

## Performance Optimization

1. **Limit RAG context**: Adjust `top_k` parameter in RAG retrieval
2. **Cache frequently accessed data**: Use Redis (future improvement)
3. **Batch operations**: Multiple queries in one prompt
4. **Async processing**: Use task queues for heavy operations

## Security Considerations

1. **API Keys**: Store in `.env`, never commit
2. **Database Credentials**: Use strong passwords
3. **Email Authentication**: Use app-specific passwords
4. **CORS**: Configure for your domain only
5. **Input Validation**: All user inputs are validated
6. **SQL Injection**: Using SQLAlchemy ORM prevents injection

## Future Enhancements

- [ ] Multi-user support with authentication
- [ ] Real-time collaboration
- [ ] Advanced caching with Redis
- [ ] GraphQL API
- [ ] Mobile app
- [ ] Advanced data visualization
- [ ] Custom action plugins
- [ ] Webhook integrations
- [ ] Audit logging
- [ ] Advanced search with Elasticsearch

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - feel free to use for any purpose

## Support

For issues and questions:
- Open an issue on GitHub
- Check existing documentation
- Review API endpoints and examples

---

**Happy Coding! 🚀**
