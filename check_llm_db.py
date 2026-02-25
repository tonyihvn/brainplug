#!/usr/bin/env python3
"""Check if Ollama Mistral is configured in the database."""
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
    print("LLMModel Database Check")
    print("="*60)
    
    # Get all models
    all_models = LLMModel.query.all()
    print(f"\nTotal models in DB: {len(all_models)}")
    
    for model in all_models:
        print(f"\n  Model: {model.name}")
        print(f"    - Type: {model.model_type}")
        print(f"    - ID: {model.model_id}")
        print(f"    - Active: {model.is_active}")
        print(f"    - Priority: {model.priority}")
    
    # Check for active Ollama model
    active_ollama = LLMModel.query.filter_by(model_type='ollama', is_active=True).first()
    if active_ollama:
        print(f"\n✅ Active Ollama Model Found: {active_ollama.model_id}")
    else:
        print(f"\n❌ No active Ollama model found")
    
    # Check for active Gemini model
    active_gemini = LLMModel.query.filter_by(model_type='gemini', is_active=True).first()
    if active_gemini:
        print(f"⚠️  Active Gemini Model Found: {active_gemini.model_id}")
    else:
        print(f"✅ No active Gemini model")
    
    print("\n" + "="*60)
