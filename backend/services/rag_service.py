"""RAG service for retrieval and embedding."""
import uuid
from datetime import datetime
try:
    from chromadb.config import Settings
    import chromadb
except Exception:
    chromadb = None
    Settings = None
from backend.models import db
from backend.models.rag import BusinessRule, SchemaInfo
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


class RAGService:
    """Service for RAG operations."""
    
    def __init__(self):
        """Initialize RAG service with vector store."""
        # Initialize Chroma vector store if available. If chromadb is not
        # installed, operate in a degraded mode where retrieval functions
        # return empty results but the app can still run.
        if chromadb and Settings:
            try:
                self.client = chromadb.Client(
                    Settings(
                        chroma_db_impl="duckdb+parquet",
                        persist_directory="./chroma_data",
                        anonymized_telemetry=False
                    )
                )
                self.collection = self.client.get_or_create_collection(
                    name="gemini_mcp_rag"
                )
                logger.info("RAG service initialized")
            except Exception as e:
                logger.error(f"Error initializing RAG service: {str(e)}")
                self.client = None
                self.collection = None
        else:
            logger.warning("chromadb not available; RAG functionality disabled")
            self.client = None
            self.collection = None
    
    def retrieve_context(self, query, top_k=5):
        """
        Retrieve relevant context from vector store.
        
        Args:
            query: User query
            top_k: Number of top results to return
        
        Returns:
            List of relevant context items
        """
        try:
            if not self.collection:
                return []

            if self.collection.count() == 0:
                return []

            results = self.collection.query(
                query_texts=[query],
                n_results=min(top_k, self.collection.count())
            )

            context = []
            if results and results.get('documents'):
                context = results['documents'][0]

            return context
        
        except Exception as e:
            logger.error(f"Error retrieving context: {str(e)}")
            return []
    
    def get_mandatory_rules(self):
        """Get mandatory business rules for all contexts."""
        try:
            rules = BusinessRule.query.filter_by(
                rule_type='compulsory',
                is_active=True
            ).all()
            
            return [r.to_dict() for r in rules]
        
        except Exception as e:
            logger.error(f"Error getting mandatory rules: {str(e)}")
            return []
    
    def get_business_rules(self):
        """Get all business rules."""
        try:
            rules = BusinessRule.query.all()
            return [r.to_dict() for r in rules]
        except Exception as e:
            logger.error(f"Error getting business rules: {str(e)}")
            return []
    
    def create_business_rule(self, rule_data):
        """Create a new business rule."""
        try:
            rule = BusinessRule(
                id=str(uuid.uuid4()),
                name=rule_data['name'],
                description=rule_data.get('description'),
                rule_type=rule_data.get('rule_type', 'optional'),
                content=rule_data['content'],
                category=rule_data.get('category'),
                is_active=rule_data.get('is_active', True)
            )
            
            db.session.add(rule)
            db.session.commit()
            
            # Add to vector store if available
            if self.collection:
                self.collection.add(
                    ids=[rule.id],
                    documents=[rule.content]
                )
            
            return rule.to_dict()
        
        except Exception as e:
            logger.error(f"Error creating business rule: {str(e)}")
            db.session.rollback()
            raise
    
    def update_business_rule(self, rule_id, rule_data):
        """Update an existing business rule."""
        try:
            rule = BusinessRule.query.get(rule_id)
            if not rule:
                raise ValueError("Rule not found")
            
            if 'name' in rule_data:
                rule.name = rule_data['name']
            if 'content' in rule_data:
                rule.content = rule_data['content']
            if 'rule_type' in rule_data:
                rule.rule_type = rule_data['rule_type']
            if 'is_active' in rule_data:
                rule.is_active = rule_data['is_active']
            
            db.session.commit()
            
            if self.collection:
                self.collection.update(
                    ids=[rule.id],
                    documents=[rule.content]
                )
            
            return rule.to_dict()
        
        except Exception as e:
            logger.error(f"Error updating business rule: {str(e)}")
            db.session.rollback()
            raise
    
    def delete_business_rule(self, rule_id):
        """Delete a business rule."""
        try:
            rule = BusinessRule.query.get(rule_id)
            if not rule:
                raise ValueError("Rule not found")
            
            db.session.delete(rule)
            db.session.commit()
            
            if self.collection:
                self.collection.delete(ids=[rule.id])
        
        except Exception as e:
            logger.error(f"Error deleting business rule: {str(e)}")
            db.session.rollback()
            raise
    
    def add_item(self, item):
        """Add a RAG item to the vector store."""
        try:
            if self.collection:
                self.collection.add(
                    ids=[item.id],
                    documents=[item.content],
                    metadatas=[{'category': item.category, 'title': item.title}]
                )
                logger.debug(f"Added RAG item to vector store: {item.title}")
        except Exception as e:
            logger.error(f"Error adding RAG item to vector store: {str(e)}")
    
    def update_item(self, item):
        """Update a RAG item in the vector store."""
        try:
            if self.collection:
                self.collection.update(
                    ids=[item.id],
                    documents=[item.content],
                    metadatas=[{'category': item.category, 'title': item.title}]
                )
                logger.debug(f"Updated RAG item in vector store: {item.title}")
        except Exception as e:
            logger.error(f"Error updating RAG item in vector store: {str(e)}")
    
    def remove_item(self, item_id):
        """Remove a RAG item from the vector store."""
        try:
            if self.collection:
                self.collection.delete(ids=[item_id])
                logger.debug(f"Removed RAG item from vector store: {item_id}")
        except Exception as e:
            logger.error(f"Error removing RAG item from vector store: {str(e)}")
    
    def get_schema(self):
        """Get database schema information."""
        try:
            schemas = SchemaInfo.query.all()
            return [s.to_dict() for s in schemas]
        except Exception as e:
            logger.error(f"Error getting schema: {str(e)}")
            return []
    
    def update_schema(self, schema_data):
        """
        Update or create schema information from connected database.
        This would typically be called when a new database is connected.
        """
        try:
            # Delete existing schema
            SchemaInfo.query.delete()
            db.session.commit()
            
            # Add new schema entries
            for table_schema in schema_data.get('tables', []):
                table_name = table_schema['table_name']
                
                for column in table_schema.get('columns', []):
                    # Store schema metadata but do NOT store sample_values here.
                    # Sample data is stored as business rules instead.
                    schema_entry = SchemaInfo(
                        id=str(uuid.uuid4()),
                        table_name=table_name,
                        column_name=column['name'],
                        column_type=column.get('type', 'TEXT'),
                        sample_values=[],
                        description=column.get('description', '')
                    )
                    
                    db.session.add(schema_entry)
                    
                    # Add to vector store for RAG retrieval if available
                    schema_doc = f"Table: {table_name}, Column: {column['name']}, Type: {column.get('type')}"
                    if self.collection:
                        self.collection.add(
                            ids=[schema_entry.id],
                            documents=[schema_doc]
                        )
            
            db.session.commit()
            return {'status': 'success', 'records_updated': len(schema_data.get('tables', []))}
        
        except Exception as e:
            logger.error(f"Error updating schema: {str(e)}")
            db.session.rollback()
            raise
