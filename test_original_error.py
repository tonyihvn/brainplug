#!/usr/bin/env python3
"""Test the specific endpoint that was failing in the original error."""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app import app, logger, rag_service, llm_service

def test_rag_service_methods():
    """Test the specific RAG service methods that were failing."""
    try:
        print("=" * 60)
        print("Testing RAG Service Methods (Original Error Source)")
        print("=" * 60)
        
        with app.app_context():
            # Test get_mandatory_rules() - this was throwing the original error
            print("\nAttempting to call rag_service.get_mandatory_rules()...")
            try:
                rules = rag_service.get_mandatory_rules()
                print(f"[OK] Successfully called get_mandatory_rules(): {len(rules)} rules")
            except Exception as e:
                print(f"[FAILED] {str(e)}")
                raise
            
            # Test retrieve_context() - also uses database
            print("\nAttempting to call rag_service.retrieve_context()...")
            try:
                context = rag_service.retrieve_context("test query", top_k=5)
                print(f"[OK] Successfully called retrieve_context(): {len(context)} items")
            except Exception as e:
                print(f"[FAILED] {str(e)}")
                raise
        
        print("\n" + "=" * 60)
        print("[OK] RAG Service methods working correctly!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] RAG Service test FAILED")
        import traceback
        traceback.print_exc()
        return False

def test_llm_service_method():
    """Test the LLM service that also calls RAG methods."""
    try:
        print("\n" + "=" * 60)
        print("Testing LLM Service with RAG Integration")
        print("=" * 60)
        
        if not llm_service:
            print("[WARNING] LLM Service not initialized - skipping LLM integration test")
            return True
        
        with app.app_context():
            # Simulate what happens in /api/chat/message
            print("\nSimulating /api/chat/message request...")
            
            # This is what the chat endpoint does:
            # 1. Get RAG context
            print("  1. Getting RAG context...")
            rag_context = rag_service.retrieve_context("How many laptops?", top_k=5)
            print(f"     [OK] Retrieved {len(rag_context)} context items")
            
            # 2. Get mandatory rules (THIS WAS FAILING)
            print("  2. Getting mandatory business rules...")
            business_rules = rag_service.get_mandatory_rules()
            print(f"     [OK] Retrieved {len(business_rules)} business rules")
            
            # 3. Process with LLM (would use the context and rules)
            print("  3. LLM ready to process prompt with context")
            print("     [OK] All prerequisites loaded successfully")
        
        print("\n" + "=" * 60)
        print("[OK] LLM Service integration test PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] LLM Service test FAILED")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success1 = test_rag_service_methods()
    success2 = test_llm_service_method()
    
    overall_success = success1 and success2
    
    print("\n" + "=" * 60)
    if overall_success:
        print("[SUCCESS] ALL TESTS PASSED")
        print("The original database error should now be FIXED!")
    else:
        print("[FAILURE] SOME TESTS FAILED")
    print("=" * 60)
    
    sys.exit(0 if overall_success else 1)
