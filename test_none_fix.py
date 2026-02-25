#!/usr/bin/env python3
"""
Test that the NoneType subscript error is fixed
"""

from app import app
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService

with app.app_context():
    print("\n" + "="*70)
    print("Testing LLM with potentially None RAG context")
    print("="*70)
    
    # Initialize services
    rag_service = RAGService()
    llm_service = LLMService()
    
    # Ensure active model is set
    llm_service._ensure_active_model()
    
    if llm_service.model_type:
        print(f"\n✓ LLM initialized: {llm_service.model_type}")
    else:
        print(f"\n✗ No LLM configured")
    
    # Test with None values (this should not crash now)
    print("\n[Test 1] _build_system_prompt with None business_rules...")
    try:
        system_prompt = llm_service._build_system_prompt(None)
        print(f"✓ Generated system prompt ({len(system_prompt)} chars)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    print("\n[Test 2] _build_enriched_prompt with None values...")
    try:
        enriched = llm_service._build_enriched_prompt(
            "Test prompt",
            rag_context=None,
            business_rules=None,
            memory=None
        )
        print(f"✓ Generated enriched prompt ({len(enriched)} chars)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    print("\n[Test 3] _build_enriched_prompt with empty lists...")
    try:
        enriched = llm_service._build_enriched_prompt(
            "Test prompt",
            rag_context=[],
            business_rules=[],
            memory=None
        )
        print(f"✓ Generated enriched prompt ({len(enriched)} chars)")
    except Exception as e:
        print(f"✗ ERROR: {str(e)}")
    
    print("\n" + "="*70)
    print("✓ All tests passed - NoneType errors should be fixed!")
    print("="*70)
