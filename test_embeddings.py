#!/usr/bin/env python3
"""Test embedding generation and display sample data."""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from utils.rag_database import RAGDatabaseManager

def test_embeddings():
    """Test if embeddings are being generated."""
    try:
        # Initialize RAG database manager
        rag_db = RAGDatabaseManager()
        
        # Check if embedder is available
        from utils.rag_database import get_embedder
        embedder = get_embedder()
        
        if embedder is None:
            print("❌ FAIL: Embedder not initialized")
            return False
        
        print("✓ Embedder loaded successfully")
        
        # Test embedding a sample text
        test_text = "This is a sample business rule for testing embeddings"
        embedding = rag_db._embed_text(test_text)
        
        if embedding is None:
            print("❌ FAIL: Embedding returned None")
            return False
        
        if not isinstance(embedding, list):
            print(f"❌ FAIL: Embedding is not a list, got {type(embedding)}")
            return False
        
        print(f"✓ Embedding generated successfully: {len(embedding)} dimensions")
        
        # Check rules.json for embeddings
        rules_file = Path('instance/rag_db/rules.json')
        if rules_file.exists():
            with open(rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            
            print(f"\n📊 Rules Analysis:")
            print(f"Total rules: {len(rules)}")
            
            # Check formatting (no Unicode box drawing characters)
            unicode_chars_found = 0
            for i, rule in enumerate(rules):
                content = rule.get('content', '')
                if '\u2550' in content or '\u2500' in content or '\u2192' in content:
                    unicode_chars_found += 1
            
            if unicode_chars_found == 0:
                print("✓ No Unicode demarcation characters found (cleaned successfully)")
            else:
                print(f"⚠️  WARNING: {unicode_chars_found} rules still have Unicode characters")
            
            # Check embeddings (note: rules might not have embeddings if added before)
            embeddings_null = sum(1 for r in rules if r.get('embedding') is None)
            embeddings_set = len(rules) - embeddings_null
            print(f"Rules with embeddings: {embeddings_set}")
            print(f"Rules with null embeddings: {embeddings_null}")
            
            if embeddings_set > 0:
                print("\n✓ Some rules have embeddings!")
                # Show sample
                for rule in rules:
                    if rule.get('embedding') is not None:
                        emb = rule['embedding']
                        dimensions = len(emb) if isinstance(emb, list) else 'unknown'
                        print(f"  Rule: {rule.get('id', 'unknown')[:40]}...")
                        print(f"  Embedding dimensions: {dimensions}")
                        break
            else:
                print("\n⚠️  WARNING: No rules have embeddings yet")
                print("   Reason: Rules in rules.json were created before sentence-transformers was installed")
                print("   Fix: Re-ingest data or manually generate embeddings")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_embeddings()
    sys.exit(0 if success else 1)
