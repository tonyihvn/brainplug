"""Conversation and Message models."""
from datetime import datetime
from sqlalchemy import JSON
from backend.models import db


class Conversation(db.Model):
    """Represents a conversation session."""
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_messages=False):
        """Convert to dictionary."""
        data = {
            'id': self.id,
            'title': self.title,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        if include_messages:
            data['messages'] = [m.to_dict() for m in self.messages]
        return data


class Message(db.Model):
    """Represents a message in a conversation."""
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    action_data = db.Column(JSON)  # Store suggested action
    action_executed = db.Column(db.Boolean, default=False)
    action_result = db.Column(JSON)  # Store action execution result
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'role': self.role,
            'content': self.content,
            'action_data': self.action_data,
            'action_executed': self.action_executed,
            'action_result': self.action_result,
            'created_at': self.created_at.isoformat()
        }
