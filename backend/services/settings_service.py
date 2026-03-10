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

# Will be imported when needed to avoid circular imports
_ingestion_pipeline = None

def get_ingestion_pipeline():
    """Get or initialize the ingestion pipeline (lazy load to avoid circular imports)."""
    global _ingestion_pipeline
    if _ingestion_pipeline is None:
        from backend.services.ingestion_pipeline import IngestionPipeline
        _ingestion_pipeline = IngestionPipeline()
    return _ingestion_pipeline


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
            for setting in db_settings:
                logger.debug(f"  └─ {setting.get('name')}: query_mode={setting.get('query_mode', 'NOT SET')}, is_active={setting.get('is_active')}")
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
        elif db_type.lower() == 'postgres' or db_type.lower() == 'postgresql':
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
        
        AUTO-RAG GENERATION:
        - When a database is marked as ACTIVE:
          1. Clear RAG records from any previously active database
          2. Immediately extract and populate RAG with current database schema
          3. All tables are auto-converted to RAG items
          4. Relationships and sample data are auto-generated as business rules
        
        IMPORTANT RULES:
        - Only ONE database's RAG can be active at any time
        - When switching databases, old RAG entries are automatically cleared
        - All settings, schemas, rules are stored in RAG Vector Database ONLY
        - Connected databases are used ONLY for schema extraction
        """
        try:
            # Normalize port to integer if provided
            if settings_data.get('port'):
                try:
                    settings_data['port'] = int(settings_data['port'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid port value: {settings_data.get('port')}, skipping")
            
            # Test connection first
            connection_string = self._build_connection_string(settings_data)
            self.db_connector.test_connection(connection_string)
            logger.info(f"✓ Database connection successful: {settings_data.get('name')}")
            logger.info(f"[DB-CONNECT] Settings: name={settings_data.get('name')}, query_mode={settings_data.get('query_mode', 'direct')}, is_active={settings_data.get('is_active')}")
            
            existing_id = settings_data.get('id')
            
            if existing_id:
                # Update existing
                existing = self.rag_db.get_database_setting(existing_id)
                if not existing:
                    raise ValueError("Database setting not found")
                
                logger.info(f"[EDIT-DB] Existing settings: query_mode={existing.get('query_mode', 'NOT SET')}, is_active={existing.get('is_active')}")
                logger.info(f"[EDIT-DB] Incoming changes: query_mode={settings_data.get('query_mode', 'NOT PROVIDED')}, is_active={settings_data.get('is_active')}")
                
                was_active = existing.get('is_active', False)
                is_now_active = settings_data.get('is_active', False)
                
                merged = {**existing, **{k: v for k, v in settings_data.items() if k != 'id'}}
                logger.info(f"[EDIT-DB] After merge: query_mode={merged.get('query_mode', 'NOT SET')}, is_active={merged.get('is_active')}")
                
                updated = self.rag_db.save_database_setting(existing_id, merged)
                logger.info(f"[EDIT-DB] Saved to RAG: {merged.get('name')}")
                
                # Verify it was saved correctly
                verify = self.rag_db.get_database_setting(existing_id)
                logger.info(f"[EDIT-DB] Verification after save: query_mode={verify.get('query_mode', 'NOT FOUND')}")
                
                # If transitioning from inactive to active, clear old data and populate RAG
                if not was_active and is_now_active:
                    logger.info(f"[AUTO-RAG] Activating database: {settings_data['name']}")
                    logger.info(f"[AUTO-RAG] Step 1: Finding and clearing old database RAG records...")
                    
                    # Find and deactivate any other active database
                    all_settings = self.rag_db.get_all_database_settings() or []
                    for other_setting in all_settings:
                        if other_setting.get('is_active') and other_setting.get('id') != existing_id:
                            old_db_id = other_setting.get('id')
                            old_db_name = other_setting.get('name')
                            logger.info(f"[AUTO-RAG] Clearing RAG for previous database: {old_db_name}")
                            
                            # Wipe RAG entries for the old database
                            self._wipe_rag_schema(old_db_id)
                            
                            # Deactivate the old database
                            other_setting['is_active'] = False
                            self.rag_db.save_database_setting(old_db_id, other_setting)
                            logger.info(f"[AUTO-RAG] ✓ Cleared and deactivated: {old_db_name}")
                    
                    # Populate RAG with new database schema
                    logger.info(f"[AUTO-RAG] Step 2: Extracting schema from database...")
                    try:
                        rag_stats = self._populate_rag_schema(updated)
                        logger.info(f"[AUTO-RAG] ✓ RAG fully populated for: {settings_data['name']}")
                        
                        # Update .env file with new DATABASE_URL
                        try:
                            new_url = self._build_connection_string(updated)
                            set_key(str(self.env_path), 'DATABASE_URL', new_url)
                            logger.info(f"[AUTO-RAG] ✓ Updated .env DATABASE_URL for {settings_data['name']}")
                        except Exception as e:
                            logger.error(f"Error updating .env DATABASE_URL: {str(e)}", exc_info=True)
                        
                        # Include RAG stats in response
                        updated['rag_statistics'] = rag_stats
                    except Exception as rag_error:
                        logger.error(f"[FAIL] RAG generation error: {str(rag_error)}", exc_info=True)
                        # Still save the database setting, but mark RAG generation as failed
                        updated['rag_statistics'] = {
                            'status': 'failed',
                            'database_name': settings_data.get('name'),
                            'error': str(rag_error),
                            'tables_scanned': 0,
                            'items_created': 0,
                            'mapping': 'Failed',
                            'storage': 'RAG Vector Database (JSON Fallback)'
                        }
                
                # If transitioning from active to inactive, wipe RAG entries
                elif was_active and not is_now_active:
                    logger.info(f"[AUTO-RAG] Deactivating database: {settings_data['name']}")
                    self._wipe_rag_schema(existing_id)
                    logger.info(f"[AUTO-RAG] ✓ RAG cleared for: {settings_data['name']}")
                
                logger.info(f"[OK] Updated database setting in RAG: {settings_data['name']}")
                return updated
            else:
                # Create new
                new_id = str(uuid.uuid4())
                is_active = settings_data.get('is_active', False)
                
                # Include ALL fields from settings_data, not just a hardcoded subset
                new_setting = {
                    'id': new_id,
                    'name': settings_data['name'],
                    'db_type': settings_data['db_type'],
                    'host': settings_data.get('host'),
                    'port': settings_data.get('port'),
                    'database': settings_data['database'],
                    'username': settings_data.get('username'),
                    'password': settings_data.get('password'),
                    'is_active': is_active,
                    'query_mode': settings_data.get('query_mode', 'direct'),  # FIXED: Include query_mode!
                    'selected_tables': settings_data.get('selected_tables', {}),  # FIXED: Include selected tables
                    'sync_interval': settings_data.get('sync_interval', 60),  # FIXED: Include sync interval
                    'created_at': datetime.now().isoformat()
                }
                
                logger.info(f"[NEW-DB] Settings to save: name={new_setting['name']}, query_mode={new_setting.get('query_mode')}, is_active={new_setting.get('is_active')}")
                self.rag_db.save_database_setting(new_id, new_setting)
                logger.info(f"[NEW-DB] Saved to RAG: {new_setting['name']}")
                
                # Verify it was saved correctly
                verify = self.rag_db.get_database_setting(new_id)
                logger.info(f"[NEW-DB] Verification after save: query_mode={verify.get('query_mode', 'NOT FOUND')} (database id={new_id})")
                
                logger.info(f"[AUTO-RAG] Created new database connection: {new_setting['name']} (mode: {new_setting.get('query_mode', 'direct')})")
                
                # If this is active, clear old data and populate RAG immediately
                if is_active:
                    logger.info(f"[AUTO-RAG] Database marked as ACTIVE - auto-generating RAG items...")
                    logger.info(f"[AUTO-RAG] Step 1: Finding and clearing old database RAG records...")
                    
                    # Find and deactivate any currently active database
                    all_settings = self.rag_db.get_all_database_settings() or []
                    for other_setting in all_settings:
                        if other_setting.get('is_active') and other_setting.get('id') != new_id:
                            old_db_id = other_setting.get('id')
                            old_db_name = other_setting.get('name')
                            logger.info(f"[AUTO-RAG] Clearing RAG for previous database: {old_db_name}")
                            
                            # Wipe RAG entries for the old database
                            self._wipe_rag_schema(old_db_id)
                            
                            # Deactivate the old database
                            other_setting['is_active'] = False
                            self.rag_db.save_database_setting(old_db_id, other_setting)
                            logger.info(f"[AUTO-RAG] ✓ Cleared and deactivated: {old_db_name}")
                    
                    # Populate RAG with new database schema
                    logger.info(f"[AUTO-RAG] Step 2: Extracting all tables from database...")
                    try:
                        rag_stats = self._populate_rag_schema(new_setting)
                        logger.info(f"[AUTO-RAG] ✓ RAG fully populated for: {new_setting['name']}")
                        
                        # Update .env file with new DATABASE_URL
                        try:
                            new_url = self._build_connection_string(new_setting)
                            set_key(str(self.env_path), 'DATABASE_URL', new_url)
                            logger.info(f"[AUTO-RAG] ✓ Updated .env DATABASE_URL for {new_setting['name']}")
                        except Exception as e:
                            logger.error(f"Error updating .env DATABASE_URL: {str(e)}", exc_info=True)
                        
                        # Include RAG stats in response
                        new_setting['rag_statistics'] = rag_stats
                    except Exception as rag_error:
                        logger.error(f"[FAIL] RAG generation error: {str(rag_error)}", exc_info=True)
                        # Still save the database setting, but mark RAG generation as failed
                        new_setting['rag_statistics'] = {
                            'status': 'failed',
                            'database_name': new_setting.get('name'),
                            'error': str(rag_error),
                            'tables_scanned': 0,
                            'items_created': 0,
                            'mapping': 'Failed',
                            'storage': 'RAG Vector Database (JSON Fallback)'
                        }
                
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
            logger.info(f"[RAG-POPULATE] Connection string built for: {database_setting['db_type']}://{database_setting.get('host', 'local')}/{database_setting['database']}")
            
            try:
                schema_data = self.db_connector.get_schema(connection_string)
                tables = schema_data.get('tables', [])
                logger.info(f"[RAG-POPULATE] ✓ Extracted schema with {len(tables)} tables")
                if len(tables) == 0:
                    logger.warning(f"[RAG-POPULATE] ⚠️ WARNING: Zero tables found in schema extraction!")
                    logger.warning(f"[RAG-POPULATE]    This could mean: database is empty, schema detection failed, or permission issue")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"[RAG-POPULATE] ✗ Failed to extract schema: {error_msg}", exc_info=True)
                # Check for specific error types
                if 'connection' in error_msg.lower() or 'refused' in error_msg.lower() or 'unreachable' in error_msg.lower():
                    raise Exception(f"Cannot connect to database server: {database_setting['host']}:{database_setting['port']}. Is the database server running?")
                elif 'authentication' in error_msg.lower() or 'access denied' in error_msg.lower():
                    raise Exception(f"Database authentication failed. Check username/password credentials.")
                elif 'unknown database' in error_msg.lower() or 'does not exist' in error_msg.lower():
                    raise Exception(f"Database '{database_setting['database']}' does not exist. Check the database name.")
                else:
                    raise Exception(f"Failed to extract database schema: {error_msg}")
            
            db_id = database_setting['id']
            items_created = 0
            
            logger.info(f"[RAG-POPULATE] Processing {len(tables)} tables for RAG generation...")
            
            if tables:
                for table in tables:
                    table_name = table.get('table_name', '')
                    columns = table.get('columns', [])
                    
                    try:
                        # ═══════════════════════════════════════════════════════════════
                        # BUILD COMPREHENSIVE RAG ITEM (1 per table)
                        # Consolidates: Schema + Relationships + Sample Data + Business Rule
                        # ═══════════════════════════════════════════════════════════════
                        
                        content_parts = [
                            "═" * 65,
                            f"TABLE: {table_name}",
                            f"DATABASE: {database_setting.get('name')}",
                            "═" * 65,
                            ""
                        ]
                        
                        # ───────────────────────────────────────────────────────────────
                        # SECTION 1: SCHEMA DEFINITION
                        # ───────────────────────────────────────────────────────────────
                        content_parts.append("SCHEMA DEFINITION")
                        content_parts.append("─" * 65)
                        
                        # Primary keys
                        if table.get('primary_keys'):
                            pk_list = ', '.join(table['primary_keys'])
                            content_parts.append(f"Primary Key: {pk_list}")
                            content_parts.append("")
                        
                        # Columns with types and nullability
                        content_parts.append("Columns:")
                        fk_map = {}
                        for fk in table.get('foreign_keys', []) or []:
                            referred = fk.get('referred_table') or ''
                            for col_name in fk.get('constrained_columns', []) or []:
                                fk_map.setdefault(col_name, set()).add(referred)
                        
                        for col in columns:
                            col_name = col.get('name')
                            if not col_name:
                                continue
                            col_type = col.get('type') or col.get('data_type') or ''
                            nullable = col.get('nullable')
                            nullable_str = 'nullable=true' if nullable else 'nullable=false'
                            default = col.get('default')
                            default_str = f", default={default}" if default is not None else ""
                            
                            fk_ref = ""
                            if col_name in fk_map:
                                related_tables = ','.join(sorted([t for t in fk_map[col_name] if t]))
                                if related_tables:
                                    fk_ref = f" → references {related_tables}"
                            
                            type_part = f"{col_type}, {nullable_str}{default_str}"
                            content_parts.append(f"  - {col_name}: {type_part}{fk_ref}")
                        
                        content_parts.append("")
                        
                        # ───────────────────────────────────────────────────────────────
                        # SECTION 2: FOREIGN KEY RELATIONSHIPS
                        # ───────────────────────────────────────────────────────────────
                        fk_entries = table.get('foreign_keys', []) or []
                        if fk_entries:
                            content_parts.append("RELATIONSHIPS (Foreign Keys)")
                            content_parts.append("─" * 65)
                            for fk in fk_entries:
                                constrained = ', '.join(fk.get('constrained_columns', []))
                                referred = fk.get('referred_table', '')
                                referred_cols = ', '.join(fk.get('referred_columns', []) or [])
                                if referred_cols:
                                    content_parts.append(f"  {constrained} → {referred}({referred_cols})")
                                else:
                                    content_parts.append(f"  {constrained} → {referred}")
                            content_parts.append("")
                        
                        # ───────────────────────────────────────────────────────────────
                        # SECTION 3: SAMPLE DATA
                        # ───────────────────────────────────────────────────────────────
                        sample_lines = []
                        for col in columns:
                            col_name = col.get('name')
                            sample_values = (col.get('sample_values') or [])
                            if sample_values and col_name:
                                sv = str(sample_values[0])
                                if len(sv) > 50:
                                    sv = sv[:47] + '...'
                                sample_lines.append(f"  {col_name}: {sv}")
                        
                        if sample_lines:
                            content_parts.append("SAMPLE DATA (Example values)")
                            content_parts.append("─" * 65)
                            content_parts.extend(sample_lines)
                            content_parts.append("")
                        
                        # ───────────────────────────────────────────────────────────────
                        # SECTION 4: BUSINESS RULE (Natural Language Explanation)
                        # ───────────────────────────────────────────────────────────────
                        content_parts.append("BUSINESS RULE & USAGE")
                        content_parts.append("─" * 65)
                        
                        # Generate natural language description based on table name and structure
                        business_rule = self._generate_natural_language_rule(table_name, columns, fk_entries)
                        content_parts.append(business_rule)
                        content_parts.append("")
                        
                        # ═══════════════════════════════════════════════════════════════
                        
                        comprehensive_content = "\n".join(content_parts)
                        
                        # Create single consolidated RAG item per table
                        category = f"{db_id}_{table_name}"
                        rule_name = f"{database_setting.get('name')}_{table_name}"
                        
                        if self.rag_db.add_business_rule(
                            rule_name=rule_name,
                            rule_content=comprehensive_content,
                            db_id=db_id,
                            rule_type="mandatory",
                            category=category,
                            meta_type="table_comprehensive"
                        ):
                            items_created += 1
                            logger.info(f"  [OK] Comprehensive RAG item created for {table_name}")
                        else:
                            logger.warning(f"  [FAIL] Could not add comprehensive RAG item for {table_name}")
                    
                    except Exception as e:
                        logger.warning(f"  [FAIL] Error creating comprehensive RAG item for {table_name}: {e}")
            
            health = self.rag_db.health_check()
            
            logger.info(f"════════════════════════════════════════════════════════════════")
            logger.info(f"[AUTO-RAG] RAG GENERATION COMPLETE for: {database_setting.get('name')}")
            logger.info(f"[AUTO-RAG] Tables Scanned: {len(tables)}")
            logger.info(f"[AUTO-RAG] Consolidated RAG Items Created: {items_created}")
            logger.info(f"[AUTO-RAG] Mapping: {items_created} items (1 per table)")
            logger.info(f"[AUTO-RAG] Each item includes: Schema + Relationships + Sample Data + Business Rule")
            logger.info(f"[AUTO-RAG] Storage: RAG Vector Database (JSON Fallback)")
            logger.info(f"════════════════════════════════════════════════════════════════")
            
            # Return statistics for display
            return {
                'status': 'success',
                'database_name': database_setting.get('name'),
                'tables_scanned': len(tables),
                'items_created': items_created,
                'mapping': f"{items_created} items (1 per table)",
                'storage': 'RAG Vector Database (JSON Fallback)'
            }
        
        except Exception as e:
            logger.error(f"[FAIL] Error extracting schema: {str(e)}", exc_info=True)
            raise
    
    def _wipe_rag_schema(self, database_id: str):
        """Remove RAG entries for a specific database when it's deactivated."""
        try:
            logger.info(f"Wiping RAG entries for database: {database_id}")
            
            schemas_deleted = 0
            rules_deleted = 0
            
            # Remove schemas for this database
            schemas = self.rag_db.get_all_schemas() or []
            for schema in schemas:
                # Check both 'db_id' (legacy) and 'database_id' (current)
                schema_metadata = schema.get('metadata', {})
                if schema_metadata.get('database_id') == database_id or schema_metadata.get('db_id') == database_id:
                    if self.rag_db.delete_schema(schema.get('id')):
                        schemas_deleted += 1
            
            # Remove business rules for this database
            rules = self.rag_db.get_all_rules() or []
            for rule in rules:
                # Check both 'db_id' (legacy) and 'database_id' (current)
                rule_metadata = rule.get('metadata', {})
                if rule_metadata.get('database_id') == database_id or rule_metadata.get('db_id') == database_id:
                    if self.rag_db.delete_rule(rule.get('id')):
                        rules_deleted += 1
            
            logger.info(f"[OK] Wiped RAG entries for database: {database_id} (Schemas: {schemas_deleted}, Rules: {rules_deleted})")
        except Exception as e:
            logger.error(f"Error wiping RAG schema: {str(e)}")
    
    def delete_database_setting(self, setting_id):
        """Delete a database setting from RAG with full cascade delete.
        
        This performs complete cleanup:
        - Removes database setting
        - Deletes all associated rules  
        - Deletes all associated schemas
        - Deletes all ingested data
        - Deletes raw data backups and directories
        """
        try:
            logger.info(f"Deleting database setting with cascade cleanup: {setting_id}")
            
            # Use enhanced cascade delete which handles rules, schemas, and ingested data
            self.rag_db.delete_database_setting(setting_id)
            
            logger.info(f"✓ Successfully deleted database setting and all associated data: {setting_id}")
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
    # RAG GENERATION HELPERS
    # ============================================================================
    
    def _generate_natural_language_rule(self, table_name: str, columns: list, foreign_keys: list) -> str:
        """
        Generate natural language business rule explanation for a table.
        This provides context about what the table represents, common queries, etc.
        """
        try:
            rule_parts = []
            
            # Analyze table name to infer purpose
            table_lower = table_name.lower()
            
            # Determine table category based on naming conventions
            category_hints = []
            if any(x in table_lower for x in ['user', 'account', 'person', 'member']):
                category_hints.append('user/account management')
            if any(x in table_lower for x in ['order', 'transaction', 'purchase', 'sale']):
                category_hints.append('order/transaction tracking')
            if any(x in table_lower for x in ['product', 'item', 'catalog', 'inventory', 'stock']):
                category_hints.append('product/inventory management')
            if any(x in table_lower for x in ['payment', 'invoice', 'receipt', 'bill']):
                category_hints.append('financial records')
            if any(x in table_lower for x in ['permission', 'role', 'access', 'auth']):
                category_hints.append('access control and security')
            if any(x in table_lower for x in ['log', 'audit', 'history', 'event']):
                category_hints.append('audit trail and history')
            
            # Build the rule text
            if category_hints:
                category_text = category_hints[0]
                rule_parts.append(f"This table is used for {category_text}. It stores core data related to {table_name.replace('_', ' ')}.")
            else:
                rule_parts.append(f"This table stores information about {table_name.replace('_', ' ')}.")
            
            # Add column information
            column_count = len(columns) if columns else 0
            if column_count > 0:
                col_names = [c.get('name') for c in columns if c.get('name')]
                rule_parts.append(f"\nKey columns include: {', '.join(col_names[:5])}" + (f", and {column_count - 5} more" if column_count > 5 else ""))
            
            # Add relationship info
            if foreign_keys:
                fk_tables = set()
                for fk in foreign_keys:
                    referred = fk.get('referred_table')
                    if referred:
                        fk_tables.add(referred)
                if fk_tables:
                    rule_parts.append(f"\nThis table connects to: {', '.join(sorted(fk_tables))}")
                    rule_parts.append(f"Use these relationships to join with related tables for comprehensive queries.")
            
            # Add usage guidance
            rule_parts.append(f"\nCommon query patterns:")
            rule_parts.append(f"  - Selecting records with specific criteria")
            rule_parts.append(f"  - Joining with related tables for complete information")
            rule_parts.append(f"  - Aggregating data (counts, sums, averages)")
            rule_parts.append(f"  - Filtering by dates, statuses, or categories")
            
            rule_parts.append(f"\nAlways refer to the schema definition above when constructing queries.")
            rule_parts.append(f"Ensure all column names and relationships match the schema exactly.")
            
            return "\n".join(rule_parts)
        
        except Exception as e:
            logger.warning(f"Error generating natural language rule for {table_name}: {e}")
            return f"Table: {table_name}\n\nThis table is part of the connected database. Refer to the schema definition above for structure and relationships."
    
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
        try:
            # Try to get system settings from RAG by ID
            settings = self.rag_db.get_database_setting('system_settings')
            if settings:
                return settings
        except Exception as e:
            logger.warning(f"Could not retrieve system settings from RAG: {e}")
        
        # Return defaults if not found
        return {
            'id': 'system_settings',
            'type': 'system',
            'restricted_keywords': {
                'DROP': True,
                'DELETE': True,
                'INSERT': True,
                'ALTER': True,
                'SELECT': False,
                'UPDATE': True,
                'TRUNCATE': True
            },
            'smtp': {},
            'imap': {},
            'pop': {}
        }
    
    def update_system_settings(self, settings_data):
        """Update system settings in RAG database."""
        try:
            # Store in RAG database with fixed ID 'system_settings'
            self.rag_db.save_database_setting('system_settings', {
                'id': 'system_settings',
                'type': 'system',
                **settings_data
            })
            logger.info("[OK] System settings updated in RAG database")
            return settings_data
        except Exception as e:
            logger.error(f"Error updating system settings: {e}")
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
    # ============================================================================
    # QUERY VALIDATION (SECURITY)
    # ============================================================================
    
    def validate_query_for_restricted_keywords(self, query: str) -> tuple[bool, str]:
        """
        Validate a query against restricted SQL keywords.
        
        Args:
            query: SQL query to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Get restricted keywords from system settings
            settings = self.get_system_settings()
            restricted_keywords = settings.get('restricted_keywords', {})
            
            # Get list of keywords that are restricted (value = True)
            restricted_list = [kw for kw, is_restricted in restricted_keywords.items() if is_restricted]
            
            if not restricted_list:
                return True, ""
            
            # Check for each restricted keyword in the query
            query_upper = query.upper()
            
            for keyword in restricted_list:
                # Use regex to match whole keyword (not as part of another word)
                import re
                pattern = rf'\b{keyword}\b'
                if re.search(pattern, query_upper):
                    return False, f"The SQL keyword '{keyword}' is restricted and cannot be used in queries. Your query was blocked for security."
            
            return True, ""
        
        except Exception as e:
            logger.error(f"Error validating query: {str(e)}")
            # If validation fails, allow query (fail-open) but log it
            return True, ""