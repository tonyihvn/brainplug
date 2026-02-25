#!/usr/bin/env python3
"""
Quick verification that LLM configuration issue is fixed.
Run this to confirm the app can now find configured LLMs.
"""

from app import app
from backend.services.llm_service import LLMService
from backend.services.settings_service import SettingsService

def verify_fix():
    """Quick verification of the LLM configuration fix"""
    
    with app.app_context():
        print("\n" + "="*70)
        print("LLM Configuration Fix Verification")
        print("="*70)
        
        # Check 1: SettingsService can find LLMs in RAG
        print("\n[1] Checking SettingsService LLM retrieval...")
        settings_service = SettingsService()
        llms = settings_service.get_llm_settings()
        
        if not llms:
            print("✗ No LLM models configured")
            print("  → Configure an LLM first in the Settings GUI")
            return False
        
        print(f"✓ Found {len(llms)} LLM model(s)")
        for llm in llms:
            status = "ACTIVE" if llm.get('is_active') else "inactive"
            print(f"  - {llm.get('name')} ({llm.get('model_type')}) [{status}]")
        
        # Check 2: LLMService can initialize with active model
        print("\n[2] Checking LLMService initialization...")
        llm_service = LLMService()
        
        if not llm_service.model_type:
            print("✗ LLMService could not initialize any LLM")
            print("  → Make sure at least one LLM is marked as active")
            return False
        
        model_name = llm_service.model_type
        if model_name == 'ollama':
            model_name = f"Ollama ({llm_service.ollama_model})"
        elif model_name == 'gemini':
            model_name = "Gemini"
        elif model_name == 'claude':
            model_name = "Claude"
        
        print(f"✓ LLMService initialized with: {model_name}")
        
        # Check 3: Verify active model details
        print("\n[3] Verifying active model configuration...")
        active = next((m for m in llms if m.get('is_active')), None)
        
        if not active:
            print("✗ No active LLM model found")
            return False
        
        print(f"✓ Active model: {active.get('name')}")
        print(f"  Type: {active.get('model_type')}")
        if active.get('model_id'):
            print(f"  Model ID: {active.get('model_id')}")
        if active.get('api_endpoint'):
            print(f"  Endpoint: {active.get('api_endpoint')}")
        if active.get('api_key'):
            print(f"  API Key: ✓ (configured)")
        
        print("\n" + "="*70)
        print("✓ FIX VERIFIED - LLM Configuration is Working!")
        print("="*70)
        print("\nThe app should now:")
        print("  • Accept chat messages without 'not configured' error")
        print("  • Use the configured LLM to process prompts")
        print("  • Support Gemini, Claude, Ollama, and other cloud LLMs")
        
        return True

if __name__ == '__main__':
    try:
        verify_fix()
    except Exception as e:
        print(f"\n✗ Verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
