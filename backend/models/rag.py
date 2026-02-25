"""RAG-related models."""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON, ARRAY
from backend.models import db


class RAGItem(db.Model):
    """RAG knowledge base items."""
    __tablename__ = 'rag_items'
    
    id = db.Column(db.String(36), primary_key=True)
    category = db.Column(db.String(100), nullable=False)  # schema, relationship, business_rule, sample_data, custom
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100), default='manual')  # manual or auto-populated
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'category': self.category,
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class BusinessRule(db.Model):
    """Business rules for RAG context."""
    __tablename__ = 'business_rules'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    rule_type = db.Column(db.String(50), nullable=False)  # 'compulsory', 'optional', 'constraint'
    content = db.Column(db.Text, nullable=False)  # The actual rule text
    category = db.Column(db.String(100))  # For filtering
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type,
            'content': self.content,
            'category': self.category,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class SchemaInfo(db.Model):
    """Database schema information for RAG."""
    __tablename__ = 'schema_info'
    
    id = db.Column(db.String(36), primary_key=True)
    table_name = db.Column(db.String(255), nullable=False)
    column_name = db.Column(db.String(255), nullable=False)
    column_type = db.Column(db.String(100), nullable=False)
    sample_values = db.Column(JSON)  # Sample data from column
    description = db.Column(db.Text)
    embedding_id = db.Column(db.String(255))  # ID in vector store
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'table_name': self.table_name,
            'column_name': self.column_name,
            'column_type': self.column_type,
            'sample_values': self.sample_values,
            'description': self.description,
            'created_at': self.created_at.isoformat()
        }
