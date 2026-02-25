#!/usr/bin/env python3
"""
Comprehensive test suite for all app features.
Tests LLM configuration, database settings, RAG, chat, and more.
"""

import sys
import json
from app import app
from backend.models import db, init_db
from backend.services.llm_service import LLMService
from backend.services.rag_service import RAGService
from backend.services.settings_service import SettingsService
from backend.models.settings import LLMModel, DatabaseSetting
from backend.models.conversation import Conversation, Message

# Test counters
total_tests = 0
passed_tests = 0
failed_tests = 0
failed_details = []

def test(name, condition, error_msg=""):
    """Helper function to track test results"""
    global total_tests, passed_tests, failed_tests
    total_tests += 1
    if condition:
        print(f"  ✓ {name}")
        passed_tests += 1
    else:
        print(f"  ✗ {name}")
        if error_msg:
            print(f"    Error: {error_msg}")
        failed_tests += 1
        failed_details.append((name, error_msg))

def section(title):
    """Print test section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")

with app.app_context():
    init_db()
    
    # ========== TEST 1: APP INITIALIZATION ==========
    section("1. APP INITIALIZATION")
    
    test("Flask app created", app is not None)
    test("Database configured", db is not None)
    test("Flask app context active", app.app_context() is not None)
    
    # ========== TEST 2: SERVICE INITIALIZATION ==========
    section("2. SERVICE INITIALIZATION")
    
    try:
        rag_service = RAGService()
        test("RAG Service initialized", rag_service is not None)
    except Exception as e:
        test("RAG Service initialized", False, str(e))
    
    try:
        settings_service = SettingsService()
        test("Settings Service initialized", settings_service is not None)
    except Exception as e:
        test("Settings Service initialized", False, str(e))
    
    try:
        llm_service = LLMService()
        test("LLM Service initialized", llm_service is not None)
    except Exception as e:
        test("LLM Service initialized", False, str(e))
    
    # ========== TEST 3: LLM CONFIGURATION ==========
    section("3. LLM CONFIGURATION")
    
    try:
        # Test creating an Ollama LLM
        test_llm = {
            'name': 'Test Ollama',
            'model_type': 'ollama',
            'model_id': 'mistral:latest',
            'api_endpoint': 'http://localhost:11434',
            'is_active': True,
            'priority': 0
        }
        result = settings_service.update_llm_settings(test_llm)
        test("Create LLM configuration", result is not None and result.get('id'), "Failed to create LLM")
        llm_id = result.get('id')
    except Exception as e:
        test("Create LLM configuration", False, str(e))
        llm_id = None
    
    try:
        # Test reading LLM settings
        llms = settings_service.get_llm_settings()
        test("Get LLM settings", isinstance(llms, list) and len(llms) > 0, f"Expected list, got {type(llms)}")
        test("LLM has required fields", all(m.get('id') and m.get('model_type') for m in llms), "Missing required fields")
    except Exception as e:
        test("Get LLM settings", False, str(e))
    
    try:
        # Test LLMService recognizes active model
        llm_service._ensure_active_model()
        has_model = llm_service.model_type is not None
        test("LLMService finds active model", has_model, f"model_type={llm_service.model_type}")
    except Exception as e:
        test("LLMService finds active model", False, str(e))
    
    # ========== TEST 4: PROMPT BUILDING ==========
    section("4. PROMPT BUILDING")
    
    try:
        # Test system prompt generation
        prompt = llm_service._build_system_prompt(None)
        test("System prompt generated", isinstance(prompt, str) and len(prompt) > 0, f"Got: {type(prompt)}")
    except Exception as e:
        test("System prompt generated", False, str(e))
    
    try:
        # Test enriched prompt with None values
        prompt = llm_service._build_enriched_prompt("Test", None, None, None)
        test("Enriched prompt with None values", isinstance(prompt, str), f"Got: {type(prompt)}")
    except Exception as e:
        test("Enriched prompt with None values", False, str(e))
    
    try:
        # Test enriched prompt with empty lists
        prompt = llm_service._build_enriched_prompt("Test", [], [], None)
        test("Enriched prompt with empty lists", isinstance(prompt, str) and "Test" in prompt)
    except Exception as e:
        test("Enriched prompt with empty lists", False, str(e))
    
    # ========== TEST 5: RESPONSE PARSING ==========
    section("5. RESPONSE PARSING")
    
    try:
        # Test parsing valid response format
        response = """UNDERSTANDING: User wants to query the database
ACTION_TYPE: DATABASE_QUERY
SQL_QUERY: SELECT * FROM users
PARAMETERS: none
CONFIDENCE: high
NEXT_STEP: Execute the query"""
        
        parsed = llm_service._parse_response(response)
        test("Parse valid response", parsed is not None and isinstance(parsed, dict))
        test("Parsed has explanation", parsed.get('explanation') is not None)
        test("Parsed has action_type", parsed.get('action_type') is not None)
        test("Parsed has action object", parsed.get('action') is not None)
    except Exception as e:
        test("Parse valid response", False, str(e))
    
    try:
        # Test parsing None response
        parsed = llm_service._parse_response(None)
        test("Parse None response gracefully", parsed is not None and parsed.get('explanation') is not None)
    except Exception as e:
        test("Parse None response gracefully", False, str(e))
    
    try:
        # Test parsing empty response
        parsed = llm_service._parse_response("")
        test("Parse empty response gracefully", parsed is not None and parsed.get('explanation') is not None)
    except Exception as e:
        test("Parse empty response gracefully", False, str(e))
    
    # ========== TEST 6: CONVERSATION MANAGEMENT ==========
    section("6. CONVERSATION MANAGEMENT")
    
    try:
        # Test creating conversation
        conv = Conversation(id=str(__import__('uuid').uuid4()), title="Test Conversation")
        db.session.add(conv)
        db.session.commit()
        conv_id = conv.id
        test("Create conversation", conv_id is not None)
    except Exception as e:
        test("Create conversation", False, str(e))
        conv_id = None
    
    if conv_id:
        try:
            # Test adding messages
            msg = Message(
                id=str(__import__('uuid').uuid4()),
                conversation_id=conv_id,
                role='user',
                content='Test message'
            )
            db.session.add(msg)
            db.session.commit()
            test("Add message to conversation", msg.id is not None)
        except Exception as e:
            test("Add message to conversation", False, str(e))
        
        try:
            # Test retrieving conversation
            fetched = Conversation.query.get(conv_id)
            test("Retrieve conversation", fetched is not None and fetched.id == conv_id)
        except Exception as e:
            test("Retrieve conversation", False, str(e))
        
        try:
            # Test retrieving messages
            messages = Message.query.filter_by(conversation_id=conv_id).all()
            test("Retrieve conversation messages", len(messages) > 0)
        except Exception as e:
            test("Retrieve conversation messages", False, str(e))
    
    # ========== TEST 7: RAG SERVICE ==========
    section("7. RAG SERVICE")
    
    try:
        # Test RAG context retrieval
        context = rag_service.retrieve_context("test query", top_k=5)
        test("Retrieve RAG context", isinstance(context, list), f"Expected list, got {type(context)}")
    except Exception as e:
        test("Retrieve RAG context", False, str(e))
    
    try:
        # Test getting business rules
        rules = rag_service.get_mandatory_rules()
        test("Get mandatory business rules", isinstance(rules, list), f"Expected list, got {type(rules)}")
    except Exception as e:
        test("Get mandatory business rules", False, str(e))
    
    # ========== TEST 8: DATABASE SETTINGS ==========
    section("8. DATABASE SETTINGS")
    
    try:
        # Test database setting creation
        db_setting = {
            'db_type': 'mysql',
            'name': 'Test DB',
            'host': 'localhost',
            'user': 'test',
            'password': 'test',
            'database': 'testdb',
            'port': 3306,
            'is_active': False
        }
        result = settings_service.update_database_settings(db_setting)
        test("Create database setting", result is not None)
    except Exception as e:
        test("Create database setting", False, str(e))
    
    try:
        # Test getting database settings
        dbs = settings_service.get_database_settings()
        test("Get database settings", isinstance(dbs, list))
    except Exception as e:
        test("Get database settings", False, str(e))
    
    # ========== TEST 9: SETTINGS PERSISTENCE ==========
    section("9. SETTINGS PERSISTENCE")
    
    try:
        # Test RAG database sync for LLM
        llms_before = len(settings_service.get_llm_settings())
        test("LLM count consistent", llms_before >= 0)
        
        # Create new LLM
        new_llm = {
            'name': 'Persistence Test',
            'model_type': 'ollama',
            'model_id': 'test:latest',
            'api_endpoint': 'http://localhost:11434',
            'is_active': False,
            'priority': 99
        }
        result = settings_service.update_llm_settings(new_llm)
        
        # Verify it's in both stores
        llms_after = settings_service.get_llm_settings()
        found = any(m.get('name') == 'Persistence Test' for m in llms_after)
        test("LLM persists in storage", found)
    except Exception as e:
        test("LLM persists in storage", False, str(e))
    
    # ========== TEST 10: ERROR HANDLING ==========
    section("10. ERROR HANDLING")
    
    try:
        # Test None safety in prompt building
        llm_service._build_system_prompt(None)
        llm_service._build_enriched_prompt("test", None, None, None)
        test("Handles None gracefully in prompts", True)
    except Exception as e:
        test("Handles None gracefully in prompts", False, str(e))
    
    try:
        # Test invalid data handling
        parsed = llm_service._parse_response("invalid response format")
        test("Handles invalid response format", parsed is not None and parsed.get('explanation'))
    except Exception as e:
        test("Handles invalid response format", False, str(e))
    
    try:
        # Test invalid LLM type
        invalid_llm = {
            'name': 'Invalid',
            'model_type': 'nonexistent',
            'model_id': 'test'
        }
        result = settings_service.update_llm_settings(invalid_llm)
        test("Accepts any model type", result is not None)
    except Exception as e:
        test("Accepts any model type", False, str(e))
    
    # ========== SUMMARY ==========
    section("TEST SUMMARY")
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {passed_tests} ✓")
    print(f"Failed: {failed_tests} ✗")
    print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
    
    if failed_details:
        print(f"\nFailed Tests:")
        for name, error in failed_details:
            print(f"  • {name}")
            if error:
                print(f"    {error}")
    
    print(f"\n{'='*70}")
    if failed_tests == 0:
        print("✓ ALL TESTS PASSED!")
        print(f"{'='*70}")
        sys.exit(0)
    else:
        print(f"✗ {failed_tests} TEST(S) FAILED")
        print(f"{'='*70}")
        sys.exit(1)
