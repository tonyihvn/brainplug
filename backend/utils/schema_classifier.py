"""
Schema classifier for intelligent RAG filtering.

Determines which database schemas are relevant to a user query,
avoiding token waste and preventing SQL from referencing non-existent tables.
"""
import re
from typing import List, Dict, Set, Tuple, Optional
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class SchemaClassifier:
    """Classifies user queries and extracts relevant table names from RAG context."""
    
    # Keywords that indicate table/schema references
    TABLE_KEYWORDS = {
        'table', 'tables', 'schema', 'schemas', 'database', 'collection',
        'entity', 'entities', 'model', 'models', 'record', 'records',
        'data', 'information', 'details', 'list', 'view', 'report'
    }
    
    # SQL-related keywords
    SQL_KEYWORDS = {
        'select', 'from', 'where', 'join', 'insert', 'update', 'delete',
        'query', 'fetch', 'retrieve', 'search', 'find', 'get', 'show'
    }
    
    # Action keywords that may need specific tables
    ACTION_KEYWORDS = {
        'export': 'query',
        'import': 'write',
        'report': 'query',
        'summary': 'query',
        'total': 'aggregate',
        'count': 'aggregate',
        'list': 'query',
        'show': 'query',
        'display': 'query',
        'print': 'query',
        'email': 'query',
        'send': 'action',
        'create': 'write',
        'add': 'write',
        'insert': 'write',
        'update': 'write',
        'modify': 'write',
        'change': 'write',
        'delete': 'write',
        'remove': 'write',
    }
    
    def __init__(self):
        """Initialize the schema classifier."""
        pass
    
    def extract_table_names(self, text: str) -> Set[str]:
        """
        Extract potential table names from text using multiple strategies.
        
        Uses fuzzy matching, SQL patterns, and noun phrase extraction.
        
        Args:
            text: User query or prompt
        
        Returns:
            Set of extracted table names (lowercased)
        """
        text_lower = text.lower()
        extracted = set()
        
        # Strategy 1: Match SQL FROM/JOIN clauses
        # Matches: FROM table_name, JOIN table_name
        from_pattern = r'\b(?:from|join|inner join|left join|right join|full join)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        for match in re.finditer(from_pattern, text_lower):
            table = match.group(1)
            if len(table) > 2:  # Avoid too-short matches
                extracted.add(table)
        
        # Strategy 2: Match quoted identifiers
        # Matches: "table_name" or `table_name`
        quoted_pattern = r'["`]([a-zA-Z_][a-zA-Z0-9_]*)["`]'
        for match in re.finditer(quoted_pattern, text_lower):
            table = match.group(1)
            if len(table) > 2:
                extracted.add(table)
        
        # Strategy 3: Match explicit mentions with patterns
        # Matches: "the users table", "users table", "table users", "users schema"
        mention_pattern = r'\b(?:the\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:table|schema|entity|model|collection|database)\b'
        for match in re.finditer(mention_pattern, text_lower):
            table = match.group(1)
            if len(table) > 2 and not self._is_common_word(table):
                extracted.add(table)
        
        # Strategy 4: Match table plural/singular forms
        # Matches: word pairs like "user records", "product items"
        plural_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s+(?:records?|rows?|items?|entries?|objects?|instances?)\b'
        for match in re.finditer(plural_pattern, text_lower):
            table = match.group(1)
            if len(table) > 2 and not self._is_common_word(table):
                extracted.add(table)
        
        # Strategy 5: Look for possessive patterns
        # Matches: "user's orders", "customer's data", "product's inventory"
        possessive_pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)[\'s]*\s+(?:data|records?|information|details)\b'
        for match in re.finditer(possessive_pattern, text_lower):
            table = match.group(1)
            if len(table) > 2 and not self._is_common_word(table):
                extracted.add(table)
        
        # Strategy 6: Contextual extraction - nouns after prepositions
        # Matches: "in users", "on products", "from orders"
        context_pattern = r'\b(?:in|on|from|at|by|of)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b'
        for match in re.finditer(context_pattern, text_lower):
            word = match.group(1)
            if len(word) > 2 and not self._is_common_word(word) and word not in self.SQL_KEYWORDS:
                extracted.add(word)
        
        logger.debug(f"[extract_table_names] Extracted from query: {extracted}")
        return extracted
    
    def _is_common_word(self, word: str) -> bool:
        """Check if a word is too common to be a table name."""
        common_words = {
            'the', 'and', 'or', 'not', 'is', 'are', 'was', 'were', 'be',
            'have', 'has', 'do', 'does', 'did', 'will', 'would', 'should',
            'could', 'can', 'may', 'might', 'must', 'shall', 'it', 'this',
            'that', 'these', 'those', 'what', 'which', 'who', 'when', 'where',
            'why', 'how', 'all', 'each', 'every', 'both', 'any', 'many', 'some',
            'few', 'more', 'most', 'other', 'such', 'no', 'nor', 'as', 'if',
            'to', 'for', 'with', 'by', 'from', 'up', 'about', 'out', 'into',
            'through', 'during', 'before', 'after', 'above', 'below', 'between',
            'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when',
            'a', 'an', 'your', 'our', 'their', 'its', 'my', 'your', 'his', 'her'
        }
        return word in common_words or len(word) < 3
    
    def match_tables_to_rag(
        self, 
        query: str, 
        available_schemas: List[Dict],
        conversation_history: List[Dict] = None
    ) -> Tuple[List[Dict], List[str], bool]:
        """
        Match extracted table names to available RAG schemas.
        
        Args:
            query: User query
            available_schemas: List of available RAG schema records
            conversation_history: Previous messages for context (optional)
        
        Returns:
            Tuple of (matched_schemas, extracted_table_names, needs_clarification)
        """
        extracted_tables = self.extract_table_names(query)
        
        # Also extract from conversation history if provided
        if conversation_history:
            for msg in conversation_history[-3:]:  # Look at last 3 messages
                if isinstance(msg, dict) and 'content' in msg:
                    extracted_tables.update(self.extract_table_names(msg['content']))
        
        # Build mapping of RAG schemas
        schema_map = {}  # table_name -> schema
        for schema in available_schemas:
            # Extract table name from schema ID (format: tableName_schema)
            schema_id = schema.get('id', '') or schema.get('name', '')
            if schema_id.endswith('_schema'):
                table_name = schema_id[:-7]  # Remove "_schema" suffix
                schema_map[table_name] = schema
            
            # Also check metadata
            if 'metadata' in schema and 'table_name' in schema['metadata']:
                table_name = schema['metadata']['table_name']
                schema_map[table_name] = schema
        
        logger.debug(f"[match_tables_to_rag] Schema map keys: {set(schema_map.keys())}")
        logger.debug(f"[match_tables_to_rag] Extracted tables: {extracted_tables}")
        
        # Try exact matches first
        matched_schemas = []
        matched_tables = set()
        unmatched_tables = set()
        
        for table in extracted_tables:
            if table in schema_map:
                matched_schemas.append(schema_map[table])
                matched_tables.add(table)
                logger.debug(f"✓ Matched table: {table}")
            else:
                unmatched_tables.add(table)
                logger.debug(f"✗ Unmatched table: {table}")
        
        # Try fuzzy matching for unmatched tables
        for unmatched in list(unmatched_tables):
            for schema_table in schema_map.keys():
                if self._fuzzy_match(unmatched, schema_table):
                    matched_schemas.append(schema_map[schema_table])
                    matched_tables.add(schema_table)
                    unmatched_tables.discard(unmatched)
                    logger.debug(f"✓ Fuzzy matched: {unmatched} -> {schema_table}")
                    break
        
        # If nothing extracted and we have context, use recent schemas
        needs_clarification = False
        if not extracted_tables and not matched_schemas:
            logger.debug(f"[match_tables_to_rag] No tables extracted; using default strategy")
            # Return empty if query is unclear
            needs_clarification = True
        
        # If unmatched tables exist, flag for clarification
        elif unmatched_tables:
            needs_clarification = True
            logger.warning(f"[match_tables_to_rag] Tables mentioned but not in RAG: {unmatched_tables}")
        
        # Ensure no duplicates
        matched_schemas = list({s.get('id'): s for s in matched_schemas}.values())
        
        logger.info(
            f"[match_tables_to_rag] Query matched {len(matched_schemas)} schemas. "
            f"Extracted: {extracted_tables}, Matched: {matched_tables}, Needs clarification: {needs_clarification}"
        )
        
        return matched_schemas, list(extracted_tables), needs_clarification
    
    def _fuzzy_match(self, query_table: str, schema_table: str, threshold: float = 0.7) -> bool:
        """
        Simple fuzzy matching using substring and Levenshtein-like distance.
        
        Args:
            query_table: Table name from query
            schema_table: Table name from schema
            threshold: Similarity threshold (0-1)
        
        Returns:
            True if tables are similar enough
        """
        # Check if one is substring of the other
        if query_table in schema_table or schema_table in query_table:
            return True
        
        # Simple char-level similarity
        common = sum(1 for c in query_table if c in schema_table)
        similarity = common / max(len(query_table), len(schema_table))
        
        return similarity >= threshold
    
    def get_clarification_message(
        self,
        query: str,
        extracted_tables: List[str],
        available_schemas: List[Dict],
        unmatched_tables: List[str]
    ) -> str:
        """
        Generate a clarification message for the user.
        
        Args:
            query: Original query
            extracted_tables: Tables extracted from query
            available_schemas: All available schemas
            unmatched_tables: Tables that couldn't be matched
        
        Returns:
            Clarification message for user
        """
        # Get available table names
        available_tables = []
        for schema in available_schemas:
            schema_id = schema.get('id', '') or schema.get('name', '')
            if schema_id.endswith('_schema'):
                available_tables.append(schema_id[:-7])
        
        message = "I need clarification about which tables you're referring to.\n\n"
        
        if unmatched_tables:
            message += f"You mentioned: {', '.join(unmatched_tables)}\n"
            message += f"But these don't exist in the database.\n\n"
        
        if not extracted_tables:
            message += "Your query didn't clearly specify which tables to query.\n\n"
        
        message += f"Available tables:\n"
        for table in sorted(available_tables):
            message += f"- {table}\n"
        
        message += "\nPlease rephrase your question using table names from the list above."
        
        return message
    
    def classify_query_intent(self, query: str) -> Dict[str, any]:
        """
        Classify the intent of a query (SELECT, INSERT, UPDATE, DELETE, etc).
        
        Args:
            query: User query
        
        Returns:
            Dictionary with intent classification
        """
        query_lower = query.lower()
        
        intent = {
            'type': 'UNKNOWN',
            'operation': None,
            'confidence': 'low'
        }
        
        # Check for operation keywords
        if any(w in query_lower for w in ['select', 'query', 'find', 'get', 'retrieve', 'fetch', 'show', 'list', 'display']):
            intent['type'] = 'SELECT'
            intent['operation'] = 'READ'
            intent['confidence'] = 'high'
        elif any(w in query_lower for w in ['insert', 'create', 'add', 'new']):
            intent['type'] = 'INSERT'
            intent['operation'] = 'WRITE'
            intent['confidence'] = 'high'
        elif any(w in query_lower for w in ['update', 'modify', 'change', 'set']):
            intent['type'] = 'UPDATE'
            intent['operation'] = 'WRITE'
            intent['confidence'] = 'high'
        elif any(w in query_lower for w in ['delete', 'remove', 'drop']):
            intent['type'] = 'DELETE'
            intent['operation'] = 'WRITE'
            intent['confidence'] = 'high'
        elif any(w in query_lower for w in ['join', 'combine', 'merge', 'correlate']):
            intent['type'] = 'SELECT'
            intent['operation'] = 'READ'
            intent['confidence'] = 'medium'
        elif any(w in query_lower for w in ['count', 'total', 'sum', 'average', 'aggregate']):
            intent['type'] = 'SELECT'
            intent['operation'] = 'AGGREGATE'
            intent['confidence'] = 'high'
        elif any(w in query_lower for w in ['export', 'save', 'download']):
            intent['type'] = 'SELECT'
            intent['operation'] = 'READ'
            intent['confidence'] = 'medium'
        elif any(w in query_lower for w in ['report', 'summary', 'analysis']):
            intent['type'] = 'SELECT'
            intent['operation'] = 'REPORT'
            intent['confidence'] = 'medium'
        
        return intent
