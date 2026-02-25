"""Database models initialization."""
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db():
    """Initialize database tables."""
    from backend.models.conversation import Conversation, Message
    from backend.models.settings import DatabaseSetting, LLMModel, APIConfig
    from backend.models.rag import BusinessRule, SchemaInfo
    from backend.models.action import ScheduledActivity, ActionHistory, Report
    try:
        db.create_all()
    except Exception as e:
        # Don't fail application startup if the configured SQL database is
        # unreachable (e.g. MySQL not running). Log and continue — the app
        # can function in degraded mode and database tables can be created
        # later when the DB becomes available.
        from backend.utils.logger import setup_logger
        logger = setup_logger(__name__)
        logger.warning(f"Database create_all() failed at startup — continuing without DB: {e}")
