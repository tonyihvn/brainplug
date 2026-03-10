#!/usr/bin/env python3
"""Clean up rules.json by removing Unicode demarcation lines."""

import json
from pathlib import Path

def clean_rules_json():
    """Remove Unicode demarcation lines and replace with simple underscores."""
    rules_file = Path('instance/rag_db/rules.json')
    
    if not rules_file.exists():
        print("rules.json not found")
        return
    
    # Read the file
    with open(rules_file, 'r', encoding='utf-8') as f:
        rules = json.load(f)
    
    print(f"Processing {len(rules)} rules...")
    
    for rule in rules:
        if 'content' in rule and rule['content']:
            content = rule['content']
            
            # Replace Unicode horizontal lines (U+2550 and U+2500) with underscores
            # Also replace repeated patterns
            content = content.replace('\u2550' * 70, '_' * 70)  # Long lines first
            content = content.replace('\u2550' * 69, '_' * 69)
            content = content.replace('\u2550' * 68, '_' * 68)
            content = content.replace('\u2550' * 65, '_' * 65)
            content = content.replace('\u2550' * 64, '_' * 64)
            content = content.replace('\u2550' * 63, '_' * 63)
            content = content.replace('\u2550' * 60, '_' * 60)
            
            # Replace remaining individual characters
            content = content.replace('\u2550', '_')
            content = content.replace('\u2500', '_')
            
            # Also replace the line used in the table header (↓)
            content = content.replace('\u2192', '->')
            
            rule['content'] = content
    
    # Write back
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(rules, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Cleaned {len(rules)} rules")
    print(f"✓ Saved to {rules_file}")

if __name__ == '__main__':
    clean_rules_json()
