#!/usr/bin/env python3
"""
Fix corrupted LLM data and ensure only one active model.
"""

from app import app
from backend.models.settings import LLMModel
from backend.models import db
from backend.services.settings_service import SettingsService
import uuid

with app.app_context():
    print("\n" + "="*70)
    print("FIXING LLM DATA")
    print("="*70)
    
    settings_service = SettingsService()
    
    # Get all LLM models from SQL
    sql_models = LLMModel.query.all()
    print(f"\nFound {len(sql_models)} models in SQL database")
    
    # Fix issues
    print("\n[1] Fixing model type mismatches...")
    for model in sql_models:
        # Fix Ollama model with wrong type
        if model.name == "Ollama" and model.model_type == "gemini":
            print(f"  Fixing: {model.name}")
            model.model_type = "ollama"
            db.session.commit()
        
        # Fix other type issues
        if model.model_id and "mistral" in str(model.model_id).lower() and model.model_type != "ollama":
            if model.model_type != "gemini":  # Don't change intentional Gemini models
                print(f"  Fixing Mistral type for: {model.name}")
                model.model_type = "ollama"
                db.session.commit()
    
    print("\n[2] Ensuring only one active model...")
    active_models = LLMModel.query.filter_by(is_active=True).all()
    print(f"  Found {len(active_models)} active models")
    
    if len(active_models) > 1:
        print(f"  Deactivating extras, keeping highest priority...")
        # Sort by priority and keep the first one
        sorted_models = sorted(active_models, key=lambda x: x.priority)
        for model in sorted_models[1:]:
            print(f"    Deactivating: {model.name}")
            model.is_active = False
            db.session.commit()
    
    # Activate a working Ollama model if no good model is active
    print("\n[3] Ensuring a working model is active...")
    active = LLMModel.query.filter_by(is_active=True).first()
    
    if not active or (active.model_type not in ['ollama', 'gemini', 'claude']):
        print("  No proper active model found, activating Ollama if it exists...")
        ollama = LLMModel.query.filter_by(model_type='ollama').first()
        if ollama:
            # Deactivate all others
            for m in LLMModel.query.filter_by(is_active=True).all():
                m.is_active = False
            # Activate this one
            ollama.is_active = True
            ollama.priority = 0
            db.session.commit()
            print(f"  ✓ Activated: {ollama.name}")
        else:
            print("  No Ollama model found")
    
    # Sync to RAG
    print("\n[4] Syncing all models to RAG database...")
    from backend.utils.rag_database import RAGDatabase
    rag_db = RAGDatabase()
    
    for model in LLMModel.query.all():
        llm_data = {
            'id': model.id,
            'name': model.name,
            'model_type': model.model_type,
            'model_id': model.model_id,
            'api_key': model.api_key or '',
            'api_endpoint': model.api_endpoint or '',
            'is_active': model.is_active,
            'priority': model.priority,
            'config': getattr(model, 'config', {})
        }
        try:
            rag_db.save_setting(model.id, llm_data)
            print(f"  ✓ Synced: {model.name}")
        except Exception as e:
            print(f"  ✗ Failed to sync {model.name}: {str(e)}")
    
    # Verify
    print("\n[5] Verifying fixes...")
    from backend.services.llm_service import LLMService
    llm_service = LLMService()
    
    if llm_service.model_type:
        print(f"  ✓ LLMService initialized with: {llm_service.model_type}")
        if llm_service.model_type == 'ollama':
            print(f"    Model: {llm_service.ollama_model}")
            print(f"    Host: {llm_service.ollama_host}")
    else:
        print(f"  ✗ LLMService still not initialized")
    
    print("\n" + "="*70)
    print("✓ CLEANUP COMPLETE")
    print("="*70)
