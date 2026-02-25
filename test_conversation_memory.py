"""
Test script for conversation memory functionality.

Tests that the LLM can maintain context across multiple messages
and reference previous discussions and decisions.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.utils.conversation_memory import ConversationMemory
from backend.utils.schema_classifier import SchemaClassifier
from backend.models.conversation import Conversation, Message
from backend.models import db, init_db
from flask import Flask

# Setup Flask app context
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL', 
    'sqlite:///gemini_mcp.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
with app.app_context():
    init_db()
    
    print("=" * 80)
    print("TESTING CONVERSATION MEMORY")
    print("=" * 80)
    
    # Create a test conversation
    print("\n1. Creating test conversation...")
    conv_id = "test_conv_001"
    # Ensure any previous test data with same id is removed
    existing = db.session.get(Conversation, conv_id)
    if existing:
        db.session.delete(existing)
        db.session.commit()

    conv = Conversation(
        id=conv_id,
        title="Test Conversation: Inventory Analysis"
    )
    db.session.add(conv)
    
    # Add test messages simulating a real conversation
    messages = [
        Message(
            id="msg_001",
            conversation_id=conv_id,
            role="user",
            content="Get the last 20 records in the inventories where category is Laptops"
        ),
        Message(
            id="msg_002",
            conversation_id=conv_id,
            role="assistant",
            content="I'll retrieve the last 20 laptop records from the inventories table.",
            action_data={
                "type": "DATABASE_QUERY",
                "sql_query": "SELECT * FROM inventories WHERE category='Laptops' ORDER BY created_at DESC LIMIT 20",
                "confidence": "high"
            }
        ),
        Message(
            id="msg_003",
            conversation_id=conv_id,
            role="user",
            content="Display the result in a table"
        ),
        Message(
            id="msg_004",
            conversation_id=conv_id,
            role="assistant",
            content="The results are now displayed in table format above.",
            action_data={
                "type": "FORMAT_DISPLAY",
                "format": "datatable",
                "confidence": "high"
            }
        ),
        Message(
            id="msg_005",
            conversation_id=conv_id,
            role="user",
            content="Check our previous chat - what tables were we discussing?"
        ),
    ]
    
    for msg in messages:
        db.session.add(msg)
    
    db.session.commit()
    print(f"✓ Created conversation {conv_id} with {len(messages)} messages")
    
    # Test ConversationMemory
    print("\n2. Testing ConversationMemory...")
    memory = ConversationMemory(conv_id)
    
    print(f"   - Loaded {len(memory.messages)} messages")
    print(f"   - Schemas mentioned: {memory.get_schemas_mentioned()}")
    print(f"   - Total decisions made: {len(memory.decisions)}")
    print(f"   - Last action: {memory.get_last_action()}")
    
    # Test conversation context retrieval
    print("\n3. Testing conversation context retrieval...")
    context = memory.get_conversation_context(max_messages=3)
    print("   Last 3 messages context:")
    for line in context.split('\n')[:10]:
        print(f"   {line}")
    
    # Test decisions context
    print("\n4. Testing decisions context...")
    decisions = memory.get_decisions_context()
    print("   Decisions made:")
    for line in decisions.split('\n')[:15]:
        print(f"   {line}")
    
    # Test clarification detection
    print("\n5. Testing clarification detection...")
    test_queries = [
        "Check our previous chat - what tables were we discussing?",
        "Get another 10 records",
        "Like before, show me the same data",
        "what was the last query we ran?"
    ]
    
    for query in test_queries:
        is_ref = memory.is_referencing_previous_context(query)
        print(f"   '{query}' -> References previous: {is_ref}")
    
    # Test schema classifier with conversation
    print("\n6. Testing schema classifier with conversation memory...")
    classifier = SchemaClassifier()
    
    # Get available schemas (from memory)
    available_schemas = [
        {
            'id': 'inventories_schema',
            'metadata': {'table_name': 'inventories'}
        },
        {
            'id': 'products_schema',
            'metadata': {'table_name': 'products'}
        },
        {
            'id': 'orders_schema',
            'metadata': {'table_name': 'orders'}
        }
    ]
    
    test_query = "Check our previous chat - what tables were we discussing?"
    matched, extracted, needs_clarification = classifier.match_tables_to_rag(
        test_query,
        available_schemas,
        [{'content': msg.content, 'role': msg.role} for msg in memory.get_last_n_messages(5)]
    )
    
    print(f"   Query: '{test_query}'")
    print(f"   - Extracted tables: {extracted}")
    print(f"   - Matched {len(matched)} schemas")
    print(f"   - Needs clarification: {needs_clarification}")
    
    # Test full context
    print("\n7. Testing full context generation...")
    full_context = memory.get_full_context()
    print("   Full context (first 500 chars):")
    print(f"   {full_context[:500]}...")
    
    # Test conversation summary
    print("\n8. Testing conversation summary...")
    summary = memory.get_conversation_summary()
    print(f"   - Conversation ID: {summary['conversation_id']}")
    print(f"   - Total messages: {summary['total_messages']}")
    print(f"   - Total decisions: {summary['total_decisions']}")
    print(f"   - Schemas mentioned: {summary['schemas_mentioned']}")
    print(f"   - Last action type: {summary['last_action'].get('type') if summary['last_action'] else 'None'}")
    
    print("\n" + "=" * 80)
    print("✓ ALL TESTS COMPLETED SUCCESSFULLY")
    print("=" * 80)
    
    # Cleanup
    db.session.delete(conv)
    db.session.commit()
    print("\nTest data cleaned up.")
