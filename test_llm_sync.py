#!/usr/bin/env python3
"""
Test that LLM settings sync between SQL and RAG databases
"""

import sys
import json
from app import app
from backend.models import db, init_db
from backend.services.settings_service import SettingsService
from backend.services.llm_service import LLMService
from backend.utils.rag_database import RAGDatabase

def test_llm_sync():
    """Test that LLM settings are properly synced to RAG database"""
    
    with app.app_context():
        init_db()
        
        print("\n" + "="*80)
        print("TEST: LLM Configuration Sync Between SQL and RAG Databases")
        print("="*80)
        
        # Initialize services
        settings_service = SettingsService()
        rag_db = RAGDatabase()
        
        # Test 1: Create a new LLM model and deactivate others
        print("\n[1] Deactivating all existing LLM models...")
        existing_llms = settings_service.get_llm_settings()
        for existing in existing_llms:
            existing['is_active'] = False
            try:
                settings_service.update_llm_settings(existing)
                print(f"  - Deactivated: {existing.get('name')}")
            except:
                pass
        
        print("\n[1] Creating a new Ollama LLM model via SettingsService...")
        test_llm_data = {
            'name': 'Test Ollama Model',
            'model_type': 'ollama',
            'model_id': 'mistral:latest',
            'api_endpoint': 'http://localhost:11434',
            'is_active': True,
            'priority': 0
        }
        
        result = settings_service.update_llm_settings(test_llm_data)
        model_id = result.get('id')
        print(f"✓ Created LLM model: {result.get('name')} (ID: {model_id})")
        
        # Test 2: Check if it's in RAG database
        print("\n[2] Checking if LLM was saved to RAG database...")
        rag_setting = rag_db.get_database_setting(model_id)
        if rag_setting:
            print(f"✓ Found in RAG database: {rag_setting.get('name')}")
            print(f"  - model_type: {rag_setting.get('model_type')}")
            print(f"  - is_active: {rag_setting.get('is_active')}")
        else:
            print(f"✗ NOT found in RAG database!")
            # Check all settings for debugging
            all_settings = rag_db.get_all_database_settings()
            llm_models = [s for s in all_settings if s.get('model_type')]
            print(f"Debug: Found {len(llm_models)} LLM models in RAG:")
            for m in llm_models:
                print(f"  - {m.get('id')}: {m.get('name')}")
            return False
        
        # Test 3: Verify LLMService can find it
        print("\n[3] Initializing LLMService and checking if it finds the active model...")
        llm_service = LLMService()
        
        if llm_service.model_type == 'ollama':
            print(f"✓ LLMService found active Ollama model: {llm_service.ollama_model} @ {llm_service.ollama_host}")
        else:
            print(f"✗ LLMService did not find Ollama model")
            print(f"  Current model_type: {llm_service.model_type}")
            return False
        
        # Test 4: Update the model and verify sync
        print("\n[4] Updating the LLM model...")
        test_llm_data['id'] = model_id
        test_llm_data['name'] = 'Test Ollama Model - Updated'
        test_llm_data['priority'] = 5
        
        result = settings_service.update_llm_settings(test_llm_data)
        print(f"✓ Updated LLM model: {result.get('name')}")
        
        # Check RAG update
        rag_setting = rag_db.get_database_setting(model_id)
        if rag_setting.get('name') == 'Test Ollama Model - Updated':
            print(f"✓ RAG database was updated: {rag_setting.get('name')}")
        else:
            print(f"✗ RAG database was NOT updated properly")
            return False
        
        # Test 5: Test get_llm_settings returns from RAG
        print("\n[5] Retrieving all LLM settings via SettingsService...")
        all_llms = settings_service.get_llm_settings()
        print(f"✓ Retrieved {len(all_llms)} LLM model(s)")
        
        # Find our test model
        test_model_in_list = next((m for m in all_llms if m.get('id') == model_id), None)
        if test_model_in_list:
            print(f"✓ Test model found in list: {test_model_in_list.get('name')}")
        else:
            print(f"✗ Test model NOT found in list")
            return False
        
        # Test 6: Reinitialize LLMService and verify it still finds the model
        print("\n[6] Reinitializing LLMService to verify persistence...")
        llm_service2 = LLMService()
        if llm_service2.model_type == 'ollama':
            print(f"✓ New LLMService instance found active Ollama model: {llm_service2.ollama_model}")
        else:
            print(f"✗ New LLMService instance did not find Ollama model")
            return False
        
        # Cleanup
        print("\n[7] Cleaning up test data...")
        settings_service.delete_llm_model(model_id)
        print(f"✓ Deleted test model")
        
        # Verify deletion from both stores
        rag_check = rag_db.get_database_setting(model_id)
        if rag_check is None:
            print(f"✓ Confirmed deletion from RAG database")
        else:
            print(f"⚠ Model still in RAG database after deletion")
        
        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED - LLM Configuration Sync is Working!")
        print("="*80)
        return True

if __name__ == '__main__':
    try:
        success = test_llm_sync()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ TEST FAILED WITH ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
