#!/usr/bin/env python3
"""Fix model priorities to ensure Ollama is preferred over Gemini."""
import sys
sys.path.insert(0, 'c:\\Users\\Ogochukwu\\Desktop\\gemini-mcp')

from backend.models import db, init_db
from backend.models.settings import LLMModel
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gemini_mcp.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    init_db()
    
    print("\n" + "="*60)
    print("Fixing Model Priorities")
    print("="*60)
    
    # Set Mistral priority to 0 (highest)
    mistral = LLMModel.query.filter_by(model_type='ollama', model_id='mistral:latest').first()
    if mistral:
        mistral.priority = 0
        print(f"\n✅ Set Mistral priority to 0 (highest)")
    
    # Set Gemini priority to 10 (fallback)
    gemini = LLMModel.query.filter_by(model_type='gemini').first()
    if gemini:
        gemini.priority = 10
        print(f"✅ Set Gemini priority to 10 (fallback)")
    
    db.session.commit()
    
    print(f"\n" + "-"*60)
    print("Final Priority Order:")
    print("-"*60)
    
    all_models = LLMModel.query.order_by(LLMModel.priority).all()
    for model in all_models:
        status = "🟢 ACTIVE" if model.is_active else "🔴 INACTIVE"
        print(f"[Priority {model.priority}] {status} {model.name} ({model.model_id})")
    
    # Show which one will be selected
    active = LLMModel.query.filter_by(is_active=True).order_by(LLMModel.priority).first()
    if active:
        print(f"\n{'='*60}")
        print(f"✅ WILL BE LOADED: {active.name} ({active.model_id})")
        print(f"{'='*60}")
