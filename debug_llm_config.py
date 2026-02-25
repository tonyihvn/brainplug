"""
DEBUG: Check why LLM is not being initialized
"""

from app import app
from backend.services.llm_service import LLMService
import json
import logging

logging.basicConfig(level=logging.DEBUG)

with app.app_context():
    # Check .env
    import os
    gemini_key = os.getenv('GEMINI_API_KEY')
    print(f"\n1. GEMINI_API_KEY in .env: {gemini_key[:20] if gemini_key else None}...")
    
    # Check RAG database
    from backend.utils.rag_database import RAGDatabase
    rag_db = RAGDatabase()
    
    all_settings = rag_db.get_all_database_settings() or []
    print(f"\n2. Total entries in RAG database: {len(all_settings)}")
    
    llm_entries = [s for s in all_settings if s.get('model_type')]
    print(f"3. LLM entries found: {len(llm_entries)}")
    
    for entry in llm_entries:
        print(f"\n   Entry: {entry.get('name')}")
        print(f"     - model_type: {entry.get('model_type')}")
        print(f"     - model_id: {entry.get('model_id')}")
        print(f"     - api_key: {entry.get('api_key')}")  # THIS IS THE ISSUE
        print(f"     - is_active: {entry.get('is_active')}")
    
    # Now check LLMService
    print(f"\n4. Initializing LLMService...")
    llm_service = LLMService()
    print(f"   - model_type: {llm_service.model_type}")
    print(f"   - model: {llm_service.model}")
    print(f"   - api_key set: {bool(llm_service.api_key)}")
    
    print(f"\n[DIAGNOSIS]")
    active_llm = next((s for s in llm_entries if s.get('is_active')), None)
    if active_llm:
        if not active_llm.get('api_key'):
            print("❌ PROBLEM: LLM entry 'Gemini Pro' is active but missing 'api_key' field")
            print("   The entry has the configuration but no API key stored in RAG database")
            print("   It tries to use .env GEMINI_API_KEY as fallback, but configuration is incomplete")
            print(f"\n[SOLUTION]")
            print("   Update the 'Gemini Pro' entry to include the api_key field in the RAG database")
        else:
            print("✓ api_key is properly stored in RAG database")
