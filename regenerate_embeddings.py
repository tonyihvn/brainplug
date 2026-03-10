#!/usr/bin/env python3
"""Regenerate embeddings for existing rules in rules.json"""

import json
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / 'backend'))

from utils.rag_database import RAGDatabase

def regenerate_embeddings():
    """Regenerate embeddings for all rules in rules.json"""
    try:
        rules_file = Path('instance/rag_db/rules.json')
        
        if not rules_file.exists():
            print("❌ rules.json not found")
            return False
        
        # Initialize RAG database
        rag_db = RAGDatabase()
        
        # Load existing rules
        with open(rules_file, 'r', encoding='utf-8') as f:
            rules = json.load(f)
        
        print(f"📚 Regenerating embeddings for {len(rules)} rules...")
        
        updated_count = 0
        failed_count = 0
        
        for i, rule in enumerate(rules):
            try:
                content = rule.get('content', '')
                if not content:
                    print(f"  [{i+1}/{len(rules)}] Skipped (no content)")
                    continue
                
                # Generate embedding
                embedding = rag_db._embed_text(content)
                
                if embedding is not None:
                    rule['embedding'] = embedding
                    updated_count += 1
                    if updated_count % 5 == 0:
                        print(f"  [{i+1}/{len(rules)}] ✓ Generated embedding ({len(embedding)} dims)")
                else:
                    failed_count += 1
                    print(f"  [{i+1}/{len(rules)}] ✗ Failed to generate embedding")
                    
            except Exception as e:
                failed_count += 1
                print(f"  [{i+1}/{len(rules)}] ✗ Error: {str(e)[:50]}")
                continue
        
        # Save updated rules
        with open(rules_file, 'w', encoding='utf-8') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Regeneration Complete:")
        print(f"   - Updated: {updated_count} rules")
        print(f"   - Failed: {failed_count} rules")
        print(f"   - Saved to {rules_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = regenerate_embeddings()
    sys.exit(0 if success else 1)
