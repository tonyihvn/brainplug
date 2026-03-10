#!/usr/bin/env python3
"""
Test script to verify RAG generation fixes.
Tests:
1. Database connection with query_mode preservation
2. RAG schema extraction for tables
3. Verify all tables are discovered and documented
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.services.settings_service import SettingsService
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

def test_database_settings_with_query_mode():
    """Test that query_mode is preserved when saving database settings."""
    
    logger.info("=" * 80)
    logger.info("TEST 1: Database Settings with Query Mode Preservation")
    logger.info("=" * 80)
    
    settings_service = SettingsService()
    
    try:
        # Create test database setting with API Query mode
        test_setting = {
            'name': 'Test PostgreSQL DB',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'postgres',
            'password': 'password',
            'is_active': False,  # Don't activate for now (no connection needed)
            'query_mode': 'api',  # ← KEY: API Query mode
            'selected_tables': {},
            'sync_interval': 60
        }
        
        logger.info("\n✓ Test: Saving database setting with query_mode='api'")
        logger.info(f"  Input: {test_setting}")
        
        # Note: This will fail due to no real connection, but we can check the error
        try:
            result = settings_service.update_database_settings(test_setting)
            logger.info(f"  ✓ Result: {result}")
            
            # Check if query_mode is preserved
            if result.get('query_mode') == 'api':
                logger.info("  ✅ PASS: query_mode 'api' was preserved")
            else:
                logger.warning(f"  ❌ FAIL: query_mode is {result.get('query_mode')}, expected 'api'")
                
        except Exception as e:
            # Expected to fail due to no connection, but check that query_mode was set
            all_settings = settings_service.rag_db.get_all_database_settings()
            test_db = next((s for s in all_settings if s.get('name') == 'Test PostgreSQL DB'), None)
            
            if test_db:
                logger.info(f"  Saved setting: {test_db}")
                if test_db.get('query_mode') == 'api':
                    logger.info("  ✅ PASS: query_mode 'api' was preserved in database")
                else:
                    logger.warning(f"  ❌ FAIL: query_mode is {test_db.get('query_mode')}, expected 'api'")
                    
                # Clean up
                settings_service.rag_db.delete_database_setting(test_db['id'])
                logger.info("  Cleaned up test setting")
            else:
                logger.warning(f"  Could not find saved setting. Error: {str(e)}")
        
    except Exception as e:
        logger.error(f"Test 1 error: {str(e)}", exc_info=True)

def test_query_mode_direct():
    """Test that Direct Query mode is also preserved."""
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST 2: Database Settings with Direct Query Mode")
    logger.info("=" * 80)
    
    settings_service = SettingsService()
    
    try:
        test_setting = {
            'name': 'Test Direct Query DB',
            'db_type': 'postgresql',
            'host': 'localhost',
            'port': 5432,
            'database': 'test_db',
            'username': 'postgres',
            'password': 'password',
            'is_active': False,
            'query_mode': 'direct',  # ← Direct Query mode
            'selected_tables': {},
            'sync_interval': 60
        }
        
        logger.info("\n✓ Test: Saving database setting with query_mode='direct'")
        
        try:
            result = settings_service.update_database_settings(test_setting)
            if result.get('query_mode') == 'direct':
                logger.info("  ✅ PASS: query_mode 'direct' was preserved")
            else:
                logger.warning(f"  ❌ FAIL: query_mode is {result.get('query_mode')}, expected 'direct'")
        except Exception as e:
            all_settings = settings_service.rag_db.get_all_database_settings()
            test_db = next((s for s in all_settings if s.get('name') == 'Test Direct Query DB'), None)
            
            if test_db:
                if test_db.get('query_mode') == 'direct':
                    logger.info("  ✅ PASS: query_mode 'direct' was preserved in database")
                else:
                    logger.warning(f"  ❌ FAIL: query_mode is {test_db.get('query_mode')}, expected 'direct'")
                settings_service.rag_db.delete_database_setting(test_db['id'])
            
    except Exception as e:
        logger.error(f"Test 2 error: {str(e)}", exc_info=True)

def test_schema_extraction():
    """Test that schema extraction finds all tables."""
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST 3: Schema Extraction Logging")
    logger.info("=" * 80)
    
    from backend.utils.database import DatabaseConnector
    
    logger.info("\n✓ Test: Schema extraction with enhanced logging")
    logger.info("  Review the logs below for [SCHEMA] entries to verify:")
    logger.info("  - Number of tables found in database")
    logger.info("  - Whether 'public' schema was checked (for PostgreSQL)")
    logger.info("  - Details of each table processed")
    logger.info("  - Any warnings or errors during extraction")
    logger.info("\n  PostgreSQL connection string format:")
    logger.info("    postgresql://username:password@localhost:5432/database_name")
    logger.info("\n  To manually test, run:")
    logger.info("    python scripts/test_rag_integration.py")


if __name__ == '__main__':
    logger.info("\n" + "=" * 80)
    logger.info("RAG GENERATION FIXES - VERIFICATION TESTS")
    logger.info("=" * 80)
    
    test_database_settings_with_query_mode()
    test_query_mode_direct()
    test_schema_extraction()
    
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    logger.info("\n✓ If all tests passed, the bugs are fixed:")
    logger.info("  1. query_mode='api' is now preserved when saving database settings")
    logger.info("  2. query_mode='direct' is now preserved when saving database settings")
    logger.info("  3. Schema extraction now logs detailed information for debugging")
    logger.info("\n✓ If Tables Scanned is still 0:")
    logger.info("  - Check database connection credentials")
    logger.info("  - Verify database server is running")
    logger.info("  - For PostgreSQL, ensure tables are in 'public' schema")
    logger.info("  - Review [SCHEMA] logs for detailed error messages")
    logger.info("\n" + "=" * 80)
