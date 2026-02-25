"""Settings models for configuration."""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from backend.models import db


class DatabaseSetting(db.Model):
    """Database connection settings."""
    __tablename__ = 'database_settings'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    db_type = db.Column(db.String(50), nullable=False)  # 'postgresql', 'mysql', 'sqlite', etc.
    host = db.Column(db.String(255))
    port = db.Column(db.Integer)
    database = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255))
    password = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary (without password)."""
        return {
            'id': self.id,
            'name': self.name,
            'db_type': self.db_type,
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class LLMModel(db.Model):
    """LLM model configurations in priority order."""
    __tablename__ = 'llm_models'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    model_type = db.Column(db.String(50), nullable=False)  # 'gemini', 'gpt', 'llama', 'local', etc.
    model_id = db.Column(db.String(255), nullable=False)  # e.g., 'gemini-pro', 'gpt-4'
    api_key = db.Column(db.String(500))  # For cloud models
    api_endpoint = db.Column(db.String(500))  # For custom endpoints
    priority = db.Column(db.Integer, default=0)  # 0 = highest priority
    is_active = db.Column(db.Boolean, default=True)
    config = db.Column(JSON)  # Additional model-specific config
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'model_type': self.model_type,
            'model_id': self.model_id,
            'api_endpoint': self.api_endpoint,
            'priority': self.priority,
            'is_active': self.is_active,
            'config': self.config,
            'created_at': self.created_at.isoformat()
        }


class APIConfig(db.Model):
    """External API configurations."""
    __tablename__ = 'api_configs'
    
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    api_type = db.Column(db.String(50), nullable=False)  # 'rest', 'graphql', etc.
    endpoint = db.Column(db.String(500), nullable=False)
    method = db.Column(db.String(20), default='GET')
    headers = db.Column(JSON)
    auth_type = db.Column(db.String(50))  # 'bearer', 'apikey', 'basic', etc.
    auth_value = db.Column(db.String(500))
    params_template = db.Column(JSON)  # Template for query parameters
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'api_type': self.api_type,
            'endpoint': self.endpoint,
            'method': self.method,
            'headers': self.headers,
            'auth_type': self.auth_type,
            'params_template': self.params_template,
            'created_at': self.created_at.isoformat()
        }
