# KEY_SOP_DOCUMENT_USER_GUIDE
## Brainplug: Standard Operating Procedures & User Guide

**Version**: 2.0
**Last Updated**: February 2026
**Audience**: End Users, Support Team, Administrators

---

## Table of Contents

1. [Quick Start Guide](#quick-start-guide)
2. [System Overview](#system-overview)
3. [Getting Started](#getting-started)
4. [Core Workflows](#core-workflows)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)
8. [FAQ](#faq)
9. [Support & Escalation](#support--escalation)

---

## Quick Start Guide

### 5-Minute Setup

#### Step 1: Access the Application
```
URL: http://localhost:5000 (or your production URL)
Expected: Homepage loads with Chat view visible
```

#### Step 2: Connect a Database (First Time)
```
1. Click Settings (gear icon)
2. Navigate to "Databases"
3. Click "Add Database"
4. Fill in:
   - Name: "Production Database"
   - Type: MySQL (or your database type)
   - Host: your.database.host
   - Port: 3306
   - Username: your_username
   - Password: your_password
   - Database: your_database_name
5. Click "Test Connection" → Should see ✅ Connected
6. Click "Save" → Auto-RAG generation starts
7. Wait for: "[AUTO-RAG] COMPLETE" in logs
```

#### Step 3: Start Chatting
```
1. Click Chat view
2. Type: "Show me all users"
3. System suggests SQL
4. Click "Confirm" → See results
Done! 🎉
```

---

## System Overview

### What is Brainplug?

**Brainplug** is an AI-powered database assistant that:
- ✅ Converts your natural language questions into SQL
- ✅ Executes those queries against your databases
- ✅ Automatically manages database documentation
- ✅ Remembers your conversation context
- ✅ Validates SQL before execution

### Key Concepts

#### Natural Language Queries
```
You ask: "Show me top 10 customers by order count"
System converts to: SELECT customers.name, COUNT(orders.id) as order_count 
                    FROM customers 
                    JOIN orders ON customers.id = orders.customer_id 
                    GROUP BY customers.id 
                    ORDER BY order_count DESC 
                    LIMIT 10
System executes and shows results ✅
```

#### Auto-RAG
```
You connect a database with 10 tables
System automatically:
  • Reads all tables and columns
  • Generates 10 documentation items (1 per table)
  • Creates natural language descriptions
  • Indexes for intelligent search
  No manual work needed! ✅
```

#### Conversation Memory
```
You ask: "Show me users"
System: Displays user table

You ask: "How many from January?"
System: Understands you mean "users from January"
Uses previous context automatically ✅
```

#### SQL Editing
```
System suggests query → You can edit it → Confirm changes
Perfect for fixing that 1 WHERE clause! ✅
```

### Supported Databases

| Database | Status | Notes |
|----------|--------|-------|
| MySQL | ✅ Full Support | Most common |
| PostgreSQL | ✅ Full Support | Advanced features |
| MariaDB | ✅ Full Support | MySQL compatible |
| SQLite | ✅ Full Support | File-based, for dev |
| Others | 🔶 Extensible | Can add custom |

### Supported LLMs

| LLM | Status | Best For |
|-----|--------|----------|
| Google Gemini | ✅ Recommended | Fast, cost-effective |
| Claude | ✅ Recommended | Better reasoning |
| Ollama (Local) | ✅ Available | Privacy, no API keys |

---

## Getting Started

### First-Time Setup Checklist

- [ ] Access application URL
- [ ] Connect first database
- [ ] Configure at least one LLM (Gemini or Claude)
- [ ] Test with simple query: "Show me all users"
- [ ] Review RAG schema in Settings
- [ ] Bookmark the application URL

### Application Layout

```
┌─────────────────────────────────────────────────┐
│  Brainplug | ⚙️ Settings | 🗣️ Chat | ❓ Help  │ ← Top Bar
├─────┬──────────────────────────────────────────┤
│     │                                          │
│ 🆕  │                                          │
│Side │        MAIN CONTENT AREA                 │
│bar  │    (Chat, Settings, RAG Manager)        │
│     │                                          │
│ 📝  │                                          │
│Conv │                                          │
│List │                                          │
├─────┴──────────────────────────────────────────┤
│  Status Bar | Connected to: production_db    │
└─────────────────────────────────────────────────┘
```

#### Navigation

- **🆕 New Chat**: Start new conversation
- **📝 Conversation List**: Click to resume previous chats
- **⚙️ Settings**: Configure databases, LLMs, view RAG schema
- **🗣️ Chat**: Main interface (default view)
- **Status Bar**: Shows current database connection

### Settings Overview

#### Databases Section
```
Databases
├─ production_db (ACTIVE)
│  ├─ Type: MySQL
│  ├─ Host: db.example.com
│  ├─ Status: ✅ Connected
│  ├─ Tables: 42
│  └─ [Deactivate | Edit | Delete]
├─ staging_db (INACTIVE)
│  ├─ Status: ✅ Available
│  └─ [Activate | Edit | Delete]
└─ [Add New Database]
```

#### LLM Settings Section
```
Language Models
├─ Gemini (ACTIVE, Priority 1)
│  ├─ Model: gemini-2.0-flash
│  ├─ Status: ✅ Connected
│  └─ [Configure | Set as Primary | Disable]
├─ Claude (ACTIVE, Priority 2)
│  ├─ Model: claude-3-5-haiku
│  ├─ Status: ✅ Connected (Fallback)
│  └─ [Configure | Test | Disable]
└─ [Add New LLM]
```

#### RAG Schema Section
```
RAG Schema Management
├─ Database: production_db
├─ Tables: 42 items
├─ Last Updated: 2 hours ago
└─ [View Schema | Rebuild | Export]
```

---

## Core Workflows

### Workflow 1: Ask a Simple Question

**Scenario**: Get list of all customers

**Steps**:
```
1. Click Chat (or already there)
2. Type: "Show me all customers"
   └─ Click [Send] or press Enter
3. Wait for system to:
   ├─ Load database schema
   ├─ Call Gemini (or Claude)
   ├─ Generate SQL
   └─ Validate SQL (should be ✅ VALID)
4. Review suggested SQL in message
   └─ SQL: SELECT * FROM customers
5. Edit if needed:
   ├─ Click [Edit] button
   ├─ Modify in textarea
   └─ Click [Confirm]
6. Click [Confirm] or [Execute]
7. Wait for results
8. See table with customer data
   ├─ Rows: 150
   ├─ Columns: id, name, email, phone, created_at
   └─ [Export | Refresh | Done]
```

**Expected Result**:
- ✅ SQL executed successfully
- ✅ Results shown in table format
- ✅ Message saved to conversation history

### Workflow 2: Complex Query with Filters

**Scenario**: Find high-value customers (orders > $1000)

**Steps**:
```
1. Chat: "Show me customers with orders over $1000"
2. System generates:
   SQL: SELECT DISTINCT c.id, c.name, c.email, SUM(o.total) as total_orders
        FROM customers c
        JOIN orders o ON c.id = o.customer_id
        GROUP BY c.id, c.name, c.email
        HAVING SUM(o.total) > 1000
        ORDER BY total_orders DESC
3. Validation: ✅ VALID (all tables exist)
4. Click [Confirm]
5. See results:
   ├─ 24 customers matched
   ├─ Top customer: $50,000 in orders
   └─ Results saved to history
```

**If SQL is Wrong**:
```
❌ VALIDATION WARNING: Table 'orders' references column 'total'
                       but 'orders' table was not found
1. Click [Edit]
2. Fix the table name
3. Click [Confirm]
4. Retry
```

### Workflow 3: Multi-Step Analysis

**Scenario**: "Show users, then show their orders, then total"

**Steps**:
```
Step 1: "Show me all users"
└─ System shows users table
└─ Context saved: user_id, names

Step 2: "Show their recent orders"
└─ System understands: orders for those users
└─ Context saved: order data linked to users

Step 3: "What's the total revenue?"
└─ System uses context: Calculate SUM(orders.total)
└─ No need to re-specify tables/users
```

**Why It Works**:
- ✅ Conversation memory tracks all previous queries
- ✅ System maintains context between messages
- ✅ Pronouns ("their", "the") resolved automatically

### Workflow 4: Edit and Re-execute

**Scenario**: Query returned wrong results

**Steps**:
```
1. View the result that's wrong
   └─ Expected 50 rows, got 150
2. Find the SQL in chat history
3. Click [Edit]
4. Modify the query:
   - Add: WHERE status = 'active'
   - Change: LIMIT 50
5. Click [Confirm to Edit]
6. Click [Execute]
7. New results display
8. ✅ Now showing correct data
```

### Workflow 5: Switch Databases

**Scenario**: Need to query staging instead of production

**Steps**:
```
1. Settings → Databases
2. Click the active database (production_db)
3. Click [Deactivate]
   └─ Auto-RAG clears old database items
4. Click the staging database
5. Click [Activate]
   └─ Auto-RAG regenerates for staging
   └─ Wait for: "[AUTO-RAG] COMPLETE"
6. Return to Chat
7. Ask questions - now queries staging! ✅
```

**Important**: Only 1 database can be active at a time

### Workflow 6: View Database Schema

**Scenario**: "What tables are available?"

**Steps**:
```
1. Settings → RAG Schema
2. See list of tables:
   ├─ users (comprehensive)
   ├─ orders (comprehensive)
   ├─ products (comprehensive)
   └─ ... (all 42 tables)
3. Click any table to expand:
   ├─ SCHEMA DEFINITION
   │  └─ Columns and types
   ├─ RELATIONSHIPS
   │  └─ Foreign keys to other tables
   ├─ SAMPLE DATA
   │  └─ Example values
   └─ BUSINESS RULE
      └─ What this table is for
4. Edit business rule if needed
5. Return to chat with better understanding
```

**What You'll See**:
```
TABLE: orders

SCHEMA DEFINITION
Primary Key: id
Columns:
  - id: INT, nullable=false
  - customer_id: INT, nullable=false → users
  - order_date: DATETIME, nullable=false
  - total: DECIMAL, nullable=false

RELATIONSHIPS (Foreign Keys)
  - customer_id → users(id)
  - product_id → products(id)

SAMPLE DATA (Example values)
  - id: 1001
  - customer_id: 42
  - order_date: 2024-01-15 10:30:00
  - total: 99.99

BUSINESS RULE & USAGE
The orders table stores customer purchase transactions...
```

---

## Advanced Features

### Feature 1: Export Results

**Scenario**: Need to share query results with manager

**Steps**:
```
1. After query executes and shows results
2. Click [Export]
3. Choose format:
   ├─ CSV (Excel compatible) ✅
   ├─ JSON (API friendly) ✅
   └─ PDF (formatted report) 🔜 Coming
4. File downloads automatically
5. Open in Excel or share
```

### Feature 2: Save Conversation

**Scenario**: Want to keep analysis for later

**What Happens Automatically**:
```
• Every message saved
• Every query result cached
• Accessible via Sidebar
• Can resume anytime

To Resume:
1. Click Sidebar
2. Find conversation (e.g., "Customer Analysis")
3. Click to open
4. Continue where you left off ✅
```

### Feature 3: Clear Conversation

**Scenario**: Start fresh without database context

**Steps**:
```
1. In Chat view
2. Click [Clear Context] or [New Chat]
3. Confirm: "Clear all conversation history?"
4. Choose:
   ├─ [Clear] → Fresh start
   └─ [Cancel] → Keep history
5. New conversation begins ✅
```

### Feature 4: Search Conversations

**Scenario**: Find that analysis from last month

**Steps**:
```
1. Sidebar: Conversations section
2. Type in search box: "customer analysis"
3. Results filtered:
   ├─ "Customer Analysis" (3 messages)
   └─ "Customer demographics" (7 messages)
4. Click to open
```

### Feature 5: Clone Query

**Scenario**: Reuse a previous query with modifications

**Steps**:
```
1. Find the query in chat history
2. Click [Copy SQL]
3. Chat: Paste previous SQL
4. Edit as needed
5. Execute ✅
```

---

## Troubleshooting

### Issue 1: "Table not found" Error

**Message**: ❌ VALIDATION WARNING: SQL references non-existent tables

**Causes**:
- Table name typo in SQL
- Table doesn't exist in connected database
- Wrong database selected

**Solutions**:
```
1. Check database status
   └─ Settings → Databases → Check ACTIVE status
2. View available tables
   └─ Settings → RAG Schema → See all tables
3. Click [Edit] in error message
4. Fix table name (copy from RAG Schema if needed)
5. Click [Confirm]
6. Retry query
```

### Issue 2: "Connection Failed" Error

**Message**: ❌ Could not connect to database

**Causes**:
- Database server is down
- Wrong credentials
- Network connectivity issue
- Wrong host/port

**Solutions**:
```
1. Verify database is running
   └─ Check with: mysql -h host -u user (or your DB tool)
2. Check credentials in Settings
   └─ Settings → Databases → Edit → Verify all fields
3. Test connection
   └─ Click [Test Connection] → Should see ✅
4. If still failing: Check firewall/network
5. If still failing: Ask DBA to check database logs
```

### Issue 3: LLM Not Responding

**Symptom**: Chat hangs or times out after 30 seconds

**Possible Causes**:
- API key invalid
- API rate limit exceeded
- Network issue to LLM provider
- LLM service down

**Solutions**:
```
1. Check API key
   └─ Settings → LLM Settings → Verify key
2. Wait 1 minute and retry
3. Try fallback LLM
   └─ If Gemini fails, Claude tries automatically
4. Check logs for error message
5. If using Ollama: Ensure it's running
   └─ ollama serve (in terminal)
```

**Status Check**:
- Gemini: [status.cloud.google.com](https://status.cloud.google.com)
- Claude: [status.anthropic.com](https://status.anthropic.com)

### Issue 4: Wrong SQL Suggested

**Problem**: System suggested query, but results are incorrect

**Example**:
```
You asked: "Active users"
System gave: SELECT * FROM users (missing WHERE status = 'active')
```

**Solutions**:
```
1. Click [Edit]
2. Add missing WHERE clause
3. Review against RAG Schema
   └─ Check column names
   └─ Verify table relationships
4. Click [Confirm]
5. Retry
```

**Prevention**:
- Use more specific language
- Mention filters explicitly
- Ask system to explain its logic first

### Issue 5: Results Not Displayed

**Problem**: Query executes but no table shows

**Causes**:
- Results are too large (>1000 rows)
- Result set is empty
- Display error

**Solutions**:
```
1. Add LIMIT clause: "LIMIT 100"
2. Check if results are empty
   └─ Ask system: "How many records?"
3. Export results instead
   └─ Click [Export] → Opens in Excel
```

### Issue 6: RAG Schema Shows Wrong Tables

**Problem**: Schema items don't match database

**Cause**: Database was changed but RAG not regenerated

**Solution**:
```
1. Settings → RAG Schema
2. Click [Rebuild Schema]
3. Confirm: "Rebuild schema from database?"
4. Wait for: "[AUTO-RAG] COMPLETE"
5. Schema now up-to-date ✅
```

### Emergency: Reset Everything

**Only if completely stuck**:
```
1. Stop the application
   └─ Ctrl+C in terminal
2. Delete RAG database
   └─ rm -rf instance/rag_db (Linux/Mac)
   └─ rmdir instance\rag_db (Windows)
3. Restart application
   └─ python app.py
4. Reconnect database
   └─ Auto-RAG regenerates everything
5. Verify with simple query
```

---

## Best Practices

### BP1: Ask Clear Questions

**❌ Vague**:
```
"Show me things"
```

**✅ Clear**:
```
"Show me all customers from California with orders over $500 in 2024"
```

**Helps**:
- LLM generates correct SQL on first try
- No need for edits
- Results match expectations

### BP2: Use Conversation Context

**❌ Inefficient**:
```
User: "Show me users"
User: "Join with orders and show everything"
User: "Now filter by date and show totals"
```

**✅ Efficient**:
```
User: "Show me users with their orders and total spending from 2024"
```

**Helps**:
- Fewer messages
- Faster execution
- Less back-and-forth

### BP3: Verify Schema Before Complex Queries

**Workflow**:
```
1. New database? 
   └─ View RAG Schema first
2. Unfamiliar tables?
   └─ Click to expand and read description
3. Unsure of relationships?
   └─ Check RELATIONSHIPS section
4. Now ask questions with confidence ✅
```

### BP4: Always Review Before Confirming

**Habit**:
```
Before clicking [Confirm]:
1. Read the suggested SQL
2. Check for:
   ├─ Correct table names
   ├─ Correct column names
   ├─ Correct JOINs
   ├─ Correct WHERE clauses
   └─ Expected result count
3. Click [Edit] if any doubt
4. Then [Confirm]
```

### BP5: Use Edit Mode for Learning

**Technique**:
```
1. Ask system for a query
2. Review the SQL
3. Click [Edit] even if correct
4. Study the structure:
   ├─ How were tables JOINed?
   ├─ How were filters applied?
   ├─ What was the ORDER BY?
5. Learn from example
6. Confirm to execute
```

### BP6: Handle Large Results

**For Big Queries**:
```
Instead of: SELECT * FROM large_table
Do this:    SELECT * FROM large_table LIMIT 100

Or ask:     "Show me the first 100 records"
Or ask:     "Count how many records match this criteria"
```

**Export Option**:
```
For large exports:
1. Run query
2. Click [Export]
3. Choose CSV format
4. Open in Excel for full analysis
```

### BP7: Maintain Database Consistency

**Don't**:
- ❌ Switch databases mid-conversation
- ❌ Edit database settings during queries
- ❌ Delete active database

**Do**:
- ✅ Finish conversation before switching
- ✅ Switch databases only when idle
- ✅ Back up important queries first

### BP8: Use Meaningful Conversation Names

**When Creating New Chat**:
```
❌ New Chat 1
✅ Q1 2024 Sales Analysis
✅ Customer RFM Segmentation
✅ Inventory Stock Check
```

**Benefits**:
- Easy to find later
- Quick context recall
- Professional documentation

---

## FAQ

### Q: Can I save my queries for reuse?
**A**: Yes! Copy the SQL from history, or save the conversation. Both are automatically saved.

### Q: What if I make a mistake in the database?
**A**: Brainplug is read-only by default (SELECT only). To enable INSERT/UPDATE/DELETE, ask your administrator.

### Q: Can I query multiple databases in one conversation?
**A**: No, only 1 active database at a time. Switch through Settings if needed.

### Q: How much history is kept?
**A**: All conversations are kept permanently unless you delete them manually. No auto-purge.

### Q: Can I share conversations with colleagues?
**A**: Future feature coming. Currently: Export as CSV or screenshot the messages.

### Q: What if the system suggests wrong SQL multiple times?
**A**: This means the database schema might be incorrect. Check RAG Schema and [Rebuild] if needed.

### Q: Is my data secure?
**A**: 
- ✅ Database credentials stored securely in RAG only
- ✅ Query results not stored permanently
- ✅ Conversation history is local
- ✅ No data sent to Brainplug servers (open source)

### Q: Can I use this offline?
**A**: For local databases (SQLite) yes. For cloud APIs (Gemini, Claude), you need internet.

### Q: What's the difference between Gemini and Claude?
**A**: Both work similarly. Gemini is faster, Claude is more thoughtful. System tries Gemini first, falls back to Claude.

### Q: Why did my conversation clear?
**A**: You clicked [Clear Context] or [New Chat]. To undo: Check conversation list in sidebar, might be saved there.

### Q: Can I modify the LLM prompts?
**A**: Not through UI currently. Contact administrator if customization needed.

### Q: How do I add a new database type?
**A**: Contact your developer. Currently supports MySQL, PostgreSQL, SQLite, MariaDB.

---

## Support & Escalation

### Level 1: Self-Service

**Try These First**:
1. ✅ Check [Troubleshooting](#troubleshooting) section above
2. ✅ Review [Best Practices](#best-practices) section
3. ✅ Check RAG Schema (Settings → RAG Schema)
4. ✅ Rebuild schema if needed
5. ✅ Try with different LLM

### Level 2: Team Support

**If Above Doesn't Work**:
- Contact your team's support channel
- Include:
  - ✅ Error message (full text)
  - ✅ What you were asking
  - ✅ What you expected
  - ✅ What actually happened
  - ✅ Screenshot if possible

**Provide**:
```
Title: "Database query error in production_db"

Details:
- Database: production_db
- Query: "Show me active customers"
- Error: "Table not found"
- Expected: List of 150+ customers
- Actual: Error message
- Screenshot: [attached]
```

### Level 3: Administrator/Developer

**When to Escalate**:
- [ ] Try Level 1 & 2
- [ ] Issue involves database configuration
- [ ] Issue involves LLM configuration
- [ ] Need system changes
- [ ] Performance issues across users

**What They Might Check**:
- Database logs
- Brainplug application logs
- RAG database integrity
- API key validity
- Server resources

### Quick Feedback
- **Bug found?** Report it immediately
- **Feature request?** Add to backlog discussion
- **Performance issue?** Note the time so we can check logs

### Emergency Contact

For production outages:
```
1. Check application URL - can you access it?
   └─ If no: Server down, contact DevOps
2. Can you log in?
   └─ If no: Check credentials, try new browser
3. Can you reach Chat view?
   └─ If no: Application error, check logs
4. Can you connect to database?
   └─ If no: Database down, check DB status
5. Still broken? Contact support with details above
```

---

## Appendix: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift+Enter` | New line in message |
| `Ctrl+K` | Clear input |
| `Escape` | Cancel edit mode |
| `Ctrl+L` | Clear conversation |
| `Ctrl+N` | New chat |
| `Ctrl+S` | (Future) Save query |
| `Ctrl+E` | (Future) Export results |

## Common Command Patterns

### Asking Questions

| Pattern | Example |
|---------|---------|
| **List all** | "Show me all customers" |
| **Filter by** | "Show me customers from California" |
| **Count** | "How many orders in 2024?" |
| **Top/Bottom** | "Show me top 10 products by revenue" |
| **Join tables** | "Show me customers and their orders" |
| **Aggregate** | "What's the total revenue by category?" |
| **Compare** | "Compare sales 2023 vs 2024" |
| **Trend** | "Show me sales by month" |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | Feb 2026 | RAG consolidation, SQL validation |
| 1.5 | Jan 2026 | Conversation memory improvements |
| 1.0 | Dec 2025 | Initial release |

---

**Status**: ✅ Updated for Version 2.0
**Last Reviewed**: February 2026
**Next Review**: August 2026

For detailed technical information, see [KEY_DEVELOPER_REFERENCE_GUIDE.md](KEY_DEVELOPER_REFERENCE_GUIDE.md)

For application architecture, see [KEY_APP_FEATURES_AND_ARCHITECTURE.md](KEY_APP_FEATURES_AND_ARCHITECTURE.md)
