#!/usr/bin/env python3
from app import app
from backend.utils.rag_database import RAGDatabase

with app.app_context():
    rag_db = RAGDatabase()
    all_settings = rag_db.get_all_database_settings()
    print('All settings in RAG database:')
    for s in all_settings:
        if 'model_type' in s:
            print(f'  - ID: {s.get("id")}, Name: {s.get("name")}, Type: {s.get("model_type")}')
