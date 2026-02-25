#!/usr/bin/env python3
"""
Migrate legacy LLM settings to new RAG-synced format.
Run this once after the fix is applied.
"""

from app import app
from backend.models import db, init_db
from backend.models.settings import LLMModel
from backend.services.settings_service import SettingsService

def migrate_llm_settings():
    """Migrate all existing LLM models to RAG database"""
    
    with app.app_context():
        init_db()
        
        print("\n" + "="*70)
        print("LLM Settings Migration to RAG Database")
        print("="*70)
        
        settings_service = SettingsService()
        
        # Get all LLMModels from SQL
        print("\n[1] Reading LLM models from SQL database...")
        sql_models = LLMModel.query.all()
        
        if not sql_models:
            print("✗ No LLM models found in SQL database")
            print("  Configure LLM models first via the Settings GUI")
            return
        
        print(f"✓ Found {len(sql_models)} LLM model(s) in SQL:")
        for model in sql_models:
            print(f"  - {model.name} ({model.model_type})")
        
        # Migrate each to RAG
        print("\n[2] Syncing models to RAG database...")
        success_count = 0
        
        for model in sql_models:
            try:
                llm_data = {
                    'id': model.id,
                    'name': model.name,
                    'model_type': model.model_type,
                    'model_id': model.model_id,
                    'api_key': model.api_key,
                    'api_endpoint': model.api_endpoint,
                    'is_active': model.is_active,
                    'priority': model.priority,
                    'config': getattr(model, 'config', {})
                }
                settings_service.rag_db.save_setting(model.id, llm_data)
                status = "ACTIVE" if model.is_active else "inactive"
                print(f"  ✓ Synced: {model.name} [{status}]")
                success_count += 1
            except Exception as e:
                print(f"  ✗ Failed to sync {model.name}: {str(e)}")
        
        print(f"\n[3] Migration Result:")
        print(f"✓ Successfully synced {success_count}/{len(sql_models)} LLM models")
        
        # Verify
        print("\n[4] Verification...")
        rag_models = settings_service.get_llm_settings()
        active = next((m for m in rag_models if m.get('is_active')), None)
        
        if active:
            print(f"✓ Active model configured: {active.get('name')}")
        else:
            print("⚠ No active LLM model. Configure one via Settings GUI")
        
        print("\n" + "="*70)
        print("✓ Migration Complete!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Restart the app: python app.py")
        print("  2. Verify with: python verify_llm_fix.py")
        print("  3. Try sending a chat message")

if __name__ == '__main__':
    try:
        migrate_llm_settings()
    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
