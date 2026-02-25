"""Check stored database credentials."""
import sys
sys.path.insert(0, '/'.join(__file__.split('\\')[:-1]))

from backend.services.settings_service import SettingsService

service = SettingsService()

active_db = service.get_active_database()

if active_db:
    print(f"\n✓ Found active database: {active_db.get('name')}")
    print(f"  Type: {active_db.get('db_type')}")
    print(f"  Host: {active_db.get('host')}")
    print(f"  Port: {active_db.get('port')}")
    print(f"  Database: {active_db.get('database')}")
    print(f"  Username: {active_db.get('username')}")
    pw = active_db.get('password')
    print(f"  Password: {'*' * len(pw) if pw else 'NONE'}")
    print(f"  Password (actual): {pw}")
    # Build a simple connection string (format depends on db_type)
    if active_db.get('db_type') == 'mysql':
        connection_string = f"mysql+pymysql://{active_db.get('username')}:{pw}@{active_db.get('host')}:{active_db.get('port')}/{active_db.get('database')}"
    else:
        connection_string = f"{active_db.get('db_type')}://{active_db.get('username')}:{pw}@{active_db.get('host')}:{active_db.get('port')}/{active_db.get('database')}"
    print(f"\n  Connection String: {connection_string}")
else:
    print("✗ No active database found")
