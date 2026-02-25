"""Action-related models."""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSON
from backend.models import db


class ScheduledActivity(db.Model):
    """Scheduled activities for later execution."""
    __tablename__ = 'scheduled_activities'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36))
    title = db.Column(db.String(255), nullable=False)
    action_type = db.Column(db.String(50), nullable=False)  # 'url_read', 'api_call', 'email', 'query', 'report'
    action_data = db.Column(JSON, nullable=False)
    scheduled_for = db.Column(db.DateTime, nullable=False)
    recurrence = db.Column(db.String(50))  # 'daily', 'weekly', 'monthly', etc.
    is_active = db.Column(db.Boolean, default=True)
    last_executed = db.Column(db.DateTime)
    next_execution = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'title': self.title,
            'action_type': self.action_type,
            'action_data': self.action_data,
            'scheduled_for': self.scheduled_for.isoformat() if self.scheduled_for else None,
            'recurrence': self.recurrence,
            'is_active': self.is_active,
            'last_executed': self.last_executed.isoformat() if self.last_executed else None,
            'next_execution': self.next_execution.isoformat() if self.next_execution else None,
            'created_at': self.created_at.isoformat()
        }


class ActionHistory(db.Model):
    """History of executed actions."""
    __tablename__ = 'action_history'
    
    id = db.Column(db.String(36), primary_key=True)
    conversation_id = db.Column(db.String(36))
    action_type = db.Column(db.String(50), nullable=False)
    action_data = db.Column(JSON, nullable=False)
    result = db.Column(JSON)
    status = db.Column(db.String(50), default='pending')  # 'pending', 'executing', 'success', 'failed'
    error_message = db.Column(db.Text)
    executed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'conversation_id': self.conversation_id,
            'action_type': self.action_type,
            'action_data': self.action_data,
            'result': self.result,
            'status': self.status,
            'error_message': self.error_message,
            'executed_at': self.executed_at.isoformat()
        }


class Report(db.Model):
    """Generated reports from prompt results."""
    __tablename__ = 'reports'
    
    id = db.Column(db.String(36), primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    report_type = db.Column(db.String(50), nullable=False)  # 'summary', 'detailed', 'chart', etc.
    data = db.Column(JSON, nullable=False)
    action_ids = db.Column(JSON)  # References to actions that contributed to report
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'report_type': self.report_type,
            'data': self.data,
            'action_ids': self.action_ids,
            'created_at': self.created_at.isoformat()
        }
