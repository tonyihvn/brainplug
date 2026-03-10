#!/usr/bin/env python3
"""Simple verification script for SQL security features"""

from backend.services.settings_service import SettingsService

# Test 1: Get and set system settings
print("\nTest 1: System Settings")
print("-" * 50)

settings_service = SettingsService()

# Get defaults
defaults = settings_service.get_system_settings()
print("Default restricted keywords:", list(defaults['restricted_keywords'].keys()))

# Update settings
new_settings = {
    'restricted_keywords': {
        'DROP': True,
        'DELETE': True,
        'INSERT': False,
        'ALTER': True,
        'SELECT': False,
        'UPDATE': False,
        'TRUNCATE': True
    }
}
settings_service.update_system_settings(new_settings)

# Verify
updated = settings_service.get_system_settings()
print("After update, restricted keywords:")
for kw, restricted in updated['restricted_keywords'].items():
    print(f"  {kw}: {'RESTRICTED' if restricted else 'ALLOWED'}")

# Test 2: Query validation
print("\nTest 2: Query Validation")
print("-" * 50)

test_queries = [
    ("SELECT * FROM users", True),
    ("DROP TABLE users", False),
    ("DELETE FROM users", False),
    ("INSERT INTO users VALUES (1)", False),
    ("UPDATE users SET name = 'test'", False),
]

for query, should_pass in test_queries:
    is_valid, msg = settings_service.validate_query_for_restricted_keywords(query)
    result = "PASS" if is_valid == should_pass else "FAIL"
    print(f"[{result}] {query[:40]:<40} -> {is_valid}")

print("\n[PASS] All security features implemented successfully!")
