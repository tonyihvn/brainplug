#!/usr/bin/env python3
"""Test database connection with the new absolute path configuration."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import app, logger

def test_db_connection():
    """Test database connection and schema creation."""
    try:
        print("=" * 60)
        print("Testing Database Connection")
        print("=" * 60)
        
        # Get the configured database URL
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
        print(f"✓ Database URL: {db_url}")
        
        # Test within app context
        with app.app_context():
            from backend.models import db
            from backend.models.conversation import Conversation
            from backend.models.rag import BusinessRule, SchemaInfo
            
            # Check if tables exist
            print("\nChecking database tables...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"✓ Found {len(tables)} tables: {', '.join(tables)}")
            
            # Try to query business rules
            print("\nAttempting to query business_rules...")
            rules = BusinessRule.query.all()
            print(f"✓ Successfully queried business_rules: {len(rules)} rules found")
            
            # Try to query conversations
            print("\nAttempting to query conversations...")
            conversations = Conversation.query.all()
            print(f"✓ Successfully queried conversations: {len(conversations)} conversations found")
            
        print("\n" + "=" * 60)
        print("✓ All database tests PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n✗ Database test FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_db_connection()
    sys.exit(0 if success else 1)
