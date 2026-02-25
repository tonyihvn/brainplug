"""
Settings service for managing ALL application settings in RAG Vector Database ONLY.

ARCHITECTURE:
- ALL settings (LLM, Database, RAG, System) are stored EXCLUSIVELY in RAG Vector Database
- SQL/MySQL/PostgreSQL databases are used ONLY for:
  - Schema extraction
  - Sample data acquisition  
  - Business rule generation (relationships, constraints)
- No settings are stored in SQL databases
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from dotenv import set_key
from sqlalchemy.exc import OperationalError as SAOperationalError

from backend.utils.database import DatabaseConnector
from backend.utils.rag_database import RAGDatabase
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class SettingsService:
    """Central service for managing all application settings in RAG Vector Database only."""
    
    def __init__(self):
        """Initialize the settings service."""
        self.db_connector = DatabaseConnector()
        self.rag_db = RAGDatabase()
        self.env_path = Path(__file__).parent.parent.parent / '.env'
        logger.info("SettingsService initialized - using RAG Vector Database ONLY for settings")
    
    # ============================================================================
    # DATABASE SETTINGS (stored in RAG only)
    # ============================================================================
    
    def get_active_database(self):
        """Get the currently active database setting from RAG database."""
        try:
            all_settings = self.rag_db.get_all_database_settings() or []
            db_settings = [s for s in all_settings if s.get('db_type')]
            active = next((s for s in db_settings if s.get('is_active')), None)
            if active:
                logger.info(f"[OK] Active database: {active.get('name')}")
            return active
        except Exception as e:
            logger.error(f"Error getting active database: {str(e)}")
            return None
    
    def get_all_active_databases(self):
        """Get all active database settings."""
        try:
            all_settings = self.rag_db.get_all_database_settings() or []
            active_dbs = [s for s in all_settings if s.get('is_active') and s.get('db_type')]
            logger.info(f"[OK] Retrieved {len(active_dbs)} active databases from RAG")
            return active_dbs
        except Exception as e:
            logger.error(f"Error getting active databases: {str(e)}")
            return []
    
    def get_database_settings(self):
        """Get ALL database settings (active and inactive) from RAG only."""
        try:
            all_settings = self.rag_db.get_all_database_settings() or []
            # Filter to only database settings (have db_type)
            db_settings = [s for s in all_settings if s.get('db_type')]
            logger.info(f"[OK] Retrieved {len(db_settings)} database settings from RAG")
            return db_settings
        except Exception as e:
            logger.error(f"Error getting database settings: {str(e)}")
            return []
    
    def _build_connection_string(self, database_setting):
        """Build a SQLAlchemy connection string from database settings."""
        db_type = database_setting.get('db_type', 'mysql')
        host = database_setting.get('host', 'localhost')
        port = database_setting.get('port', 3306)
        database = database_setting.get('database', 'iventory')
        username = database_setting.get('username', 'root')
        password = database_setting.get('password', '')
        
        if db_type.lower() == 'mysql' or db_type.lower() == 'mariadb':
            driver = 'mysql+pymysql'
            if password:
                return f"{driver}://{username}:{password}@{host}:{port}/{database}"
            else:
                return f"{driver}://{username}@{host}:{port}/{database}"
        elif db_type.lower() == 'postgres':
            driver = 'postgresql'
            if password:
                return f"{driver}://{username}:{password}@{host}:{port}/{database}"
            else:
                return f"{driver}://{username}@{host}:{port}/{database}"
        else:
            return f"sqlite:///{database}.db"
    
    def update_database_settings(self, settings_data):
        """
        Create or update database settings in RAG Vector Database ONLY.
        
        This database setting is used to:
        1. Connect and extract schema
        2. Extract sample data
        3. Generate business rules
        """
        try:
            # Test connection first
            connection_string = self._build_connection_string(settings_data)
            self.db_connector.test_connection(connection_string)
            
            existing_id = settings_data.get('id')
            
            if existing_id:
                # Update existing
                existing = self.rag_db.get_database_setting(existing_id)
                if not existing:
                    raise ValueError("Database setting not found")
                
                was_active = existing.get('is_active', False)
                is_now_active = settings_data.get('is_active', False)
                
                updated = self.rag_db.save_database_setting(
                    existing_id,
                    {**existing, **{k: v for k, v in settings_data.items() if k != 'id'}}
                )
                
                # If transitioning from inactive to active, populate RAG
                if not was_active and is_now_active:
                    logger.info(f"Database {settings_data['name']} activated - extracting schema and rules")
                    self._populate_rag_schema(updated)
                    
                    # Update .env file with new DATABASE_URL
                    try:
                        new_url = self._build_connection_string(updated)
                        set_key(str(self.env_path), 'DATABASE_URL', new_url)
                        logger.info(f"[OK] Updated .env DATABASE_URL for {settings_data['name']}")
                    except Exception as e:
                        logger.error(f"Error updating .env DATABASE_URL: {str(e)}", exc_info=True)
                
                # If transitioning from active to inactive, wipe RAG entries
                elif was_active and not is_now_active:
                    logger.info(f"Database {settings_data['name']} deactivated - clearing schema from RAG")
                    self._wipe_rag_schema(existing_id)
                
                logger.info(f"[OK] Updated database setting in RAG: {settings_data['name']}")
                return updated
            else:
                # Create new
                new_id = str(uuid.uuid4())
                new_setting = {
                    'id': new_id,
                    'name': settings_data['name'],
                    'db_type': settings_data['db_type'],
                    'host': settings_data.get('host'),
                    'port': settings_data.get('port'),
                    'database': settings_data['database'],
                    'username': settings_data.get('username'),
                    'password': settings_data.get('password'),
                    'is_active': settings_data.get('is_active', False),
                    'created_at': datetime.now().isoformat()
                }
                
                self.rag_db.save_database_setting(new_id, new_setting)
                
                # If this is active, populate RAG immediately
                if new_setting['is_active']:
                    logger.info(f"New database {new_setting['name']} is active - extracting schema and rules")
                    self._populate_rag_schema(new_setting)
                    
                    # Update .env file with new DATABASE_URL
                    try:
                        new_url = self._build_connection_string(new_setting)
                        set_key(str(self.env_path), 'DATABASE_URL', new_url)
                        logger.info(f"[OK] Updated .env DATABASE_URL for new database {new_setting['name']}")
                    except Exception as e:
                        logger.error(f"Error updating .env DATABASE_URL: {str(e)}", exc_info=True)
                
                logger.info(f"[OK] Created new database setting in RAG: {new_setting['name']}")
                return new_setting
        
        except Exception as e:
            logger.error(f"Error updating database settings: {str(e)}", exc_info=True)
            raise
    
    def _populate_rag_schema(self, database_setting):
        """
        Populate RAG with database schema and business rules.
        
        When a database is connected:
        1. Extract schema from connected database
        2. Create schema entries in RAG
        3. Create business rules (relationships, sample data)
        
        Note: The connected database is used ONLY for this extraction.
        All settings and business rules are stored in RAG.
        """
        try:
            logger.info(f"=== Starting schema extraction for database: {database_setting['name']} ===")
            
            # Get schema from database
            connection_string = self._build_connection_string(database_setting)
            logger.info(f"Extracting schema from: {database_setting['db_type']}://{database_setting['host']}/{database_setting['database']}")
            
            try:
                schema_data = self.db_connector.get_schema(connection_string)
                tables = schema_data.get('tables', [])
                logger.info(f"[OK] Extracted schema with {len(tables)} tables")
            except Exception as e:
                logger.error(f"[FAIL] Failed to extract schema: {str(e)}", exc_info=True)
                raise
            
            db_id = database_setting['id']
            schemas_added = 0
            rules_added = 0
            
            if tables:
                for table in tables:
                    table_name = table.get('table_name', '')
                    columns = table.get('columns', [])
                    
                    # Build schema content
                    try:
                        # Map columns with foreign keys
                        fk_map = {}
                        for fk in table.get('foreign_keys', []) or []:
                            referred = fk.get('referred_table') or ''
                            for col_name in fk.get('constrained_columns', []) or []:
                                fk_map.setdefault(col_name, set()).add(referred)

                        field_descriptions = []
                        for col in columns:
                            col_name = col.get('name')
                            if not col_name:
                                continue
                            col_type = col.get('type') or col.get('data_type') or ''
                            nullable = col.get('nullable')
                            nullable_str = ', nullable' if nullable else ''
                            default = col.get('default')
                            default_str = f", default={default}" if default is not None else ''
                            related = ''
                            if col_name in fk_map:
                                related_tables = ','.join(sorted([t for t in fk_map[col_name] if t]))
                                if related_tables:
                                    related = f" [{related_tables}]"
                            type_part = f" ({col_type}{nullable_str}{default_str})" if col_type or nullable or default is not None else ''
                            field_descriptions.append(f"  - {col_name}{type_part}{related}")

                        field_lines = "\n".join(field_descriptions)
                        schema_content = f"Table: {table_name}\n\nColumns:\n{field_lines}\n"

                        # Add primary key info if present
                        if table.get('primary_keys'):
                            schema_content += f"\nPrimary Key: {', '.join(table['primary_keys'])}"

                        # Add schema to RAG
                        if self.rag_db.add_schema(table_name=table_name, schema_content=schema_content, db_id=db_id):
                            schemas_added += 1
                            logger.info(f"  [OK] Schema added for {table_name}")
                    except Exception as e:
                        logger.warning(f"  [FAIL] Error adding schema for {table_name}: {e}")
                    
                    # Create business rules: relationships and sample data
                    try:
                        category = f"{db_id}_{table_name}"

                        # Relationships rule
                        fk_entries = table.get('foreign_keys', []) or []
                        if fk_entries:
                            rel_lines = []
                            for fk in fk_entries:
                                constrained = ', '.join(fk.get('constrained_columns', []))
                                referred = fk.get('referred_table', '')
                                referred_cols = ', '.join(fk.get('referred_columns', []) or [])
                                if referred_cols:
                                    rel_lines.append(f"- {constrained} -> {referred}({referred_cols})")
                                else:
                                    rel_lines.append(f"- {constrained} -> {referred}")

                            rel_content = f"Database: {database_setting.get('name')}\nTable: {table_name}\n\nRelationships:\n{chr(10).join(rel_lines)}\n\nNote: Auto-generated from foreign key inspection."
                            rel_name = f"{database_setting.get('name')}_{table_name}_relationships"
                            if self.rag_db.add_business_rule(rule_name=rel_name, rule_content=rel_content, db_id=db_id, rule_type="optional", category=category, meta_type="relationship"):
                                rules_added += 1
                                logger.info(f"  [OK] Relationship rule added for {table_name}")

                        # Sample data rule
                        try:
                            sample_lines_table = []
                            for col in columns:
                                col_name = col.get('name')
                                sample_values = (col.get('sample_values') or [])
                                if sample_values and col_name:
                                    sv = str(sample_values[0])
                                    if len(sv) > 50:
                                        sv = sv[:47] + '...'
                                    sample_lines_table.append(f"{col_name}: {sv}")

                            if sample_lines_table:
                                sample_content_parts = [f"Database: {database_setting.get('name')}", f"Table: {table_name}", ""]
                                sample_content_parts.append("Sample Values (per column, up to 1 each):")
                                sample_content_parts.extend([f"- {s}" for s in sample_lines_table])
                                sample_content_parts.append("")
                                sample_content_parts.append("Note: Auto-captured sample values (values truncated to 50 chars)")
                                sample_content = "\n".join(sample_content_parts)
                                sample_name = f"{database_setting.get('name')}_{table_name}_sample_data"
                                if self.rag_db.add_business_rule(rule_name=sample_name, rule_content=sample_content, db_id=db_id, rule_type="optional", category=category, meta_type="sample_data"):
                                    rules_added += 1
                                    logger.info(f"  [OK] Sample data rule added for {table_name}")
                        except Exception:
                            logger.debug(f"  [FAIL] Could not build sample-data rule for {table_name}")

                    except Exception as e:
                        logger.warning(f"  [FAIL] Error adding rule(s) for {table_name}: {e}")
            
            health = self.rag_db.health_check()
            
            logger.info(f"=== Schema extraction completed ===")
            logger.info(f"Summary: Schemas: {schemas_added}, Business Rules: {rules_added}")
            logger.info(f"RAG Database Health: {health}")
        
        except Exception as e:
            logger.error(f"[FAIL] Error extracting schema: {str(e)}", exc_info=True)
            raise
    
    def _wipe_rag_schema(self, database_id: str):
        """Remove RAG entries for a specific database when it's deactivated."""
        try:
            logger.info(f"Wiping RAG entries for database: {database_id}")
            
            # Remove schemas for this database
            schemas = self.rag_db.get_all_schemas() or []
            for schema in schemas:
                if schema.get('db_id') == database_id:
                    self.rag_db.delete_schema(schema.get('id'))
            
            # Remove business rules for this database
            rules = self.rag_db.get_all_rules() or []
            for rule in rules:
                if rule.get('db_id') == database_id:
                    self.rag_db.delete_rule(rule.get('id'))
            
            logger.info(f"[OK] Wiped RAG entries for database: {database_id}")
        except Exception as e:
            logger.error(f"Error wiping RAG schema: {str(e)}")
    
    def delete_database_setting(self, setting_id):
        """Delete a database setting from RAG."""
        try:
            self._wipe_rag_schema(setting_id)
            self.rag_db.delete_database_setting(setting_id)
            logger.info(f"[OK] Deleted database setting: {setting_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting database setting: {str(e)}")
            return False
    
    # ============================================================================
    # LLM SETTINGS (stored in RAG only)
    # ============================================================================
    
    def update_llm_settings(self, settings_data):
        """
        Create or update LLM settings in RAG Vector Database ONLY.
        
        ⚠️ IMPORTANT: Settings are saved EXCLUSIVELY to RAG database.
        SQL/MySQL/PostgreSQL databases are used ONLY for:
        - Schema extraction
        - Sample data acquisition
        - Business rule generation
        """
        try:
            model_id = settings_data.get('id') or str(uuid.uuid4())
            
            # Build LLM data record
            llm_data = {
                'id': str(model_id),
                'name': settings_data.get('name'),
                'model_type': settings_data.get('model_type'),
                'model_id': settings_data.get('model_id'),
                'api_key': settings_data.get('api_key', ''),
                'api_endpoint': settings_data.get('api_endpoint', ''),
                'is_active': settings_data.get('is_active', False),
                'priority': settings_data.get('priority', 10),
                'config': settings_data.get('config', {}),
                'created_at': datetime.now().isoformat()
            }
            
            # Save ONLY to RAG database
            self.rag_db.save_setting(str(model_id), llm_data)
            logger.info(f"[OK] Saved LLM model to RAG database: {settings_data.get('name')}")
            
            return llm_data
        except Exception as e:
            logger.error(f"Error updating LLM settings: {str(e)}", exc_info=True)
            raise
    
    def get_llm_settings(self):
        """Get all LLM settings from RAG database ONLY."""
        try:
            all_settings = self.rag_db.get_all_database_settings() or []
            llm_settings = [s for s in all_settings if s.get('model_type')]
            logger.info(f"[OK] Retrieved {len(llm_settings)} LLM models from RAG database")
            return llm_settings
        except Exception as e:
            logger.error(f"Error getting LLM settings: {str(e)}")
            return []
    
    def delete_llm_model(self, model_id):
        """Delete an LLM model from RAG database ONLY."""
        try:
            self.rag_db.delete_database_setting(model_id)
            logger.info(f"[OK] Deleted LLM model from RAG: {model_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting LLM model: {str(e)}")
            return False
    
    # ============================================================================
    # RAG SCHEMAS & BUSINESS RULES
    # ============================================================================
    
    def get_rag_schemas(self):
        """Get all RAG schemas."""
        try:
            schemas = self.rag_db.get_all_schemas() or []
            
            formatted = []
            for schema in schemas:
                formatted.append({
                    'id': schema.get('id'),
                    'table_name': schema.get('table_name'),
                    'content': schema.get('content'),
                    'db_id': schema.get('db_id'),
                    'metadata': schema.get('metadata', {})
                })
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting RAG schemas: {str(e)}")
            return []
    
    def get_business_rules(self):
        """Get all business rules from RAG database."""
        try:
            rules = self.rag_db.get_all_rules() or []
            
            formatted = []
            for rule in rules:
                metadata = rule.get('metadata', {})
                rule_type = metadata.get('type', 'rule')
                
                formatted.append({
                    'id': rule.get('id'),
                    'name': metadata.get('rule_name') or metadata.get('name'),
                    'category': metadata.get('category'),
                    'content': rule.get('content'),
                    'type': rule_type,
                    'rule_type': metadata.get('rule_type'),
                    'metadata': metadata
                })
            
            return formatted
        except Exception as e:
            logger.error(f"Error getting business rules: {str(e)}")
            return []
    
    # ============================================================================
    # SYSTEM SETTINGS
    # ============================================================================
    
    def get_rag_settings(self):
        """Get RAG settings from RAG database."""
        return {'status': 'ok'}
    
    def update_rag_settings(self, settings_data):
        """Update RAG settings in RAG database."""
        return settings_data
    
    def get_system_settings(self):
        """Get system settings from RAG database."""
        return {'status': 'ok'}
    
    def update_system_settings(self, settings_data):
        """Update system settings in RAG database."""
        return settings_data
    
    # ============================================================================
    # API SUPPORT
    # ============================================================================
    
    def list_local_ollama_models(self, host='http://localhost:11434'):
        """List Ollama models available on local machine."""
        try:
            import requests
            endpoints = ['/api/tags', '/models', '/api/models']
            for endpoint in endpoints:
                try:
                    resp = requests.get(f"{host}{endpoint}", timeout=2)
                    if resp.status_code == 200:
                        data = resp.json()
                        models = []
                        if isinstance(data, list):
                            models = [str(m) for m in data]
                        elif isinstance(data, dict) and 'models' in data:
                            models = [m.get('name', str(m)) if isinstance(m, dict) else str(m) for m in data['models']]
                        return models
                except Exception:
                    continue
            return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {str(e)}")
            return []
