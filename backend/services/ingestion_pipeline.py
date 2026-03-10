"""
API-Mediated RAG Ingestion Pipeline Service.

Handles ETL (Extract, Transform, Load) for populating vector database from source databases.
Creates a "security air gap" between RAG and raw data sources.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

from backend.utils.database import DatabaseConnector
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class IngestionPipeline:
    """Service for ingesting data from source databases into vector database."""

    def __init__(self):
        """Initialize the ingestion pipeline."""
        self.db_connector = DatabaseConnector()
        self.vector_client = self._init_vector_db()
        logger.info("✓ IngestionPipeline initialized")

    def _init_vector_db(self):
        """Initialize ChromaDB client for vector storage."""
        try:
            if chromadb and Settings:
                client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory="./chroma_data",
                        anonymized_telemetry=False
                    )
                )
                logger.info("✓ Vector database initialized")
                return client
            else:
                logger.warning("✗ ChromaDB not available")
                return None
        except Exception as e:
            logger.error(f"✗ Error initializing vector database: {str(e)}")
            return None

    def discover_tables(self, database_setting: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Discover all tables in the source database.
        
        Args:
            database_setting: Database connection configuration
            
        Returns:
            List of table information with structure
        """
        try:
            connector = DatabaseConnector()
            connector.set_connection(database_setting)
            
            tables = connector.get_table_names()
            table_info = []
            
            for table_name in tables:
                try:
                    columns = connector.get_table_columns(table_name)
                    sample_data = connector.get_sample_data(table_name, limit=5)
                    
                    table_info.append({
                        'name': table_name,
                        'columns': columns,
                        'sample_count': len(sample_data),
                        'enabled': False,
                        'sync_interval': 60,  # Default: every hour
                        'conditions': {},  # Empty conditions by default
                        'query_template': self._generate_query_template(table_name, columns)
                    })
                except Exception as e:
                    logger.warning(f"Error discovering table {table_name}: {str(e)}")
                    continue
            
            logger.info(f"✓ Discovered {len(table_info)} tables")
            return table_info
            
        except Exception as e:
            logger.error(f"✗ Error discovering tables: {str(e)}")
            return []

    def _generate_query_template(self, table_name: str, columns: List[str]) -> str:
        """
        Generate a suggested query template for table extraction.
        
        Args:
            table_name: Name of the table
            columns: List of column names
            
        Returns:
            SQL query template (editable)
        """
        column_list = ', '.join(columns[:10])  # First 10 columns
        return f"SELECT {column_list} FROM {table_name} ORDER BY id DESC LIMIT 1000"

    def transform_to_chunks(self, table_name: str, data: List[Dict[str, Any]], 
                           columns: List[str]) -> List[str]:
        """
        Transform raw data into natural language chunks for embedding.
        
        Converts database records to readable text format:
        {"name": "Product X", "price": 100} -> "Product X costs 100 dollars"
        
        Args:
            table_name: Name of the source table
            data: List of record dictionaries
            columns: Column names and their descriptions
            
        Returns:
            List of text chunks ready for vectorization
        """
        chunks = []
        
        for record in data:
            chunk_text = f"From table {table_name}: "
            text_parts = []
            
            for column, value in record.items():
                if value is None:
                    continue
                    
                # Convert different types to readable format
                if isinstance(value, bool):
                    text_parts.append(f"{column} is {'yes' if value else 'no'}")
                elif isinstance(value, (int, float)):
                    text_parts.append(f"{column} is {value}")
                elif isinstance(value, str):
                    # Avoid very long strings
                    if len(value) > 255:
                        value = value[:252] + "..."
                    text_parts.append(f"{column} contains '{value}'")
                elif isinstance(value, dict):
                    text_parts.append(f"{column} is {json.dumps(value)}")
                else:
                    text_parts.append(f"{column} is {str(value)}")
            
            if text_parts:
                chunk_text += "; ".join(text_parts)
                chunks.append(chunk_text)
        
        return chunks

    def ingest_table(self, database_setting: Dict[str, Any], table_config: Dict[str, Any],
                     collection_name: str) -> Dict[str, Any]:
        """
        Ingest data from a table into the vector database.
        
        Steps:
        1. Extract: Query the table with the configured SQL
        2. Transform: Convert records to natural language chunks
        3. Vectorize: Use embedding model to create vectors
        4. Store: Save vectors and metadata in ChromaDB
        
        Args:
            database_setting: Source database configuration
            table_config: Table-specific ingestion config with query and conditions
            collection_name: Vector DB collection name
            
        Returns:
            Result dictionary with status and metadata
        """
        try:
            if not self.vector_client:
                return {'status': 'error', 'message': 'Vector DB not available'}
            
            table_name = table_config.get('name')
            query = table_config.get('query_template', f"SELECT * FROM {table_name}")
            
            logger.info(f"→ Ingesting table: {table_name}")
            
            # Step 1: Extract
            connector = DatabaseConnector()
            connector.set_connection(database_setting)
            data = connector.execute_query(query)
            
            if not data:
                logger.warning(f"✗ No data extracted from {table_name}")
                return {
                    'status': 'success',
                    'table': table_name,
                    'records_ingested': 0,
                    'chunks_created': 0
                }
            
            # Step 2: Transform
            columns = table_config.get('columns', [])
            chunks = self.transform_to_chunks(table_name, data, columns)
            
            if not chunks:
                logger.warning(f"✗ No chunks generated from {table_name}")
                return {
                    'status': 'success',
                    'table': table_name,
                    'records_ingested': len(data),
                    'chunks_created': 0
                }
            
            # Step 3 & 4: Vectorize and Store
            collection = self.vector_client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"Vector DB for {table_name}"}
            )
            
            # Add documents with metadata
            ids = []
            metadatas = []
            documents = []
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{table_name}_{uuid.uuid4()}"
                ids.append(doc_id)
                documents.append(chunk)
                metadatas.append({
                    'table': table_name,
                    'chunk_index': i,
                    'total_chunks': len(chunks),
                    'ingested_at': datetime.utcnow().isoformat()
                })
            
            collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"✓ Ingested {len(data)} records from {table_name} as {len(chunks)} chunks")
            
            return {
                'status': 'success',
                'table': table_name,
                'records_ingested': len(data),
                'chunks_created': len(chunks),
                'vector_ids': len(ids),
                'ingested_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"✗ Error ingesting table {table_name}: {str(e)}")
            return {
                'status': 'error',
                'table': table_name,
                'error': str(e)
            }

    def ingest_database(self, database_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ingest all selected tables from a database.
        
        Args:
            database_setting: Database configuration with selected_tables
            
        Returns:
            Summary of ingestion results
        """
        try:
            selected_tables = database_setting.get('selected_tables', {})
            collection_name = database_setting.get('vector_db_collection')
            
            if not collection_name:
                collection_name = f"db_{database_setting.get('id', 'unknown')}"
            
            results = {
                'status': 'success',
                'database': database_setting.get('name'),
                'total_tables': 0,
                'tables_ingested': 0,
                'total_records': 0,
                'total_chunks': 0,
                'table_results': [],
                'started_at': datetime.utcnow().isoformat()
            }
            
            for table_name, table_config in selected_tables.items():
                if not table_config.get('enabled'):
                    continue
                
                results['total_tables'] += 1
                table_result = self.ingest_table(database_setting, table_config, collection_name)
                results['table_results'].append(table_result)
                
                if table_result['status'] == 'success':
                    results['tables_ingested'] += 1
                    results['total_records'] += table_result.get('records_ingested', 0)
                    results['total_chunks'] += table_result.get('chunks_created', 0)
            
            results['completed_at'] = datetime.utcnow().isoformat()
            logger.info(f"✓ Ingestion complete: {results['tables_ingested']}/{results['total_tables']} tables")
            
            return results
            
        except Exception as e:
            logger.error(f"✗ Error ingesting database: {str(e)}")
            return {
                'status': 'error',
                'database': database_setting.get('name'),
                'error': str(e)
            }

    def search_vector_db(self, query: str, collection_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the vector database for relevant context.
        
        This is called by the LLM when using API Query mode.
        
        Args:
            query: Natural language search query
            collection_name: Vector DB collection to search
            top_k: Number of top results to return
            
        Returns:
            List of relevant context items with metadata
        """
        try:
            if not self.vector_client:
                return []
            
            collection = self.vector_client.get_collection(name=collection_name)
            results = collection.query(
                query_texts=[query],
                n_results=min(top_k, collection.count())
            )
            
            context = []
            if results and results.get('documents'):
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results.get('metadatas', [[]])[0][i] if results.get('metadatas') else {}
                    distance = results.get('distances', [[]])[0][i] if results.get('distances') else None
                    
                    context.append({
                        'text': doc,
                        'metadata': metadata,
                        'relevance_score': 1 - (distance / 2) if distance else 0.5
                    })
            
            return context
            
        except Exception as e:
            logger.error(f"✗ Error searching vector DB: {str(e)}")
            return []

    def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents from a collection for re-ingestion."""
        try:
            if not self.vector_client:
                return False
            
            collection = self.vector_client.get_collection(name=collection_name)
            collection.delete_all()
            logger.info(f"✓ Cleared collection: {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Error clearing collection: {str(e)}")
            return False
    
    def detect_table_relationships(self, database_setting: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        Detect foreign key relationships between tables.
        
        Returns mapping of table -> related tables for auto-configuration.
        Example: {'users': ['orders', 'profiles'], 'orders': ['users', 'items']}
        
        Args:
            database_setting: Database connection configuration
            
        Returns:
            Dictionary mapping table names to their related tables
        """
        try:
            connector = DatabaseConnector()
            connector.set_connection(database_setting)
            
            relationships = {}
            
            db_type = database_setting.get('db_type', 'mysql').lower()
            
            if 'postgres' in db_type or 'sqlite' in db_type or 'mysql' in db_type:
                # Query information schema for foreign keys
                if 'postgres' in db_type:
                    # PostgreSQL foreign key query
                    fk_query = """
                    SELECT kcu1.table_name, kcu2.table_name as related_table
                    FROM information_schema.referential_constraints rc
                    JOIN information_schema.key_column_usage kcu1 ON rc.constraint_name = kcu1.constraint_name
                    JOIN information_schema.key_column_usage kcu2 ON rc.unique_constraint_name = kcu2.constraint_name
                    """
                elif 'mysql' in db_type:
                    # MySQL foreign key query
                    fk_query = """
                    SELECT TABLE_NAME, REFERENCED_TABLE_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE REFERENCED_TABLE_NAME IS NOT NULL
                    """
                else:
                    # SQLite doesn't expose foreign keys in information_schema easily
                    return relationships
                
                try:
                    results = connector.execute_query(fk_query)
                    for row in results:
                        table = row.get('TABLE_NAME') or row.get('table_name')
                        related = row.get('REFERENCED_TABLE_NAME') or row.get('related_table')
                        if table and related:
                            if table not in relationships:
                                relationships[table] = []
                            if related not in relationships[table]:
                                relationships[table].append(related)
                except Exception as e:
                    logger.warning(f"Could not detect relationships: {e}")
            
            logger.info(f"✓ Detected relationships for {len(relationships)} tables")
            return relationships
            
        except Exception as e:
            logger.error(f"✗ Error detecting relationships: {str(e)}")
            return {}
    
    def get_related_records(self, connector: DatabaseConnector, primary_table: str,
                           primary_record: Dict[str, Any], relationships: Dict[str, List[str]],
                           config: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get related records from related tables for a given primary record.
        
        Implements smart joining based on detected relationships and configuration.
        
        Args:
            connector: Database connector
            primary_table: Name of primary table
            primary_record: The primary record to find related data for
            relationships: Table relationship mapping
            config: Configuration with join rules
            
        Returns:
            Dictionary mapping related table names to their records
        """
        related_data = {}
        
        try:
            if primary_table not in relationships:
                return related_data
            
            # Get auto-config setting
            auto_join_related = config.get('auto_join_related', True)
            join_limit = config.get('join_records_limit', 50)
            
            if not auto_join_related:
                return related_data
            
            related_tables = relationships.get(primary_table, [])
            
            for related_table in related_tables[:5]:  # Limit to 5 related tables max
                try:
                    # Find common keys
                    query = f"SELECT * FROM {related_table} LIMIT {join_limit}"
                    
                    # Try to find foreign key match
                    id_field = f"{primary_table.rstrip('s')}_id"  # Simple heuristic
                    primary_id = primary_record.get('id')
                    
                    if primary_id:
                        query = f"SELECT * FROM {related_table} WHERE {id_field} = {primary_id} LIMIT {join_limit}"
                    
                    records = connector.execute_query(query)
                    if records:
                        related_data[related_table] = records
                        logger.info(f"  ✓ Retrieved {len(records)} records from {related_table}")
                        
                except Exception as e:
                    logger.warning(f"  Could not retrieve related table {related_table}: {e}")
                    continue
            
            return related_data
            
        except Exception as e:
            logger.error(f"Error getting related records: {e}")
            return related_data
    
    def store_raw_ingested_data(self, database_id: str, table_name: str, 
                               data: List[Dict[str, Any]], related_data: Dict[str, List[Dict[str, Any]]] = None) -> bool:
        """
        Store raw ingested data separately from vectors for audit/recovery.
        
        Maintains a JSON backup of all ingested data alongside vector embeddings.
        
        Args:
            database_id: Source database ID
            table_name: Table name
            data: Raw data records
            related_data: Optional related records from other tables
            
        Returns:
            Success status
        """
        try:
            from pathlib import Path
            
            # Store in JSON format for easy access and audit trails
            raw_data_dir = Path(f"instance/ingested_data/{database_id}")
            raw_data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save table data
            table_data_file = raw_data_dir / f"{table_name}.json"
            with open(table_data_file, 'w') as f:
                json.dump({
                    'table': table_name,
                    'database_id': database_id,
                    'record_count': len(data),
                    'timestamp': datetime.now().isoformat(),
                    'records': data
                }, f, indent=2, default=str)
            
            logger.info(f"✓ Stored {len(data)} raw records for {table_name} to {table_data_file}")
            
            # Save related data if provided
            if related_data:
                related_file = raw_data_dir / f"{table_name}_related.json"
                with open(related_file, 'w') as f:
                    json.dump({
                        'table': table_name,
                        'database_id': database_id,
                        'related': {
                            rel_table: len(records) for rel_table, records in related_data.items()
                        },
                        'timestamp': datetime.now().isoformat(),
                        'data': related_data
                    }, f, indent=2, default=str)
                
                logger.info(f"✓ Stored related data for {table_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing raw ingested data: {e}")
            return False
    
    def ingest_table_with_processing(self, database_setting: Dict[str, Any], 
                                     table_config: Dict[str, Any],
                                     embeddings_method: str = 'semantic') -> Dict[str, Any]:
        """
        Extended ingest method that handles:
        1. Related record fetching
        2. Raw data persistence  
        3. Embeddings generation
        4. Configurable processing
        
        Args:
            database_setting: Database connection config
            table_config: Table configuration with processing preferences
            embeddings_method: 'semantic' or 'raw' for embedding approach
            
        Returns:
            Result with ingestion statistics
        """
        try:
            table_name = table_config.get('name')
            query = table_config.get('query_template', f"SELECT * FROM {table_name}")
            logger.info(f"→ Extended ingestion for {table_name} using {embeddings_method} embeddings")
            
            # Step 1: Extract data
            connector = DatabaseConnector()
            connector.set_connection(database_setting)
            data = connector.execute_query(query)
            
            if not data:
                logger.warning(f"✗ No data extracted from {table_name}")
                return {
                    'status': 'success',
                    'table': table_name,
                    'records_ingested': 0,
                    'records_with_relationships': 0,
                    'embeddings_generated': 0
                }
            
            # Step 2: Detect relationships if auto-join enabled
            related_data_map = {}
            auto_join = table_config.get('auto_join_related_tables', True)
            
            if auto_join:
                relationships = self.detect_table_relationships(database_setting)
                
                # Get related records for each primary record
                for i, record in enumerate(data):
                    if i >= 10:  # Limit relationship fetching for performance
                        break
                    
                    related = self.get_related_records(
                        connector, table_name, record, relationships,
                        {'auto_join_related': True, 'join_records_limit': 20}
                    )
                    if related:
                        related_data_map[record.get('id', i)] = related
            
            # Step 3: Store raw data
            database_id = database_setting.get('id')
            self.store_raw_ingested_data(database_id, table_name, data, 
                                        related_data_map if related_data_map else None)
            
            # Step 4: Transform to chunks
            columns = table_config.get('columns', [])
            chunks = self.transform_to_chunks(table_name, data, columns)
            
            # Step 5: Generate embeddings and store
            if not self.vector_client:
                return {
                    'status': 'error',
                    'message': 'Vector database not available',
                    'table': table_name
                }
            
            # Create collection for this database's ingested data
            collection_name = f"ingested_{database_id}_{table_name}".replace('-', '_')[:60]
            
            try:
                self.vector_client.delete_collection(name=collection_name)
            except:
                pass  # Collection doesn't exist yet
            
            # Add records with metadata
            ids = [f"{database_id}_{table_name}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    'database_id': database_id,
                    'table_name': table_name,
                    'record_index': i,
                    'record_id': str(data[i].get('id', i)) if i < len(data) else str(i),
                    'has_related': str(data[i].get('id', i) in related_data_map) if i < len(data) else 'false'
                }
                for i in range(len(chunks))
            ]
            
            self.vector_client.add(
                collection_name=collection_name,
                ids=ids,
                metadatas=metadatas,
                documents=chunks
            )
            
            result = {
                'status': 'success',
                'table': table_name,
                'records_ingested': len(data),
                'records_with_relationships': len(related_data_map),
                'embeddings_generated': len(chunks),
                'embedding_method': embeddings_method,
                'collection_name': collection_name,
                'raw_data_stored': True
            }
            
            logger.info(f"✓ Ingestion complete: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error in extended ingestion: {e}")
            return {'status': 'error', 'message': str(e), 'table': table_config.get('name')}
