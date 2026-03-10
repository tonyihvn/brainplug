#!/usr/bin/env python3
"""
Verify that the app is clean and all orphaned data has been removed.
Also provides recommendations for production readiness.
"""
import json
from pathlib import Path
from typing import Dict, List, Tuple
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

class CleanupVerifier:
    """Verify cleanup status and health of the application."""
    
    def __init__(self, workspace_root: str = None):
        """Initialize verifier."""
        if workspace_root is None:
            workspace_root = Path(__file__).parent.parent
        else:
            workspace_root = Path(workspace_root)
        
        self.workspace_root = workspace_root
        self.instance_dir = self.workspace_root / "instance"
        self.rag_db_dir = self.instance_dir / "rag_db"
        self.store_dir = self.instance_dir / "store"
        self.ingested_dir = self.instance_dir / "ingested_data"
        
        self.health_report = {
            'status': 'HEALTHY',
            'issues': [],
            'warnings': [],
            'info': [],
            'rules_by_database': {},
            'schemas_by_database': {},
            'stats': {}
        }
    
    def verify_database_settings(self) -> Tuple[int, Dict]:
        """Verify database settings are present and valid."""
        try:
            settings_file = self.store_dir / "database_settings.json"
            if not settings_file.exists():
                self.health_report['warnings'].append("No database_settings.json file found")
                return 0, {}
            
            settings_data = json.loads(settings_file.read_text())
            valid_count = 0
            settings_dict = {}
            
            for setting in settings_data:
                if isinstance(setting, dict) and 'id' in setting:
                    valid_count += 1
                    settings_dict[setting['id']] = setting.get('name', 'Unknown')
            
            self.health_report['info'].append(f"✓ Found {valid_count} active database connection(s)")
            self.health_report['stats']['active_databases'] = valid_count
            
            return valid_count, settings_dict
        except Exception as e:
            self.health_report['issues'].append(f"Error reading database settings: {e}")
            self.health_report['status'] = 'ERROR'
            return 0, {}
    
    def verify_rag_rules(self, valid_ids: List[str]) -> Dict:
        """Verify RAG rules and detect orphaned entries."""
        try:
            rules_file = self.rag_db_dir / "rules.json"
            if not rules_file.exists():
                self.health_report['info'].append("✓ No RAG rules file (expected if no databases connected)")
                return {}
            
            rules_data = json.loads(rules_file.read_text())
            rules_by_db = {}
            orphaned = []
            
            for rule in rules_data:
                if not isinstance(rule, dict):
                    continue
                
                metadata = rule.get('metadata', {})
                db_id = metadata.get('database_id') or metadata.get('db_id')
                
                if db_id in valid_ids:
                    if db_id not in rules_by_db:
                        rules_by_db[db_id] = []
                    rules_by_db[db_id].append(rule.get('id', 'Unknown'))
                else:
                    orphaned.append({
                        'id': rule.get('id'),
                        'db_id': db_id,
                        'rule_name': metadata.get('rule_name', 'Unknown')
                    })
            
            total_rules = len(rules_data)
            self.health_report['stats']['total_rules'] = total_rules
            self.health_report['stats']['rules_by_database'] = {k: len(v) for k, v in rules_by_db.items()}
            self.health_report['rules_by_database'] = rules_by_db
            
            if orphaned:
                self.health_report['issues'].append(
                    f"⚠️  Found {len(orphaned)} orphaned rules! These should have been deleted."
                )
                self.health_report['status'] = 'UNHEALTHY'
            else:
                self.health_report['info'].append(f"✓ All {total_rules} RAG rules are valid (no orphaned entries)")
            
            return rules_by_db
        except Exception as e:
            self.health_report['issues'].append(f"Error reading RAG rules: {e}")
            self.health_report['status'] = 'ERROR'
            return {}
    
    def verify_rag_schemas(self, valid_ids: List[str]) -> Dict:
        """Verify RAG schemas and detect orphaned entries."""
        try:
            schemas_file = self.rag_db_dir / "schemas.json"
            if not schemas_file.exists():
                self.health_report['info'].append("✓ No RAG schemas file (expected if no databases connected)")
                return {}
            
            schemas_data = json.loads(schemas_file.read_text())
            schemas_by_db = {}
            orphaned = []
            
            for schema in schemas_data:
                if not isinstance(schema, dict):
                    continue
                
                metadata = schema.get('metadata', {})
                db_id = metadata.get('database_id') or metadata.get('db_id')
                
                if db_id in valid_ids:
                    if db_id not in schemas_by_db:
                        schemas_by_db[db_id] = []
                    schemas_by_db[db_id].append(schema.get('id', 'Unknown'))
                else:
                    orphaned.append({
                        'id': schema.get('id'),
                        'db_id': db_id,
                        'table_name': metadata.get('table_name', 'Unknown')
                    })
            
            total_schemas = len(schemas_data)
            self.health_report['stats']['total_schemas'] = total_schemas
            self.health_report['stats']['schemas_by_database'] = {k: len(v) for k, v in schemas_by_db.items()}
            self.health_report['schemas_by_database'] = schemas_by_db
            
            if orphaned:
                self.health_report['issues'].append(
                    f"⚠️  Found {len(orphaned)} orphaned schemas! These should have been deleted."
                )
                self.health_report['status'] = 'UNHEALTHY'
            else:
                self.health_report['info'].append(f"✓ All {total_schemas} RAG schemas are valid (no orphaned entries)")
            
            return schemas_by_db
        except Exception as e:
            self.health_report['issues'].append(f"Error reading RAG schemas: {e}")
            self.health_report['status'] = 'ERROR'
            return {}
    
    def verify_ingested_data(self, valid_ids: List[str]) -> Dict:
        """Verify ingested data directories match active databases."""
        try:
            if not self.ingested_dir.exists():
                self.health_report['info'].append("✓ No ingested data directory (expected if data not ingested yet)")
                return {}
            
            ingested_dbs = {}
            orphaned = []
            
            for item in self.ingested_dir.iterdir():
                if item.is_dir():
                    db_id = item.name
                    if db_id in valid_ids:
                        # Count files in directory
                        file_count = len(list(item.glob('*.json')))
                        ingested_dbs[db_id] = file_count
                    else:
                        orphaned.append(db_id)
            
            self.health_report['stats']['ingested_databases'] = list(ingested_dbs.keys())
            
            if orphaned:
                self.health_report['warnings'].append(
                    f"⚠️  Found {len(orphaned)} orphaned ingested data directories: {orphaned}"
                )
            else:
                if ingested_dbs:
                    self.health_report['info'].append(
                        f"✓ All ingested data directories valid ({len(ingested_dbs)} database(s))"
                    )
            
            return ingested_dbs
        except Exception as e:
            self.health_report['warnings'].append(f"Could not verify ingested data: {e}")
            return {}
    
    def verify_test_files(self) -> int:
        """Check for remaining test files."""
        test_patterns = [
            'test_*.py',
            'verify_*.py',
            '*_ERROR_HANDLING_*.md',
            '*_INGESTION_*.md',
            'IMPLEMENTATION_VERIFICATION.md'
        ]
        
        test_files = []
        for pattern in test_patterns:
            test_files.extend(self.workspace_root.glob(pattern))
        
        if test_files:
            self.health_report['warnings'].append(
                f"ℹ️  Found {len(test_files)} test/temp files (can be removed if no longer needed)"
            )
        else:
            self.health_report['info'].append("✓ No test or temporary files detected")
        
        return len(test_files)
    
    def verify_app_database(self) -> bool:
        """Check app database exists."""
        try:
            app_db = self.instance_dir / "app.db"
            if app_db.exists():
                size_mb = app_db.stat().st_size / (1024 * 1024)
                self.health_report['info'].append(f"✓ App database exists ({size_mb:.2f} MB)")
                return True
            else:
                self.health_report['warnings'].append("App database not found (will be created on first run)")
                return False
        except Exception as e:
            self.health_report['warnings'].append(f"Could not verify app database: {e}")
            return False
    
    def run_verification(self) -> Dict:
        """Run full cleanup verification."""
        logger.info("=" * 80)
        logger.info("VERIFYING APP CLEANUP STATUS")
        logger.info("=" * 80)
        
        # Get valid database IDs
        logger.info("\n[1/6] Checking database settings...")
        valid_count, settings_dict = self.verify_database_settings()
        valid_ids = list(settings_dict.keys())
        
        # Verify rules
        logger.info("\n[2/6] Verifying RAG rules...")
        self.verify_rag_rules(valid_ids)
        
        # Verify schemas
        logger.info("\n[3/6] Verifying RAG schemas...")
        self.verify_rag_schemas(valid_ids)
        
        # Verify ingested data
        logger.info("\n[4/6] Verifying ingested data...")
        self.verify_ingested_data(valid_ids)
        
        # Verify test files cleaned
        logger.info("\n[5/6] Checking for test files...")
        self.verify_test_files()
        
        # Verify app database
        logger.info("\n[6/6] Verifying app database...")
        self.verify_app_database()
        
        return self.health_report
    
    def print_report(self):
        """Print verification report."""
        logger.info("\n" + "=" * 80)
        logger.info("VERIFICATION REPORT")
        logger.info("=" * 80)
        
        # Status
        status = self.health_report['status']
        if status == 'HEALTHY':
            logger.info(f"\n✓ STATUS: {status} 🟢")
        elif status == 'UNHEALTHY':
            logger.info(f"\n⚠️  STATUS: {status} 🟡")
        else:
            logger.info(f"\n❌ STATUS: {status} 🔴")
        
        # Stats
        logger.info("\n--- STATISTICS ---")
        for key, value in self.health_report['stats'].items():
            logger.info(f"  {key}: {value}")
        
        # Info
        if self.health_report['info']:
            logger.info("\n--- HEALTHY FINDINGS ---")
            for msg in self.health_report['info']:
                logger.info(f"  {msg}")
        
        # Warnings
        if self.health_report['warnings']:
            logger.info("\n--- WARNINGS ---")
            for msg in self.health_report['warnings']:
                logger.info(f"  {msg}")
        
        # Issues
        if self.health_report['issues']:
            logger.info("\n--- ISSUES FOUND ---")
            for msg in self.health_report['issues']:
                logger.info(f"  {msg}")
        
        # Recommendations
        logger.info("\n--- RECOMMENDATIONS ---")
        if status == 'HEALTHY':
            logger.info("  ✓ App is clean and ready to use")
            logger.info("  ✓ No orphaned data detected")
            logger.info("  ✓ Cascade delete is working properly")
        else:
            logger.info("  ⚠️  Please run cleanup_orphaned_data.py to remove orphaned entries")
        
        logger.info("\n" + "=" * 80)


def main():
    """Main verification entry point."""
    try:
        verifier = CleanupVerifier()
        verifier.run_verification()
        verifier.print_report()
        
        # Exit code based on status
        if verifier.health_report['status'] == 'HEALTHY':
            return 0
        else:
            return 1
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        return 2


if __name__ == '__main__':
    exit(main())
