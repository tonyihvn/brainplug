#!/usr/bin/env python3
"""Fix LLM entries in instance/rag_db/database_settings.json

This script will:
- Prefix LLM entries' `id` with `llm_` when they look like LLM settings
- Normalize `model_id` by stripping a leading `ollama:` prefix
- Deduplicate entries by preferring the newest `created_at` timestamp

Run: python scripts/fix_rag_llm_settings.py
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_FILE = ROOT / 'instance' / 'rag_db' / 'database_settings.json'


def load_items(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return []


def write_items(path: Path, items):
    path.write_text(json.dumps(items, indent=2))


def is_llm_entry(item: dict) -> bool:
    # Heuristic: presence of model_type or model_id or api_endpoint indicates LLM
    return bool(item.get('model_type') or item.get('model_id') or item.get('api_endpoint'))


def normalize_model_id(mid: str) -> str:
    if not isinstance(mid, str):
        return mid
    if mid.lower().startswith('ollama:'):
        return mid.split(':', 1)[1]
    return mid


def parse_created_at(item: dict):
    v = item.get('created_at') or ''
    try:
        return datetime.fromisoformat(v)
    except Exception:
        return datetime.min


def main():
    print(f"Loading: {SETTINGS_FILE}")
    items = load_items(SETTINGS_FILE)
    if not items:
        print("No settings found or failed to read file.")
        return

    # Map of id -> item (choose newest by created_at)
    out_map = {}

    for it in items:
        new_it = dict(it)
        if is_llm_entry(it):
            raw_id = str(it.get('id') or '')
            if not raw_id.startswith('llm_'):
                new_id = 'llm_' + raw_id
            else:
                new_id = raw_id
            new_it['id'] = new_id

            # normalize model id
            if 'model_id' in new_it:
                new_it['model_id'] = normalize_model_id(new_it.get('model_id'))

        # Decide whether to keep: prefer newest created_at
        cur = out_map.get(new_it['id'])
        if not cur:
            out_map[new_it['id']] = new_it
        else:
            a = parse_created_at(cur)
            b = parse_created_at(new_it)
            if b >= a:
                out_map[new_it['id']] = new_it

    new_items = list(out_map.values())

    # Sort by name for readability, keep databases first
    def sort_key(it):
        # Databases have db_type
        if it.get('db_type'):
            return (0, it.get('name') or '')
        return (1, it.get('name') or '')

    new_items_sorted = sorted(new_items, key=sort_key)

    # Backup
    backup = SETTINGS_FILE.with_suffix('.backup.json')
    try:
        SETTINGS_FILE.replace(backup)
        print(f"Backup saved to: {backup}")
    except Exception:
        print("Warning: could not create backup; aborting")
        return

    write_items(SETTINGS_FILE, new_items_sorted)
    print(f"Wrote cleaned settings ({len(new_items_sorted)} items) to {SETTINGS_FILE}")


if __name__ == '__main__':
    main()
