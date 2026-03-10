"""
Main Flask application for Gemini-like MCP system.
Handles routing, request processing, and orchestration of services.
"""
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.services.action_service import ActionService
from backend.services.settings_service import SettingsService
from backend.utils.database import DatabaseConnector
import sqlalchemy as sa
from sqlalchemy.exc import OperationalError as SAOperationalError
import pymysql
from backend.models import db, init_db
from backend.models.rag import RAGItem
from backend.utils.logger import setup_logger
from backend.services.settings_service import SettingsService

load_dotenv()
logger = setup_logger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
# The app uses TWO separate databases:
# 1. APP DATABASE: SQLite for storing conversations, messages (local app state)
# 2. CONNECTED DATABASE: User's database (MySQL/PostgreSQL) - for schema discovery and data queries
# 
# Settings are stored EXCLUSIVELY in RAG Vector Database, NOT in either SQL database.

# Ensure instance directory exists for SQLite database
instance_dir = Path(__file__).parent / 'instance'
instance_dir.mkdir(parents=True, exist_ok=True)

# App database - use SQLite stored in instance directory
db_path = instance_dir / 'app.db'
app_db_url = f'sqlite:///{db_path.as_posix()}'
app.config['SQLALCHEMY_DATABASE_URI'] = app_db_url
logger.info(f"Database URL: {app_db_url}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JSON_SORT_KEYS'] = False

# Connected database info (for schema discovery only) - stored as settings in RAG
# This is NOT used for SQLAlchemy ORM anymore
db_url = os.getenv('DATABASE_URL', '').strip()
# Note: Connected database URL is handled by SettingsService in RAG
# It's NOT used in SQLAlchemy configuration anymore

# Initialize database
db.init_app(app)
with app.app_context():
    init_db()

# Initialize services (LLMService will be re-initialized after Ollama probe)
rag_service = RAGService()
action_service = ActionService()
settings_service = SettingsService()
llm_service = None  # Will be initialized after Ollama probe

# Simple Ollama auto-initialization on first startup (not on reloader)
werkzeug_run_main = os.environ.get('WERKZEUG_RUN_MAIN')
logger.info(f"Startup: WERKZEUG_RUN_MAIN = {werkzeug_run_main}")
if werkzeug_run_main != 'true':
    logger.info("Probing for local Ollama daemon...")
    try:
        import requests as req
        # Probe for Ollama and register in RAG database
        def try_probe_ollama(host, endpoints):
            """Try to probe Ollama at given host and return model list if found."""
            for endpoint in endpoints:
                try:
                    resp = req.get(f"{host}{endpoint}", timeout=1)
                    if resp.status_code != 200:
                        continue
                    
                    data = resp.json()
                    models = []
                    
                    if isinstance(data, list):
                        models = [str(m) for m in data]
                    elif isinstance(data, dict):
                        if 'models' in data and isinstance(data['models'], list):
                            models = [m.get('name', str(m)) if isinstance(m, dict) else str(m) for m in data['models']]
                        elif 'tags' in data and isinstance(data['tags'], list):
                            models = [str(t) for t in data['tags']]
                    
                    return models
                except Exception:
                    continue
            return []
        
        # Probe common Ollama hosts
        hosts = ['http://localhost:11434', 'http://127.0.0.1:11434']
        endpoints = ['/api/tags', '/models', '/api/models']
        mistral_model = None
        mistral_host = None
        
        for host in hosts:
            if mistral_model:
                break
            models = try_probe_ollama(host, endpoints)
            for m in models:
                if 'mistral' in str(m).lower():
                    mistral_model = m
                    mistral_host = host
                    break
        
        if mistral_model and mistral_host:
            logger.info(f"Found Mistral: {mistral_model} @ {mistral_host}")
            
            # Register in RAG database (not SQL)
            existing_models = settings_service.get_llm_settings()
            existing = next((m for m in existing_models if m.get('model_type') == 'ollama' and m.get('model_id') == mistral_model), None)
            if not existing:
                settings_service.update_llm_settings({
                    'name': f"Local Mistral ({mistral_model})",
                    'model_type': 'ollama',
                    'model_id': mistral_model,
                    'api_endpoint': mistral_host,
                    'is_active': True,
                    'priority': 0
                })
                logger.info(f"[OK] Auto-created Mistral LLM model in RAG with priority=0")
            else:
                logger.info(f"[OK] Mistral model already exists in RAG")
        else:
            logger.info("No Ollama/Mistral found - will use configured cloud LLM")
    except Exception as e:
        logger.error(f"Ollama init error: {str(e)}")

# Initialize LLMService
with app.app_context():
    try:
        llm_service = LLMService()
        logger.info("✓ LLMService initialized from RAG database")
    except Exception as e:
        logger.error(f"Error initializing LLMService: {e}")
        llm_service = None

# =====================================================================
# CHAT & CONVERSATION ENDPOINTS
# =====================================================================

@app.route('/api/chat/message', methods=['POST'])
def chat_message():
    """
    Receive a natural language prompt, classify action type, retrieve RAG context,
    and send to LLM for response and action suggestion.
    """
    try:
        # Check if LLM service is initialized
        if llm_service is None:
            return jsonify({'error': 'LLM service not initialized. Please configure an LLM model in Settings.'}), 503
        
        data = request.json
        user_message = data.get('message', '')
        conversation_id = data.get('conversation_id')
        
        if not user_message:
            return jsonify({'error': 'Message is required'}), 400
        
        # Load conversation memory for context
        from backend.utils.conversation_memory import ConversationMemory
        memory = ConversationMemory(conversation_id) if conversation_id else None
        
        # Get RAG context
        rag_context = rag_service.retrieve_context(
            user_message,
            top_k=5
        )
        
        # Get mandatory business rules
        business_rules = rag_service.get_mandatory_rules()
        
        # Process with LLM (now with conversation memory)
        response = llm_service.process_prompt(
            prompt=user_message,
            rag_context=rag_context,
            business_rules=business_rules,
            conversation_id=conversation_id
        )
        
        return jsonify({
            'success': True,
            'data': response
        }), 200
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/confirm-action', methods=['POST'])
def confirm_action():
    """Confirm and execute an action."""
    try:
        data = request.json
        action = data.get('action', {})
        
        # Log raw action before normalization
        logger.info(f"confirm_action received: {action}")
        
        # Execute the action through action_service (which now normalizes)
        result = action_service.execute_action(action)
        
        logger.info(f"Action executed successfully: {result}")
        return jsonify({'status': 'success', 'result': result}), 200
    
    except Exception as e:
        logger.error(f"Error confirming action: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/conversations', methods=['GET'])
def get_conversations():
    """Get all conversations history."""
    try:
        from backend.models.conversation import Conversation
        conversations = Conversation.query.order_by(
            Conversation.created_at.desc()
        ).all()
        
        return jsonify({
            'success': True,
            'data': [c.to_dict() for c in conversations]
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching conversations: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['GET'])
def get_conversation(conversation_id):
    """Get specific conversation with all messages."""
    try:
        from backend.models.conversation import Conversation
        # Use Session.get to avoid SQLAlchemy 2.0 Query.get deprecation warning
        conversation = db.session.get(Conversation, conversation_id)
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        return jsonify({
            'success': True,
            'data': conversation.to_dict(include_messages=True)
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
def delete_conversation(conversation_id):
    """Delete a conversation."""
    try:
        from backend.models.conversation import Conversation
        conversation = db.session.get(Conversation, conversation_id)
        
        if not conversation:
            return jsonify({'error': 'Conversation not found'}), 404
        
        db.session.delete(conversation)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Conversation deleted'
        }), 200
    
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =====================================================================
# SETTINGS ENDPOINTS
# =====================================================================

@app.route('/api/settings/database', methods=['GET', 'POST'])
def database_settings():
    """
    Get or update database connection settings.
    
    AUTO-RAG GENERATION:
    - When a database is marked as ACTIVE (is_active=True), automatic RAG generation happens immediately
    - All tables from the database are scanned and converted to RAG schema items
    - Relationships and sample data are auto-generated as business rules
    - When switching to a new database, old database RAG items are automatically cleared
    - Only ONE database's RAG can be active at a time
    
    POST body should include:
    {
        "id": "uuid (optional, for update)",
        "name": "Database Name",
        "db_type": "mysql|postgres|sqlite",
        "host": "localhost",
        "port": 3306,
        "database": "db_name",
        "username": "user",
        "password": "pass",
        "is_active": true (set to true to trigger auto-RAG generation)
    }
    """
    try:
        if request.method == 'DELETE':
            # Support DELETE with id in JSON body for clients that don't use URL param
            data = request.json or {}
            setting_id = data.get('id')
            logger.info(f"Received DELETE /api/settings/database with id={setting_id}")
            if not setting_id:
                return jsonify({'error': 'id is required for DELETE'}), 400
            settings_service.delete_database_setting(setting_id)
            return jsonify({'success': True, 'message': 'Database setting deleted'}), 200
        elif request.method == 'POST':
            settings_data = request.json
            result = settings_service.update_database_settings(settings_data)
            return jsonify({'success': True, 'data': result}), 200
        else:
                # GET: return only entries that represent actual database connections
                try:
                    settings = settings_service.get_database_settings() or []
                    # Defensive filter in case RAG store contains non-db entries
                    db_only = [s for s in settings if s.get('db_type')]
                    logger.info(f"GET /api/settings/database: returning {len(db_only)} database settings (raw returned {len(settings)})")
                    return jsonify({'success': True, 'data': db_only}), 200
                except Exception as e:
                    logger.error(f"Error fetching database settings for GET: {str(e)}")
                    return jsonify({'success': True, 'data': []}), 200
    
    except Exception as e:
        logger.error(f"Error in database settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/database/<setting_id>', methods=['DELETE'])
def delete_database_setting(setting_id):
    """Delete a database connection setting."""
    try:
        logger.info(f"Deleting database setting: {setting_id}")
        settings_service.delete_database_setting(setting_id)
        logger.info(f"✓ Successfully deleted database setting: {setting_id}")
        return jsonify({'success': True, 'message': 'Database setting deleted'}), 200
    except Exception as e:
        logger.error(f"Error deleting database setting: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/database/discover-tables', methods=['POST'])
def discover_tables():
    """Discover tables from a connected database."""
    try:
        data = request.json or {}
        database_id = data.get('database_id')
        
        if not database_id:
            return jsonify({'error': 'database_id is required'}), 400
        
        # Get the database setting from RAG
        all_settings = settings_service.get_database_settings() or []
        db_setting = next((s for s in all_settings if s.get('id') == database_id), None)
        
        if not db_setting:
            return jsonify({'error': 'Database setting not found'}), 404
        
        # Build connection string
        connection_string = settings_service._build_connection_string(db_setting)
        
        # Get schema from database
        db_connector = DatabaseConnector()
        schema = db_connector.get_schema(connection_string)
        
        # Transform to frontend format with foreign keys and indexes
        discovered_tables = []
        for table in schema.get('tables', []):
            # Extract foreign key information
            foreign_keys = []
            for fk in table.get('foreign_keys', []):
                foreign_keys.append({
                    'column': fk.get('constrained_columns', [''])[0] if fk.get('constrained_columns') else '',
                    'references_table': fk.get('referred_table', ''),
                    'references_column': fk.get('referred_columns', [''])[0] if fk.get('referred_columns') else ''
                })
            
            # Get indexes by checking column constraints and primary keys
            indexes = []
            primary_keys = table.get('primary_keys', [])
            if primary_keys:
                indexes.append({
                    'name': 'PRIMARY KEY',
                    'columns': primary_keys,
                    'type': 'primary'
                })
            
            discovered_tables.append({
                'name': table.get('table_name'),
                'columns': [col.get('name') for col in table.get('columns', [])],
                'query_template': f"SELECT * FROM {table.get('table_name')}",
                'sample_count': 3,
                'foreign_keys': foreign_keys,
                'indexes': indexes,
                'primary_keys': primary_keys
            })
        
        logger.info(f"✓ Discovered {len(discovered_tables)} tables from database {database_id}")
        return jsonify({'success': True, 'data': discovered_tables}), 200
    
    except Exception as e:
        logger.error(f"Error discovering tables: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/database/table-relationships', methods=['POST'])
def get_table_relationships():
    """Get foreign key relationships for a specific table."""
    try:
        data = request.json or {}
        database_id = data.get('database_id')
        table_name = data.get('table_name')
        
        if not database_id or not table_name:
            return jsonify({'error': 'database_id and table_name are required'}), 400
        
        # Get the database setting from RAG
        all_settings = settings_service.get_database_settings() or []
        db_setting = next((s for s in all_settings if s.get('id') == database_id), None)
        
        if not db_setting:
            return jsonify({'error': 'Database setting not found'}), 404
        
        # Build connection string
        connection_string = settings_service._build_connection_string(db_setting)
        
        # Get schema from database
        db_connector = DatabaseConnector()
        schema = db_connector.get_schema(connection_string)
        
        # Find relationships for this table
        relationships = {
            'table': table_name,
            'referenced_by': [],  # Tables that reference this table
            'references': [],      # Tables this table references
            'all_tables': []       # All table names for building WHERE conditions
        }
        
        # Get all table names
        relationships['all_tables'] = [t.get('table_name') for t in schema.get('tables', [])]
        
        # Find the current table
        current_table = None
        for table in schema.get('tables', []):
            if table.get('table_name') == table_name:
                current_table = table
                break
        
        if not current_table:
            return jsonify({'error': f'Table {table_name} not found'}), 404
        
        # Find tables this table references (outgoing relationships)
        for fk in current_table.get('foreign_keys', []):
            references_table = fk.get('referred_table')
            if references_table:
                column = fk.get('constrained_columns', [''])[0] if fk.get('constrained_columns') else ''
                referred_column = fk.get('referred_columns', [''])[0] if fk.get('referred_columns') else ''
                relationships['references'].append({
                    'table': references_table,
                    'local_column': column,
                    'remote_column': referred_column
                })
        
        # Find tables that reference this table (incoming relationships)
        for table in schema.get('tables', []):
            for fk in table.get('foreign_keys', []):
                if fk.get('referred_table') == table_name:
                    local_table = table.get('table_name')
                    column = fk.get('constrained_columns', [''])[0] if fk.get('constrained_columns') else ''
                    referred_column = fk.get('referred_columns', [''])[0] if fk.get('referred_columns') else ''
                    relationships['referenced_by'].append({
                        'table': local_table,
                        'local_column': column,
                        'remote_column': referred_column
                    })
        
        logger.info(f"✓ Found relationships for table {table_name}: {len(relationships['references'])} references + {len(relationships['referenced_by'])} referenced_by")
        return jsonify({'success': True, 'data': relationships}), 200
    
    except Exception as e:
        logger.error(f"Error getting table relationships: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/ingest/config', methods=['POST'])
def configure_table_ingestion():
    """
    Configure ingestion for specific tables.
    
    Accepts configuration with processing method (raw or semantic) and related table settings.
    """
    try:
        data = request.json or {}
        database_id = data.get('database_id')
        tables_config = data.get('tables', [])  # List of table configs
        processing_method = data.get('processing_method', 'semantic')  # 'raw' or 'semantic'
        
        if not database_id or not tables_config:
            return jsonify({'error': 'database_id and tables are required'}), 400
        
        # Store ingestion configuration in RAG
        config = {
            'database_id': database_id,
            'processing_method': processing_method,
            'tables': tables_config,
            'created_at': datetime.now().isoformat(),
            'status': 'configured'
        }
        
        # Save to settings service or RAG database
        config_id = str(uuid.uuid4())
        settings_service.rag_db.save_setting(
            f"ingest_config_{config_id}",
            {
                'id': config_id,
                'database_id': database_id,
                'config': config,
                'meta_type': 'ingestion_config'
            }
        )
        
        logger.info(f"✓ Configured ingestion for {len(tables_config)} tables in database {database_id}")
        return jsonify({
            'success': True,
            'config_id': config_id,
            'tables_configured': len(tables_config)
        }), 200
    
    except Exception as e:
        logger.error(f"Error configuring ingestion: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/ingest/start', methods=['POST'])
def start_table_ingestion():
    """
    Start data ingestion from configured tables.
    
    Pulls data from source, detects relationships, generates embeddings, stores raw data.
    """
    try:
        from backend.services.ingestion_pipeline import IngestionPipeline
        
        data = request.json or {}
        database_id = data.get('database_id')
        table_names = data.get('tables', [])
        config_id = data.get('config_id')
        
        if not database_id:
            return jsonify({'error': 'database_id is required'}), 400
        
        # Get database setting
        all_settings = settings_service.get_database_settings() or []
        db_setting = next((s for s in all_settings if s.get('id') == database_id), None)
        
        if not db_setting:
            return jsonify({'error': 'Database setting not found'}), 404
        
        # Get ingestion config if provided
        ingest_config = {}
        if config_id:
            try:
                ingest_config = settings_service.rag_db.get_setting(f"ingest_config_{config_id}")
            except:
                pass
        
        # Initialize ingestion pipeline
        pipeline = IngestionPipeline()
        results = []
        
        # Ingest each table
        for table_name in table_names:
            try:
                table_config = next(
                    (t for t in ingest_config.get('config', {}).get('tables', []) 
                     if t.get('name') == table_name),
                    {'name': table_name, 'columns': [], 'query_template': f"SELECT * FROM {table_name}"}
                )
                
                processing_method = ingest_config.get('config', {}).get('processing_method', 'semantic')
                
                # Use extended ingestion method
                result = pipeline.ingest_table_with_processing(
                    db_setting,
                    table_config,
                    embeddings_method=processing_method
                )
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error ingesting table {table_name}: {e}")
                results.append({
                    'status': 'error',
                    'table': table_name,
                    'message': str(e)
                })
        
        # Summary
        successful = sum(1 for r in results if r.get('status') == 'success')
        total_records = sum(r.get('records_ingested', 0) for r in results)
        total_embeddings = sum(r.get('embeddings_generated', 0) for r in results)
        
        logger.info(f"✓ Ingestion complete: {successful}/{len(results)} tables, {total_records} records, {total_embeddings} embeddings")
        
        return jsonify({
            'success': True,
            'status': 'completed',
            'tables_processed': len(results),
            'successful_tables': successful,
            'total_records': total_records,
            'total_embeddings': total_embeddings,
            'details': results
        }), 200
    
    except Exception as e:
        logger.error(f"Error starting ingestion: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/ingest/delete/<database_id>', methods=['DELETE'])
def delete_ingested_data(database_id):
    """Delete all ingested data for a database."""
    try:
        settings_service.rag_db._delete_ingested_data_for_database(database_id)
        logger.info(f"✓ Deleted all ingested data for database {database_id}")
        return jsonify({'success': True, 'message': 'Ingested data deleted'}), 200
    except Exception as e:
        logger.error(f"Error deleting ingested data: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/ingest/manual', methods=['POST'])
def manual_ingest_trigger():
    """Manually trigger ingestion for all configured tables in a database."""
    try:
        data = request.json or {}
        database_id = data.get('database_id')
        
        if not database_id:
            return jsonify({'error': 'database_id is required'}), 400
        
        # Get the database setting from RAG
        from backend.services.ingestion_pipeline import IngestionPipeline
        
        all_settings = settings_service.get_database_settings() or []
        db_setting = next((s for s in all_settings if s.get('id') == database_id), None)
        
        if not db_setting:
            return jsonify({'error': 'Database setting not found'}), 404
        
        # Initialize ingestion pipeline
        pipeline = IngestionPipeline()
        
        # Ingest all selected tables for this database
        result = pipeline.ingest_database(db_setting)
        
        logger.info(f"✓ Manual ingestion completed for database {database_id}")
        return jsonify({'success': True, 'data': result}), 200
        
    except Exception as e:
        logger.error(f"Error in manual ingestion: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/ingest/status', methods=['POST'])
def ingest_status():
    """Get status of ingested data for a database."""
    try:
        data = request.json or {}
        database_id = data.get('database_id')
        
        if not database_id:
            return jsonify({'error': 'database_id is required'}), 400
        
        # Try to get ingestion status from RAG
        try:
            status = settings_service.rag_db.get_database_setting(f'ingest_status_{database_id}')
            if status:
                return jsonify({
                    'success': True,
                    'data': status
                }), 200
        except:
            pass
        
        # Alternative: check filesystem for ingested data
        import os
        import json
        from pathlib import Path
        
        ingested_dir = Path('instance/ingested_data') / database_id
        ingested_data = {
            'database_id': database_id,
            'total_records': 0,
            'tables_ingested': 0,
            'ingested_tables': [],
            'storage_path': str(ingested_dir),
            'exists': ingested_dir.exists(),
            'sample_embeddings': [],
            'sample_rules': []
        }
        
        if ingested_dir.exists():
            for file in ingested_dir.glob('*_records.json'):
                try:
                    with open(file, 'r') as f:
                        records = json.load(f)
                    table_name = file.stem.replace('_records', '')
                    record_count = len(records) if isinstance(records, list) else 1
                    ingested_data['total_records'] += record_count
                    ingested_data['tables_ingested'] += 1
                    ingested_data['ingested_tables'].append({
                        'name': table_name,
                        'records_ingested': record_count,
                        'file': file.name
                    })
                    
                    # Collect first few records as sample embeddings
                    if isinstance(records, list) and len(ingested_data['sample_embeddings']) < 3:
                        for record in records[:3]:
                            if isinstance(record, dict):
                                sample_item = {
                                    'id': f"{table_name}_{record.get('id', 'unknown')}",
                                    'content': json.dumps(record)[:100],
                                    'table': table_name
                                }
                                ingested_data['sample_embeddings'].append(sample_item)
                except:
                    pass
        
        # Get sample rules with embeddings from rules.json
        try:
            rules_file = Path('instance/rag_db/rules.json')
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    rules = json.load(f)
                
                # Filter rules for this database and get sample embeddings
                db_rules = [r for r in rules if database_id in r.get('id', '')]
                for rule in db_rules[:3]:  # Get first 3
                    rule_sample = {
                        'id': rule.get('id', 'unknown')[:50],
                        'content': rule.get('content', '')[:150],
                        'has_embedding': rule.get('embedding') is not None,
                        'embedding_dims': len(rule.get('embedding', [])) if rule.get('embedding') else 0
                    }
                    ingested_data['sample_rules'].append(rule_sample)
        except:
            pass
        
        # Get last ingestion time if available
        timestamp_file = ingested_dir / 'last_ingestion.txt'
        if timestamp_file.exists():
            try:
                with open(timestamp_file, 'r') as f:
                    ingested_data['last_ingestion'] = f.read().strip()
            except:
                pass
        
        return jsonify({
            'success': True,
            'data': ingested_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting ingestion status: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/llm', methods=['GET', 'POST'])
def get_llm_settings():
    """Get all LLM models, or create/update an LLM model."""
    try:
        if request.method == 'POST':
            # Create or update LLM model
            settings_data = request.json
            try:
                result = settings_service.update_llm_settings(settings_data)
                logger.info(f"✓ POST /api/settings/llm: Model {result.get('name')} {'updated' if settings_data.get('id') else 'created'}")
            except SAOperationalError as oe:
                # SQLAlchemy OperationalError (DB auth/connection problem)
                logger.error(f"Database operational error while updating LLM settings: {str(oe)}", exc_info=True)
                hint = (
                    "Database authentication/connection failed.\n"
                    "Check your `DATABASE_URL` or set `DB_PASSWORD` / `DATABASE_PASSWORD` in your .env.\n"
                    "Example: DATABASE_URL='mysql+pymysql://root:YOUR_PASS@localhost:3306/iventory'\n"
                    "Or set: DB_PASSWORD='YOUR_PASS' and restart the app."
                )
                return jsonify({'status': 'error', 'message': 'Database connection failed', 'details': str(oe), 'hint': hint}), 503
            except pymysql.err.OperationalError as pe:
                # Raw pymysql operational error
                logger.error(f"pymysql OperationalError while updating LLM settings: {str(pe)}", exc_info=True)
                hint = (
                    "Database authentication failed (pymysql).\n"
                    "Ensure your DB credentials are correct and `DB_PASSWORD` is set if your DATABASE_URL has no password."
                )
                return jsonify({'status': 'error', 'message': 'Database authentication failed', 'details': str(pe), 'hint': hint}), 503


            # Refresh the global llm_service so changes take effect immediately
            try:
                if llm_service:
                    llm_service._ensure_active_model()
                    logger.info("✓ llm_service refreshed after LLM settings update")
            except Exception as e:
                logger.error(f"Error refreshing llm_service after LLM settings update: {str(e)}")
            return jsonify({
                'status': 'success',
                'data': result
            }), 200
        else:
            # GET: Return all LLM models from RAG settings store
            try:
                llms = settings_service.get_llm_settings() or []
                active = next((m for m in llms if m.get('is_active')), None)
                logger.info(f"✓ GET /api/settings/llm: {len(llms)} models | Active: {active.get('name') if active else 'NONE'}")
                return jsonify({'status': 'success', 'data': llms, 'active_model': {'id': active.get('id'), 'name': active.get('name'), 'model_type': active.get('model_type')} if active else None}), 200
            except Exception as e:
                logger.error(f"Error reading LLM settings from RAG: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)}), 500
    except Exception as e:
        logger.error(f"Error in get_llm_settings: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Internal server error', 'details': str(e)}), 500


@app.route('/api/settings/llm/<model_id>', methods=['DELETE'])
def delete_llm_model(model_id):
    """Delete an LLM model from RAG database."""
    try:
        settings_service = SettingsService()
        deleted = settings_service.delete_llm_model(model_id)
        if deleted:
            return jsonify({'success': True, 'message': 'Model deleted from RAG'}), 200
        else:
            return jsonify({'success': False, 'message': 'Model not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting LLM model: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/llm/ollama/models', methods=['GET'])
def ollama_models():
    """Probe local Ollama Daemon and list available models."""
    try:
        host = request.args.get('host', 'http://localhost:11434')
        result = settings_service.list_local_ollama_models(host=host)
        # result is a dict: {models: [...], host: 'http://..', errors: [...]}
        models = result.get('models', []) if isinstance(result, dict) else result
        if isinstance(result, dict) and result.get('models'):
            return jsonify({'success': True, 'data': result}), 200
        else:
            # return diagnostics so frontend can show useful info
            return jsonify({'success': False, 'message': 'No local Ollama models found', 'diagnostics': result}), 200
    except Exception as e:
        logger.error(f"Error probing Ollama: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/llm/ollama/test', methods=['POST'])
def ollama_test():
    """Run a diagnostic test against the local Ollama host/model and return raw responses."""
    try:
        data = request.json or {}
        # Prefer explicit host/model from request body, fall back to active LLM
        host = data.get('host')
        model = data.get('model')

        # If not provided, ask llm_service to refresh and use its configured host/model
        try:
            if llm_service:
                llm_service._ensure_active_model()
                if not host:
                    host = getattr(llm_service, 'ollama_host', None)
                if not model:
                    model = getattr(llm_service, 'ollama_model', None)
        except Exception:
            pass

        if not host:
            return jsonify({'success': False, 'message': 'No host provided and no active Ollama host found'}), 400

        import requests as _requests
        endpoints = ['/api/generate', '/api/completions', '/chat', '/api/chat']
        payloads = [
            {'model': model, 'prompt': 'Say hello from diagnostic test', 'stream': False},
            {'model': model, 'messages': [{'role': 'user', 'content': 'Say hello from diagnostic test'}], 'stream': False}
        ]

        results = []
        host_clean = host.rstrip('/')
        for ep in endpoints:
            url = f"{host_clean}{ep}"
            for pl in payloads:
                try:
                    resp = _requests.post(url, json=pl, timeout=15)
                    body = None
                    try:
                        body = resp.json()
                    except Exception:
                        body = resp.text

                    results.append({
                        'endpoint': url,
                        'payload_keys': list(pl.keys()),
                        'status_code': resp.status_code,
                        'body_preview': str(body)[:800],
                        'headers': dict(resp.headers)
                    })
                except Exception as e:
                    results.append({'endpoint': url, 'payload_keys': list(pl.keys()), 'error': str(e)})

        return jsonify({'success': True, 'host': host, 'model': model, 'results': results}), 200
    except Exception as e:
        logger.error(f"Error running Ollama diagnostic test: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings/rag', methods=['GET', 'POST'])
def rag_settings():
    """Get or update RAG settings."""
    try:
        if request.method == 'POST':
            settings_data = request.json
            result = settings_service.update_rag_settings(settings_data)
            return jsonify({'success': True, 'data': result}), 200
        else:
            settings = settings_service.get_rag_settings()
            return jsonify({'success': True, 'data': settings}), 200
    
    except Exception as e:
        logger.error(f"Error in RAG settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/system', methods=['GET', 'POST'])
def system_settings():
    """Get or update system settings (SMTP, IMAP, POP)."""
    try:
        if request.method == 'POST':
            settings_data = request.json
            result = settings_service.update_system_settings(settings_data)
            return jsonify({'success': True, 'data': result}), 200
        else:
            settings = settings_service.get_system_settings()
            return jsonify({'success': True, 'data': settings}), 200
    
    except Exception as e:
        logger.error(f"Error in system settings: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/api-configs', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_configs():
    """Manage API configurations."""
    try:
        if request.method == 'POST':
            config_data = request.json
            result = settings_service.create_api_config(config_data)
            return jsonify({'success': True, 'data': result}), 201
        elif request.method == 'PUT':
            config_id = request.json.get('id')
            config_data = request.json
            result = settings_service.update_api_config(config_id, config_data)
            return jsonify({'success': True, 'data': result}), 200
        elif request.method == 'DELETE':
            config_id = request.json.get('id')
            settings_service.delete_api_config(config_id)
            return jsonify({'success': True, 'message': 'Config deleted'}), 200
        else:
            configs = settings_service.get_api_configs()
            return jsonify({'success': True, 'data': configs}), 200
    
    except Exception as e:
        logger.error(f"Error managing API configs: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/scheduled-activities', methods=['GET', 'POST'])
def scheduled_activities():
    """Get or create scheduled activities."""
    try:
        if request.method == 'POST':
            activity_data = request.json
            result = action_service.schedule_activity(activity_data)
            return jsonify({'success': True, 'data': result}), 201
        else:
            activities = action_service.get_scheduled_activities()
            return jsonify({'success': True, 'data': activities}), 200
    
    except Exception as e:
        logger.error(f"Error managing scheduled activities: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/settings/scheduled-activities/<activity_id>', methods=['PUT', 'DELETE'])
def manage_scheduled_activity(activity_id):
    """Update or delete a scheduled activity."""
    try:
        if request.method == 'PUT':
            activity_data = request.json
            result = action_service.update_scheduled_activity(activity_id, activity_data)
            return jsonify({'success': True, 'data': result}), 200
        else:
            action_service.delete_scheduled_activity(activity_id)
            return jsonify({'success': True, 'message': 'Activity deleted'}), 200
    
    except Exception as e:
        logger.error(f"Error managing scheduled activity: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =====================================================================
# REPORTS ENDPOINTS
# =====================================================================

@app.route('/api/reports', methods=['GET', 'POST'])
def reports():
    """Get all reports or create a new report."""
    try:
        if request.method == 'POST':
            report_data = request.json
            result = action_service.generate_report(report_data)
            return jsonify({'success': True, 'data': result}), 201
        else:
            reports_list = action_service.get_reports()
            return jsonify({'success': True, 'data': reports_list}), 200
    
    except Exception as e:
        logger.error(f"Error managing reports: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/<report_id>', methods=['GET', 'DELETE'])
def get_report(report_id):
    """Get specific report or delete it."""
    try:
        if request.method == 'DELETE':
            action_service.delete_report(report_id)
            return jsonify({'success': True, 'message': 'Report deleted'}), 200
        else:
            report = action_service.get_report(report_id)
            if not report:
                return jsonify({'error': 'Report not found'}), 404
            return jsonify({'success': True, 'data': report}), 200
    
    except Exception as e:
        logger.error(f"Error managing report: {str(e)}")
        return jsonify({'error': str(e)}), 500


# =====================================================================
# RAG MANAGEMENT ENDPOINTS
# =====================================================================

@app.route('/api/rag/schema', methods=['GET', 'POST'])
def rag_schema():
    """Get or update RAG database schema."""
    try:
        if request.method == 'POST':
            schema_data = request.json
            result = rag_service.update_schema(schema_data)
            return jsonify({'success': True, 'data': result}), 200
        else:
            # Get schemas from RAG database (ChromaDB), not from database table
            schema = settings_service.get_rag_schemas()
            return jsonify({'success': True, 'data': schema}), 200
    
    except Exception as e:
        logger.error(f"Error managing RAG schema: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/rag/business-rules', methods=['GET', 'POST'])
def business_rules_list():
    """Get all business rules from ChromaDB or create a new one."""
    try:
        if request.method == 'POST':
            # Manual rule creation (stored in ChromaDB)
            rule_data = request.json
            active_db = settings_service.get_active_database()
            
            if not active_db:
                return jsonify({'status': 'error', 'message': 'No active database'}), 400
            
            result = settings_service.rag_db.add_business_rule(
                rule_name=rule_data.get('name'),
                rule_content=rule_data.get('content'),
                db_id=active_db['id'],
                rule_type=rule_data.get('rule_type', 'optional'),
                category=rule_data.get('category')
            )
            
            if result:
                logger.info(f"✓ Created business rule: {rule_data.get('name')}")
                return jsonify({'status': 'success', 'message': 'Rule created'}), 201
            else:
                return jsonify({'status': 'error', 'message': 'Failed to create rule'}), 500
        else:
            rules = settings_service.get_business_rules()
            logger.info(f"✓ GET /api/rag/business-rules: {len(rules)} rules from ChromaDB")
            return jsonify({'status': 'success', 'data': rules}), 200
    
    except Exception as e:
        logger.error(f"Error managing business rules: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/rag/business-rules/<rule_id>', methods=['GET', 'PUT', 'DELETE'])
def business_rules_detail(rule_id):
    """Get, update, or delete a specific business rule from ChromaDB."""
    try:
        if request.method == 'GET':
            rules = settings_service.get_business_rules()
            rule = next((r for r in rules if r.get('id') == rule_id), None)
            if not rule:
                return jsonify({'status': 'error', 'message': 'Rule not found'}), 404
            return jsonify({'status': 'success', 'data': rule}), 200
        
        elif request.method == 'PUT':
            # Update business rule
            updates = request.json or {}
            rule_content = updates.get('content', '')
            rule_name = updates.get('name', '')
            
            if not rule_content:
                return jsonify({'status': 'error', 'message': 'content is required'}), 400
            
            success = settings_service.rag_db.update_rule(
                rule_id=rule_id,
                rule_content=rule_content,
                rule_name=rule_name if rule_name else None
            )
            
            if success:
                logger.info(f"✓ Updated business rule: {rule_id}")
                # Fetch and return the updated rule
                rules = settings_service.get_business_rules()
                rule = next((r for r in rules if r.get('id') == rule_id), None)
                return jsonify({'status': 'success', 'data': rule, 'message': 'Rule updated'}), 200
            else:
                return jsonify({'status': 'error', 'message': 'Failed to update rule'}), 500
        
        elif request.method == 'DELETE':
            settings_service.rag_db.delete_rule(rule_id)
            logger.info(f"✓ Deleted business rule: {rule_id}")
            return jsonify({'status': 'success', 'message': 'Rule deleted'}), 200
    
    except Exception as e:
        logger.error(f"Error managing business rule {rule_id}: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =====================================================================
# HEALTH CHECK
# =====================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with RAG vector database status."""
    try:
        # Check RAG database health
        rag_health = settings_service.rag_db.health_check()
        db_count = len(settings_service.get_database_settings())
        rag_schemas = len(settings_service.get_rag_schemas())
        rag_rules = len(settings_service.get_business_rules())
        
        logger.info(f"✓ Health Check: RAG Schemas={rag_schemas}, Business Rules={rag_rules}")
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'database_settings': db_count,
            'rag_schemas': rag_schemas,
            'rag_rules': rag_rules,
            'rag_health': rag_health
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/rag/populate', methods=['POST'])
def populate_rag():
    """
    Manually populate RAG with database schema (usually automatic).
    
    NOTE: RAG population happens AUTOMATICALLY when you:
    1. Create a new database connection with is_active=True, OR
    2. Update an existing database to is_active=True
    
    This endpoint is a FALLBACK for manual RAG re-population if needed.
    
    POST body should include:
    {
        "database_id": "uuid of the database"
    }
    """
    try:
        database_id = request.json.get('database_id')
        if not database_id:
            return jsonify({'status': 'error', 'message': 'database_id required'}), 400
        
        # Get database setting from settings service (now using ChromaDB)
        db_settings = settings_service.get_database_settings()
        db_setting = next((s for s in db_settings if s.get('id') == database_id), None)
        
        if not db_setting:
            logger.warning(f"Database setting not found: {database_id}")
            return jsonify({'status': 'error', 'message': 'Database not found'}), 404
        
        logger.info(f"→ MANUAL: Populating RAG for database: {db_setting.get('name')}")
        
        # Use settings_service to populate RAG (which calls _populate_rag_schema)
        settings_service._populate_rag_schema(db_setting)
        
        logger.info(f"✓ RAG populated for database: {db_setting.get('name')}")
        
        return jsonify({
            'status': 'success',
            'message': f"RAG populated for {db_setting.get('name')}"
        }), 200
    
    except Exception as e:
        logger.error(f"Error populating RAG: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/rag/items', methods=['GET'])
def get_rag_items():
    """Get all RAG schemas from ChromaDB (not database)."""
    try:
        schemas = settings_service.get_rag_schemas()
        
        data = [{
            'id': schema['id'],
            'category': schema['metadata'].get('category', schema['metadata'].get('table_name', '')),
            'title': schema['metadata'].get('table_name', ''),
            'content': schema['content'],
            'type': schema['metadata'].get('type', 'schema'),
        } for schema in schemas]
        
        logger.info(f"✓ GET /api/rag/items: {len(data)} schemas from ChromaDB")
        
        return jsonify({
            'status': 'success',
            'data': data
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching RAG items: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/rag/items', methods=['POST'])
def create_rag_item():
    """Create a new RAG item."""
    try:
        data = request.json
        
        item = RAGItem(
            id=str(uuid.uuid4()),
            category=data.get('category', 'custom'),
            title=data.get('title'),
            content=data.get('content'),
            source=data.get('source', 'manual'),
        )
        db.session.add(item)
        db.session.commit()
        
        # Add to vector store
        rag_service.add_item(item)
        
        logger.info(f"✓ Created RAG item: {item.title}")
        
        return jsonify({
            'status': 'success',
            'data': {
                'id': item.id,
                'category': item.category,
                'title': item.title,
            }
        }), 201
    
    except Exception as e:
        logger.error(f"Error creating RAG item: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/rag/items/<item_id>', methods=['PUT'])
def update_rag_item(item_id):
    """Update a RAG item."""
    try:
        item = RAGItem.query.get(item_id)
        if not item:
            return jsonify({'status': 'error', 'message': 'Item not found'}), 404
        
        data = request.json
        item.category = data.get('category', item.category)
        item.title = data.get('title', item.title)
        item.content = data.get('content', item.content)
        item.source = data.get('source', item.source)
        
        db.session.commit()
        
        # Re-index in vector store
        rag_service.update_item(item)
        
        logger.info(f"✓ Updated RAG item: {item.title}")
        
        return jsonify({
            'status': 'success',
            'data': {'id': item.id}
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating RAG item: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/rag/items/<item_id>', methods=['DELETE'])
def delete_rag_item(item_id):
    """Delete a RAG item."""
    try:
        item = RAGItem.query.get(item_id)
        if not item:
            return jsonify({'status': 'error', 'message': 'Item not found'}), 404
        
        rag_service.remove_item(item_id)
        
        db.session.delete(item)
        db.session.commit()
        
        logger.info(f"✓ Deleted RAG item: {item_id}")
        
        return jsonify({'status': 'success'}), 200
    
    except Exception as e:
        logger.error(f"Error deleting RAG item: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =====================================================================
# DBMS EXPLORER ENDPOINTS
# =====================================================================

@app.route('/api/dbms/databases', methods=['GET'])
def get_dbms_databases():
    """Get all connected databases for explorer."""
    try:
        databases = settings_service.get_database_settings()
        
        data = [{
            'id': db['id'],
            'name': db['name'],
            'db_type': db['db_type'],
            'host': db['host'],
            'database': db['database'],
            'is_active': db.get('is_active', False)
        } for db in databases]
        
        logger.info(f"✓ GET /api/dbms/databases: {len(data)} databases")
        return jsonify({'status': 'success', 'data': data}), 200
    
    except Exception as e:
        logger.error(f"Error fetching DBMS databases: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/dbms/tables/<database_id>', methods=['GET'])
def get_dbms_tables(database_id):
    """Get all tables from a specific database."""
    try:
        db_setting = settings_service.rag_db.get_database_setting(database_id)
        if not db_setting:
            return jsonify({'status': 'error', 'message': 'Database not found'}), 404
        
        connection_string = settings_service._build_connection_string(db_setting)
        schema_data = settings_service.db_connector.get_schema(connection_string)
        tables = schema_data.get('tables', [])
        
        data = [{
            'name': t['table_name'],
            'column_count': len(t.get('columns', [])),
            'has_primary_key': len(t.get('primary_keys', [])) > 0,
            'has_foreign_keys': len(t.get('foreign_keys', [])) > 0
        } for t in tables]
        
        logger.info(f"✓ GET /api/dbms/tables/{database_id}: {len(data)} tables")
        return jsonify({'status': 'success', 'data': data}), 200
    
    except Exception as e:
        logger.error(f"Error fetching DBMS tables: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/dbms/table-data/<database_id>/<table_name>', methods=['GET'])
def get_dbms_table_data(database_id, table_name):
    """Get table data with pagination."""
    try:
        db_setting = settings_service.rag_db.get_database_setting(database_id)
        if not db_setting:
            return jsonify({'status': 'error', 'message': 'Database not found'}), 404
        
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        offset = (page - 1) * limit
        
        connection_string = settings_service._build_connection_string(db_setting)
        engine = __import__('sqlalchemy').create_engine(connection_string)
        
        with engine.connect() as conn:
            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM {table_name}"
            result = conn.execute(__import__('sqlalchemy').text(count_query))
            total_count = result.scalar()
            
            # Get paginated data
            data_query = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
            result = conn.execute(__import__('sqlalchemy').text(data_query))
            rows = [dict(row._mapping) for row in result]
        
        logger.info(f"✓ GET /api/dbms/table-data/{database_id}/{table_name}: page {page}")
        return jsonify({
            'status': 'success',
            'data': rows,
            'total_count': total_count,
            'page': page,
            'limit': limit,
            'total_pages': (total_count + limit - 1) // limit
        }), 200
    
    except Exception as e:
        logger.error(f"Error fetching table data: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/dbms/table-schema/<database_id>/<table_name>', methods=['GET'])
def get_dbms_table_schema(database_id, table_name):
    """Get complete table schema with indexes, keys, and relationships."""
    try:
        db_setting = settings_service.rag_db.get_database_setting(database_id)
        if not db_setting:
            return jsonify({'status': 'error', 'message': 'Database not found'}), 404
        
        connection_string = settings_service._build_connection_string(db_setting)
        schema_data = settings_service.db_connector.get_schema(connection_string)
        tables = schema_data.get('tables', [])
        
        table_schema = next((t for t in tables if t['table_name'] == table_name), None)
        if not table_schema:
            return jsonify({'status': 'error', 'message': 'Table not found'}), 404
        
        response = {
            'name': table_schema['table_name'],
            'columns': table_schema.get('columns', []),
            'primary_keys': table_schema.get('primary_keys', []),
            'foreign_keys': table_schema.get('foreign_keys', []),
            'indexes': []  # Add index retrieval if needed
        }
        
        logger.info(f"✓ GET /api/dbms/table-schema/{database_id}/{table_name}")
        return jsonify({'status': 'success', 'data': response}), 200
    
    except Exception as e:
        logger.error(f"Error fetching table schema: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =====================================================================
# DATA SOURCES ENDPOINTS
# =====================================================================

@app.route('/api/data-sources', methods=['GET', 'POST'])
def data_sources():
    """Get all data sources or create a new one."""
    try:
        if request.method == 'POST':
            data = request.json
            # Save data source
            data_source = {
                'id': str(__import__('uuid').uuid4()),
                'name': data.get('name'),
                'type': data.get('type'),  # 'database', 'api', 'file', etc.
                'description': data.get('description'),
                'source_config': data.get('source_config', {}),
                'is_active': data.get('is_active', True),
                'created_at': datetime.now().isoformat()
            }
            settings_service.rag_db.save_setting(f"data_source_{data_source['id']}", data_source)
            logger.info(f"✓ Created data source: {data_source['name']}")
            return jsonify({'status': 'success', 'data': data_source}), 201
        else:
            # Get all data sources
            all_settings = settings_service.rag_db.get_all_database_settings()
            data_sources_list = [{
                'id': s['id'],
                'name': s['name'],
                'type': 'database',
                'db_type': s.get('db_type'),
                'is_active': s.get('is_active', False)
            } for s in all_settings]
            
            logger.info(f"✓ GET /api/data-sources: {len(data_sources_list)} sources")
            return jsonify({'status': 'success', 'data': data_sources_list}), 200
    
    except Exception as e:
        logger.error(f"Error managing data sources: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =====================================================================
# DATABASE WIDE SEARCH
# =====================================================================


@app.route('/api/search/databases', methods=['GET'])
@app.route('/search/databases', methods=['GET'])
@app.route('/api/search', methods=['GET'])
@app.route('/search', methods=['GET'])
def search_databases():
    """Search across all active database connections for a query string.

    This endpoint iterates over active database settings, retrieves table
    schemas, and performs a conservative LIKE-based search across text-like
    columns. It includes basic limits to avoid long-running queries and also
    performs a best-effort scan of configured data sources saved in the RAG
    settings store.
    """
    try:
        q = request.args.get('q', '').strip()
        if not q:
            return jsonify({'status': 'error', 'message': 'q (query) parameter is required'}), 400

        max_tables_per_db = 10
        max_rows_per_table = 10
        overall_result_limit = 200

        results = []
        diagnostics = {'databases_checked': 0, 'db_diagnostics': []}
        databases = settings_service.get_database_settings()
        active_dbs = [d for d in databases if d.get('is_active')]
        diagnostics['databases_checked'] = len(active_dbs)

        for db_setting in active_dbs:
            if len(results) >= overall_result_limit:
                break

            db_id = db_setting.get('id')
            db_name = db_setting.get('name')
            db_diag = {'database_id': db_id, 'database_name': db_name, 'tables_checked': 0, 'errors': []}
            try:
                conn_str = settings_service._build_connection_string(db_setting)
                schema = settings_service.db_connector.get_schema(conn_str)
                tables = schema.get('tables', [])[:max_tables_per_db]
                db_diag['tables_checked'] = len(tables)

                engine = __import__('sqlalchemy').create_engine(conn_str)

                for table in tables:
                    if len(results) >= overall_result_limit:
                        break

                    table_name = table.get('table_name')

                    # choose only text-like columns to avoid casting numeric/binary types
                    text_like = []
                    for c in table.get('columns', []):
                        col_name = c.get('name') or c.get('column_name')
                        col_type = (c.get('type') or '').upper()
                        if not col_name:
                            continue
                        if any(t in col_type for t in ('CHAR', 'TEXT', 'VARCHAR', 'STRING')):
                            text_like.append(col_name)

                    # Fallback: if no text-like columns detected, use all columns but be cautious
                    columns = text_like if text_like else [c.get('name') or c.get('column_name') for c in table.get('columns', [])]
                    columns = [c for c in columns if c]
                    if not columns:
                        continue

                    # Build a WHERE clause that checks selected columns by casting to a dialect-appropriate text type
                    dialect_name = getattr(engine.dialect, 'name', '').lower()
                    if dialect_name in ('mysql', 'mariadb'):
                        cast_type = 'CHAR'
                    elif dialect_name in ('mssql', 'microsoft'):
                        cast_type = 'NVARCHAR(MAX)'
                    else:
                        # postgres, sqlite and others support TEXT
                        cast_type = 'TEXT'

                    where_clauses = [f"CAST({col} AS {cast_type}) LIKE :q" for col in columns]
                    where_sql = ' OR '.join(where_clauses)
                    query_sql = f"SELECT * FROM {table_name} WHERE {where_sql} LIMIT {max_rows_per_table}"

                    try:
                        with engine.connect() as conn:
                            res = conn.execute(__import__('sqlalchemy').text(query_sql), {'q': f"%{q}%"})
                            rows = [dict(r._mapping) for r in res]

                        for row in rows:
                            # Determine which columns matched for lightweight metadata
                            matched = [col for col in columns if row.get(col) is not None and q.lower() in str(row.get(col)).lower()]
                            results.append({
                                'database_id': db_id,
                                'database_name': db_name,
                                'table': table_name,
                                'row': row,
                                'matched_columns': matched,
                            })

                            if len(results) >= overall_result_limit:
                                break
                    except Exception as e:
                        msg = f"Search query failed for {db_name}.{table_name}: {str(e)}"
                        logger.debug(msg)
                        db_diag['errors'].append(msg)
                        continue

            except Exception as e:
                msg = f"Could not search database {db_name}: {str(e)}"
                logger.debug(msg)
                db_diag['errors'].append(msg)
                diagnostics['db_diagnostics'].append(db_diag)
                continue
            diagnostics['db_diagnostics'].append(db_diag)

        # Also search configured data sources stored in RAG DB settings (names and descriptions)
        try:
            all_settings = settings_service.rag_db.get_all_database_settings()
            for s in all_settings:
                if len(results) >= overall_result_limit:
                    break
                sid = s.get('id') or ''
                # data source records are saved with keys like 'data_source_<id>'
                if sid.startswith('data_source_') or s.get('type') == 'database' or s.get('type') == 'file':
                    # check name and description
                    name = (s.get('name') or '')
                    desc = (s.get('description') or '')
                    if q.lower() in name.lower() or q.lower() in desc.lower():
                        results.append({
                            'database_id': s.get('id'),
                            'database_name': s.get('name') or s.get('id'),
                            'table': None,
                            'row': {'source': s},
                            'matched_columns': ['name' if q.lower() in name.lower() else 'description']
                        })
        except Exception:
            # best effort; ignore errors here
            pass

        return jsonify({'status': 'success', 'query': q, 'count': len(results), 'results': results, 'diagnostics': diagnostics}), 200

    except Exception as e:
        logger.error(f"Error in database-wide search: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': str(e)}), 500


# =====================================================================
# APIs ENDPOINTS
# =====================================================================

@app.route('/api/api-configs-list', methods=['GET', 'POST'])
def api_configs_list():
    """Get all API configurations or create a new one."""
    try:
        if request.method == 'POST':
            config_data = request.json
            api_config = {
                'id': str(__import__('uuid').uuid4()),
                'name': config_data.get('name'),
                'endpoint': config_data.get('endpoint'),
                'method': config_data.get('method', 'GET'),
                'auth_type': config_data.get('auth_type'),  # 'bearer', 'api_key', 'basic', etc.
                'headers': config_data.get('headers', {}),
                'params_template': config_data.get('params_template', {}),
                'description': config_data.get('description'),
                'is_active': config_data.get('is_active', True),
                'created_at': datetime.now().isoformat()
            }
            settings_service.rag_db.save_setting(f"api_config_{api_config['id']}", api_config)
            logger.info(f"✓ Created API config: {api_config['name']}")
            return jsonify({'status': 'success', 'data': api_config}), 201
        else:
            # Get all API configs
            configs = settings_service.get_api_configs()
            logger.info(f"✓ GET /api/api-configs-list: {len(configs)} configs")
            return jsonify({'status': 'success', 'data': configs}), 200
    
    except Exception as e:
        logger.error(f"Error managing API configs: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
