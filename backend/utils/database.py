"""Database connector utility."""
import sqlalchemy as sa
from sqlalchemy import inspect
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseConnector:
    """Manages database connections and queries."""
    
    def __init__(self):
        """Initialize database connector."""
        self.connections = {}
    
    def test_connection(self, connection_string):
        """Test database connection."""
        try:
            engine = sa.create_engine(connection_string)
            with engine.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
            logger.info("Database connection successful")
            return True
        except Exception as e:
            # Log but do not raise; callers can decide how to handle a failed
            # connection. Raising here previously caused the entire application
            # to fail to start when the configured DB (e.g. MySQL) was not
            # accepting connections. Return False so the caller can retry
            # later or save the setting without making the app crash.
            logger.warning(f"Database connection failed (will not raise): {str(e)}")
            return False
    
    def execute_query(self, db_name, query):
        """Execute a query on the specified database."""
        try:
            # For now, use default connection
            from app import db as main_db
            
            result = main_db.session.execute(sa.text(query))
            rows = [dict(row._mapping) for row in result.fetchall()]
            return rows
        except Exception as e:
            logger.error(f"Error executing query: {str(e)}")
            raise
    
    def get_schema(self, connection_string):
        """Get database schema with sample data and detailed column info."""
        try:
            engine = sa.create_engine(connection_string)
            inspector = inspect(engine)
            
            schema_data = {'tables': []}
            
            # Get all table names (handling schema-specific databases like PostgreSQL)
            logger.info(f"[SCHEMA] ========== SCHEMA EXTRACTION STARTING ==========")
            logger.info(f"[SCHEMA] Connection string type: {connection_string.split('://')[0] if '://' in connection_string else 'unknown'}")
            
            table_names = inspector.get_table_names()
            logger.info(f"[SCHEMA] Initial get_table_names() returned {len(table_names)} tables")
            
            if not table_names:
                # For PostgreSQL, tables might be in specific schemas; try to get them explicitly
                try:
                    schemas = inspector.get_schema_names()
                    logger.info(f"[SCHEMA] Available schemas in database: {schemas}")
                    
                    # Try to get tables from 'public' schema specifically for PostgreSQL
                    if 'public' in schemas:
                        table_names = inspector.get_table_names(schema='public')
                        logger.info(f"[SCHEMA] After explicit 'public' schema query: found {len(table_names)} tables")
                    else:
                        logger.warning(f"[SCHEMA] 'public' schema not found in available schemas")
                        
                        # Try first available schema
                        if schemas:
                            first_schema = schemas[0]
                            logger.info(f"[SCHEMA] Trying first available schema: {first_schema}")
                            table_names = inspector.get_table_names(schema=first_schema)
                            logger.info(f"[SCHEMA] After trying schema '{first_schema}': found {len(table_names)} tables")
                except Exception as e:
                    logger.warning(f"[SCHEMA] Could not retrieve schema list: {str(e)}")
            
            if not table_names:
                logger.warning(f"[SCHEMA] WARNING: No tables found after all attempts")
            else:
                logger.info(f"[SCHEMA] OK: Will process {len(table_names)} tables")
            
            for table_name in table_names:
                try:
                    logger.debug(f"[SCHEMA] Processing table: {table_name}")
                    
                    columns = inspector.get_columns(table_name)
                    primary_keys = inspector.get_pk_constraint(table_name)
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    
                    logger.debug(f"[SCHEMA]   ├─ Columns: {len(columns)}")
                    logger.debug(f"[SCHEMA]   ├─ Primary Keys: {primary_keys}")
                    logger.debug(f"[SCHEMA]   └─ Foreign Keys: {len(foreign_keys) if foreign_keys else 0}")
                    
                    table_schema = {
                        'table_name': table_name,
                        'columns': [],
                        'primary_keys': primary_keys.get('constrained_columns', []) if primary_keys else [],
                        'foreign_keys': foreign_keys if foreign_keys else []
                    }
                    
                    for column in columns:
                        col_info = {
                            'name': column['name'],
                            'type': str(column['type']),
                            'nullable': column['nullable'],
                            'default': str(column.get('default')) if column.get('default') else None,
                            'sample_values': []
                        }
                        table_schema['columns'].append(col_info)
                    
                    # Try to fetch sample data (limit 3 rows) but only keep up to 2 unique sample values per column
                    try:
                        with engine.connect() as conn:
                            result = conn.execute(
                                sa.text(f"SELECT * FROM {table_name} LIMIT 3")
                            )
                            rows = result.fetchall()
                            if rows:
                                # build a mapping of column name -> column dict for appending sample values
                                col_map = {c['name']: c for c in table_schema['columns']}
                                for row in rows:
                                    sample_row = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
                                    for col_name, col_dict in col_map.items():
                                        try:
                                            val = sample_row.get(col_name)
                                        except Exception:
                                            val = None
                                        if val is not None:
                                            sv = col_dict.get('sample_values') or []
                                            sval = str(val)[:100]
                                            if sval and sval not in sv:
                                                # Only keep up to 2 sample values per column
                                                if len(sv) < 2:
                                                    sv.append(sval)
                                                col_dict['sample_values'] = sv
                    except Exception as e:
                        logger.debug(f"Could not fetch sample data for {table_name}: {str(e)}")
                    
                    schema_data['tables'].append(table_schema)
                    logger.debug(f"[SCHEMA] Processed table: {table_name} ({len(table_schema['columns'])} columns)")
                except Exception as e:
                    logger.warning(f"[SCHEMA] Error processing table {table_name}: {str(e)}")
                    continue
            
            logger.info(f"[SCHEMA] Successfully retrieved schema: {len(schema_data['tables'])} tables")
            return schema_data
        except Exception as e:
            logger.error(f"Error getting schema: {str(e)}")
            raise
