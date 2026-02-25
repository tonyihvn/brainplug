#!/usr/bin/env python3
"""Manual trigger for RAG population."""

from app import app, db
from backend.models.settings import DatabaseSetting
from backend.services.settings_service import SettingsService

with app.app_context():
    # Get the active database
    active_db = DatabaseSetting.query.filter_by(is_active=True).first()
    
    if not active_db:
        print("No active database found!")
        exit(1)
    
    print(f"Found active database: {active_db.name}")
    print(f"Database ID: {active_db.id}")
    print(f"Type: {active_db.db_type}")
    print(f"Host: {active_db.host}")
    print(f"Database: {active_db.database}")
    
    print("\n" + "=" * 60)
    print("Manually triggering RAG population...")
    print("=" * 60 + "\n")
    
    settings_service = SettingsService()
    
    try:
        settings_service._populate_rag_schema(active_db)
        print("\n✓ RAG population completed!")
    except Exception as e:
        print(f"\n✗ Error during RAG population: {str(e)}")
        import traceback
        traceback.print_exc()
