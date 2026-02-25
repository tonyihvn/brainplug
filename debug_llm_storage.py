#!/usr/bin/env python3
"""Debug LLM model storage and initialization"""

from app import app
from backend.services.settings_service import SettingsService
from backend.services.llm_service import LLMService

with app.app_context():
    settings_service = SettingsService()
    
    print("\n" + "="*70)
    print("DEBUGGING LLM MODEL STORAGE")
    print("="*70)
    
    # Get all LLM models
    llms = settings_service.get_llm_settings()
    
    print(f"\nFound {len(llms)} LLM model(s):")
    for llm in llms:
        print(f"\n  Model: {llm.get('name')}")
        print(f"    ID: {llm.get('id')}")
        print(f"    Type: {llm.get('model_type')}")
        print(f"    Model ID: {llm.get('model_id')}")
        print(f"    Endpoint: {llm.get('api_endpoint')}")
        print(f"    Active: {llm.get('is_active')}")
        print(f"    Priority: {llm.get('priority')}")
        print(f"    Keys: {list(llm.keys())}")
    
    # Try to initialize LLMService
    print("\n" + "="*70)
    print("INITIALIZING LLM SERVICE")
    print("="*70)
    
    llm_service = LLMService()
    print(f"\nLLMService status:")
    print(f"  model_type: {llm_service.model_type}")
    print(f"  ollama_available: {llm_service.ollama_available}")
    print(f"  ollama_host: {llm_service.ollama_host}")
    print(f"  ollama_model: {llm_service.ollama_model}")
    print(f"  model: {llm_service.model}")
