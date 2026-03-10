#!/usr/bin/env python3
import json
from pathlib import Path

rules_file = Path('instance/rag_db/rules.json')
with open(rules_file, 'r', encoding='utf-8') as f:
    rules = json.load(f)

has_emb = [r for r in rules if r.get('embedding')]
print(f'✓ Total rules: {len(rules)}')
print(f'✓ Rules with embeddings: {len(has_emb)}')
if has_emb:
    print(f'✓ Embedding dimensions: {len(has_emb[0]["embedding"])}')
    print(f'\n Sample rule with embedding:')
    rule = has_emb[0]
    print(f'  ID: {rule.get("id", "unknown")[:50]}')
    print(f'  Content: {rule.get("content", "")[:100]}...')
    print(f'  Embedding: [{has_emb[0]["embedding"][0]:.4f}, {has_emb[0]["embedding"][1]:.4f}, {has_emb[0]["embedding"][2]:.4f}, ...]')
