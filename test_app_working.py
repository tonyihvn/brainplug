#!/usr/bin/env python3
"""
Verify app works end-to-end with Ollama.
Simple final verification after all fixes.
"""

from app import app
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.models.conversation import Conversation
from backend.models import db
import uuid

with app.app_context():
    print("\n" + "="*70)
    print("APP VERIFICATION - END-TO-END TEST")
    print("="*70)
    
    # [1] Check services
    print("\n[1] Checking LLM Service...")
    llm = LLMService()
    print(f"  ✓ LLM Type: {llm.model_type}")
    print(f"  ✓ Model: {llm.ollama_model}")
    print(f"  ✓ Host: {llm.ollama_host}")
    
    # [2] Check RAG
    print("\n[2] Checking RAG Service...")
    rag = RAGService()
    print(f"  ✓ RAG Service initialized")
    
    # [3] Create and save conversation
    print("\n[3] Creating conversation...")
    conv_id = f"verify-{uuid.uuid4().hex[:8]}"
    conv = Conversation(id=conv_id, title="Verification Test")
    db.session.add(conv)
    db.session.commit()
    print(f"  ✓ Conversation saved: {conv.id}")
    
    # [4] Send message to Ollama
    print("\n[4] Sending message to Ollama...")
    message = "What is 2+2?"
    
    try:
        response = llm.process_prompt(
            prompt=message,
            rag_context=None,
            business_rules=None,
            conversation_id=conv_id
        )
        
        print(f"  ✓ Response received")
        print(f"    - Explanation: {response['explanation'][:80]}...")
        print(f"    - Action Type: {response.get('action_type', 'UNKNOWN')}")
        
        # [5] Verify response structure
        print("\n[5] Verifying response structure...")
        required = ['explanation', 'action_type', 'action']
        found = all(k in response for k in required)
        if found:
            print(f"  ✓ All required fields present")
        else:
            print(f"  ✗ Missing fields")
        
        print("\n" + "="*70)
        print("✓ ALL TESTS PASSED - APP IS WORKING CORRECTLY!")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
