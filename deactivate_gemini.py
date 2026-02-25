#!/usr/bin/env python3
"""Deactivate Gemini and ensure Ollama Mistral is configured properly."""
import sys
sys.path.insert(0, 'c:\\Users\\Ogochukwu\\Desktop\\gemini-mcp')

from backend.models import db, init_db
from backend.models.settings import LLMModel
from flask import Flask
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gemini_mcp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    init_db()
    
    print("\n" + "="*60)
    print("LLM Configuration Update")
    print("="*60)
    
    # Find and deactivate all Gemini models
    gemini_models = LLMModel.query.filter_by(model_type='gemini').all()
    if gemini_models:
        print(f"\nDeactivating {len(gemini_models)} Gemini model(s)...")
        for model in gemini_models:
            model.is_active = False
            print(f"  - Deactivated: {model.name} (ID: {model.model_id})")
        db.session.commit()
    
    # Check for Ollama Mistral
    ollama_models = LLMModel.query.filter_by(model_type='ollama').all()
    
    if ollama_models:
        print(f"\nFound {len(ollama_models)} Ollama model(s):")
        for model in ollama_models:
            print(f"  - {model.name} (ID: {model.model_id}, Priority: {model.priority}, Active: {model.is_active})")
            # Ensure it's active and has highest priority
            model.is_active = True
            model.priority = 0
            print(f"    → Updated: Active=True, Priority=0")
        db.session.commit()
    else:
        print(f"\n⚠️  No Ollama models found in DB. Adding Mistral...")
        mistral = LLMModel(
            id=str(uuid.uuid4()),
            name="Local Mistral (mistral:latest)",
            model_type='ollama',
            model_id='mistral:latest',
            priority=0,
            is_active=True
        )
        db.session.add(mistral)
        db.session.commit()
        print(f"  ✅ Created: {mistral.name}")
    
    # Display final state
    print(f"\n" + "-"*60)
    print("Final LLM Model Configuration:")
    print("-"*60)
    
    all_models = LLMModel.query.order_by(LLMModel.priority).all()
    for model in all_models:
        status = "🟢 ACTIVE" if model.is_active else "🔴 INACTIVE"
        print(f"\n{status} {model.name}")
        print(f"   Type: {model.model_type} | ID: {model.model_id} | Priority: {model.priority}")
    
    # Identify active model
    active = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.priority).first()
    if active:
        print(f"\n" + "="*60)
        print(f"✅ ACTIVE LLM: {active.name} ({active.model_id})")
        print("="*60)
    else:
        print(f"\n" + "="*60)
        print(f"❌ NO ACTIVE LLM CONFIGURED")
        print("="*60)
