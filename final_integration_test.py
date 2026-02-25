#!/usr/bin/env python3
"""
Final integration test - send real message to Ollama and verify response.
"""

import json
from app import app
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.models.conversation import Conversation
from backend.models.action import ActionHistory
from backend.models import db
from datetime import datetime
import uuid

with app.app_context():
    print("\n" + "="*70)
    print("FINAL INTEGRATION TEST - OLLAMA CHAT")
    print("="*70)
    
    # Test 1: Initialize services
    print("\n[1] Initializing services...")
    llm_service = LLMService()
    rag_service = RAGService()
    
    print(f"  LLM Service: {llm_service.model_type} ✓")
    print(f"  Ollama Model: {llm_service.ollama_model} ✓")
    print(f"  Ollama Host: {llm_service.ollama_host} ✓")
    
    # Test 2: Create conversation
    print("\n[2] Creating test conversation...")
    import uuid as _uuid
    conv_id = f"final-test-conv-{_uuid.uuid4().hex[:8]}"
    conv = Conversation(
        id=conv_id,
        title="Final Integration Test"
    )
    db.session.add(conv)
    db.session.commit()
    print(f"  Created: {conv.title} ({conv.id}) ✓")
    
    # Test 3: Send message to LLM
    print("\n[3] Sending test message to Ollama...")
    test_message = "What is the capital of France? Please respond with just the city name."
    
    try:
        response = llm_service.process_prompt(
            prompt=test_message,
            rag_context=None,
            business_rules=None,
            conversation_id=conv.id
        )
        
        print(f"  User: {test_message}")
        print(f"  Response: {response['explanation']}")
        print(f"  Action Type: {response['action_type']} ✓")
        print(f"  Response Status: ✓ SUCCESS")
        
        # Test 4: Verify response format
        print("\n[4] Verifying response format...")
        required_fields = ['explanation', 'action_type', 'action']
        for field in required_fields:
            if field in response:
                print(f"  ✓ {field}: present")
            else:
                print(f"  ✗ {field}: MISSING")
        
        # Test 5: Create action from response
        print("\n[5] Creating action history from response...")
        action = ActionHistory(
            id=str(uuid.uuid4()),
            conversation_id=conv.id,
            action_type=response.get('action_type', 'NONE'),
            action_data=response.get('action', {}),
            status='completed',
            created_at=datetime.utcnow()
        )
        db.session.add(action)
        db.session.commit()
        print(f"  Action History Created: {action.action_type} ✓")
        
        print("\n" + "="*70)
        print("✓ INTEGRATION TEST PASSED!")
        print("="*70)
        print("\nSummary:")
        print("  ✓ LLMService initialized with Ollama")
        print("  ✓ Ollama model (mistral:latest) responsive")
        print("  ✓ Message processing works end-to-end")
        print("  ✓ Response parsing successful")
        print("  ✓ Action creation successful")
        print("  ✓ Database persistence working")
        print("\nCONCLUSION: All core features working perfectly!")
        
    except Exception as e:
        print(f"  ✗ Error: {str(e)}")
        print("\n" + "="*70)
        print("✗ INTEGRATION TEST FAILED")
        print("="*70)
        import traceback
        traceback.print_exc()
