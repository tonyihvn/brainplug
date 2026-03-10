"""
Database Query Router

Routes queries to either direct database execution or vector database semantic search
based on the configured query mode for the active database.
"""

from typing import Dict, List, Any, Optional
from backend.utils.logger import setup_logger
from backend.utils.database import DatabaseConnector
from backend.services.ingestion_pipeline import IngestionPipeline

logger = setup_logger(__name__)


class DatabaseQueryRouter:
    """Routes database queries to appropriate execution method based on query mode."""

    def __init__(self):
        """Initialize the router."""
        self.db_connector = DatabaseConnector()
        self.ingestion_pipeline = IngestionPipeline()

    def execute_query(self, query: str, database_setting: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Execute a query using the appropriate mode.
        
        Routes to either:
        - Direct SQL query execution (for 'direct' mode)
        - Semantic vector search (for 'api' mode)
        
        Args:
            query: The SQL query or search query
            database_setting: Database configuration (if not provided, uses active DB)
            
        Returns:
            Query results as list of dictionaries
        """
        try:
            # Get database setting if not provided
            if not database_setting:
                from backend.services.settings_service import SettingsService
                settings_service = SettingsService()
                database_setting = settings_service.get_active_database()
                
                if not database_setting:
                    logger.error("✗ No active database configured")
                    return []
            
            # Validate query for restricted keywords
            from backend.services.settings_service import SettingsService
            settings_service = SettingsService()
            is_valid, error_msg = settings_service.validate_query_for_restricted_keywords(query)
            
            if not is_valid:
                logger.error(f"✗ Query validation failed: {error_msg}")
                raise ValueError(error_msg)
            
            query_mode = database_setting.get('query_mode', 'direct')
            db_name = database_setting.get('name', 'unknown')
            
            logger.info(f"→ Query mode for {db_name}: {query_mode}")
            
            if query_mode == 'api':
                # Use semantic search on vector database
                logger.info(f"→ Using API Query mode (Vector DB search)")
                return self._search_vector_db(query, database_setting)
            else:
                # Use direct SQL query
                logger.info(f"→ Using Direct Query mode (SQL)")
                return self._execute_sql_query(query, database_setting)
                
        except Exception as e:
            logger.error(f"✗ Error executing query: {str(e)}")
            return []

    def _execute_sql_query(self, query: str, database_setting: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute a direct SQL query against the source database.
        
        Args:
            query: SQL query string
            database_setting: Database configuration
            
        Returns:
            Query results
        """
        try:
            self.db_connector.set_connection(database_setting)
            rows = self.db_connector.execute_query(query)
            
            # Convert rows to list of dicts if needed
            if rows and isinstance(rows[0], dict):
                return rows
            elif rows:
                # Convert tuple/other format to dict
                return [dict(row) if hasattr(row, '__dict__') else row for row in rows]
            else:
                return []
                
        except Exception as e:
            logger.error(f"✗ Error executing SQL query: {str(e)}")
            return []

    def _search_vector_db(self, search_query: str, database_setting: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Search the vector database for relevant context.
        
        Converts semantic search results into a format similar to SQL query results.
        
        Args:
            search_query: Natural language search query
            database_setting: Database configuration with vector DB collection info
            
        Returns:
            Search results formatted like SQL rows
        """
        try:
            collection_name = database_setting.get('vector_db_collection')
            if not collection_name:
                collection_name = f"db_{database_setting.get('id', 'unknown')}"
            
            logger.info(f"→ Searching vector DB collection: {collection_name}")
            
            # Search vector database
            context_items = self.ingestion_pipeline.search_vector_db(
                query=search_query,
                collection_name=collection_name,
                top_k=10  # Return top 10 relevant chunks
            )
            
            if not context_items:
                logger.warning("✗ No relevant data found in vector database")
                return []
            
            # Convert context items to row format
            results = []
            for i, item in enumerate(context_items):
                results.append({
                    'source': f"Vector Search Result #{i+1}",
                    'table': item.get('metadata', {}).get('table', 'unknown'),
                    'content': item.get('text', ''),
                    'relevance_score': item.get('relevance_score', 0),
                    'chunk_index': item.get('metadata', {}).get('chunk_index'),
                    '_vector_result': True  # Flag to indicate this came from vector DB
                })
            
            logger.info(f"✓ Vector search returned {len(results)} relevant chunks")
            return results
            
        except Exception as e:
            logger.error(f"✗ Error searching vector database: {str(e)}")
            return []

    def suggest_vector_search(self, sql_query: str, database_setting: Dict[str, Any]) -> str:
        """
        Convert a SQL query suggestion into a semantic search query.
        
        Used when the LLM suggests a SQL query but the database is in API mode.
        Converts: "SELECT * FROM products WHERE price > 100"
        To: "Products with price greater than 100"
        
        Args:
            sql_query: SQL query suggested by LLM
            database_setting: Database configuration
            
        Returns:
            Natural language search query
        """
        try:
            # Simple heuristic conversion - could be enhanced with NLP
            sql_lower = sql_query.lower().strip()
            
            # Extract basic patterns
            if 'select' in sql_lower and 'from' in sql_lower:
                # Try to extract key information from SELECT query
                import re
                
                # Look for WHERE clause
                match = re.search(r'where\s+(.+?)(?:\s+order\s+by|\s+limit|$)', sql_lower)
                if match:
                    conditions = match.group(1).strip()
                    # Extract table name
                    table_match = re.search(r'from\s+(\w+)', sql_lower)
                    table = table_match.group(1) if table_match else 'records'
                    
                    return f"Find {table} records where {conditions}"
            
            # Fallback: use the query as-is but remove SQL keywords
            search_query = re.sub(r'\b(select|from|where|and|or|=|<|>)\b', '', sql_query, flags=re.IGNORECASE)
            return search_query.strip() if search_query.strip() else sql_query
            
        except Exception as e:
            logger.error(f"✗ Error converting SQL to search query: {str(e)}")
            return sql_query


# Global instance
_query_router = None


def get_query_router() -> DatabaseQueryRouter:
    """Get the global query router instance."""
    global _query_router
    if _query_router is None:
        _query_router = DatabaseQueryRouter()
    return _query_router
